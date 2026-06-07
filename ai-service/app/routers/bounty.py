import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.config import settings
from app.schemas import (
    DiyBountyAnswers,
    DiyBountyGenerateResponse,
    DiyBountyPublishRequest,
    DiyBountyPublishResponse,
)
from app.services.bounty_generator import generate_diy_bounty_variants
from app.services.history_store import append_history_record

router = APIRouter()

GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated" / "diy-bounty-jobs"


def _save_diy_audit_record(
    job_id: str,
    reference_image_bytes: bytes,
    hand_image_bytes: bytes | None,
    response: DiyBountyGenerateResponse,
    answers: DiyBountyAnswers,
    timings_ms: dict[str, float],
    created_at: datetime,
    completed_at: datetime,
) -> None:
    audit_dir = Path("generated/diy-audit") / job_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    # Save reference image
    (audit_dir / "reference_image.jpg").write_bytes(reference_image_bytes)
    
    # Save hand image if present
    if hand_image_bytes:
        (audit_dir / "hand_image.jpg").write_bytes(hand_image_bytes)
        
    # Download/save result image
    result_url = None
    if response.variants:
        variant = response.variants[0]
        if variant.image_url.startswith("data:image/"):
            try:
                header, encoded = variant.image_url.split(",", 1)
                data = base64.b64decode(encoded)
                (audit_dir / "result_image.png").write_bytes(data)
                result_url = f"/generated/diy-audit/{job_id}/result_image.png"
            except Exception as e:
                logging.warning(f"Failed to decode base64 result image for audit: {e}")
        else:
            try:
                import httpx
                r = httpx.get(variant.image_url, timeout=10.0)
                if r.status_code == 200:
                    (audit_dir / "result_image.png").write_bytes(r.content)
                    result_url = f"/generated/diy-audit/{job_id}/result_image.png"
            except Exception as e:
                logging.warning(f"Failed to download variant image for audit: {e}")

    # Build variants payload summary to match what test UI parses
    variants_summary = []
    for var in response.variants:
        variants_summary.append({
            "id": var.id,
            "image_url": resolve_variant_url(var.image_url, job_id) if result_url else var.image_url,
            "title": var.title,
            "tags": var.tags,
            "prompt": var.prompt
        })

    summary = {
        "id": job_id,
        "job_id": job_id,
        "created_at": created_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status": response.status,
        "channel": response.channel,
        "model": settings.qwen_image_model if hand_image_bytes else settings.doubao_image_model,
        "prompt": response.prompt,
        "answers": answers.model_dump(),
        "variants": variants_summary,
        "assets": {
            "reference_image_url": f"/generated/diy-audit/{job_id}/reference_image.jpg",
            "hand_image_url": f"/generated/diy-audit/{job_id}/hand_image.jpg" if hand_image_bytes else None,
            "result_image_url": result_url
        },
        "timings_ms": timings_ms,
        "payload_summary": {
            "endpoint": settings.qwen_image_api_url if hand_image_bytes else settings.doubao_image_api_url,
            "model": settings.qwen_image_model if hand_image_bytes else settings.doubao_image_model,
            "mode": response.channel
        },
        "sent_to_model": {
            "hand_image": bool(hand_image_bytes),
            "reference_image": True,
            "prompt": True,
            "single_image": not bool(hand_image_bytes)
        },
        "publish": {
            "status": "not_published",
            "bounty_id": None,
            "image": None,
            "title": None,
            "merchant_visible": False,
            "store_visible": False
        }
    }
    
    (audit_dir / "request_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_variant_url(url: str, job_id: str) -> str:
    if url.startswith("data:image/"):
        return f"/generated/diy-audit/{job_id}/result_image.png"
    return url


def _update_diy_audit_publish_status(selected_variant_id: str, bounty_id: str, image_url: str, title: str, publish_ms: float = 150.0) -> None:
    root = Path("generated/diy-audit")
    if not root.exists():
        return
    for path in root.glob("*/request_summary.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            has_variant = False
            variants = data.get("variants") or data.get("provider_payload", {}).get("variants", [])
            if isinstance(variants, list):
                for v in variants:
                    if isinstance(v, dict) and v.get("id") == selected_variant_id:
                        has_variant = True
                        break
            if has_variant:
                data["publish"] = {
                    "status": "published",
                    "bounty_id": bounty_id,
                    "image": image_url,
                    "title": title,
                    "merchant_visible": True,
                    "store_visible": True
                }
                data.setdefault("timings_ms", {})["publish_total"] = publish_ms
                data["completed_at"] = datetime.now(timezone.utc).isoformat()
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                break
        except Exception as e:
            logging.warning(f"Error checking diy audit publish: {e}")


def _persist_generation(response: DiyBountyGenerateResponse, answers: DiyBountyAnswers) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    payload = response.model_dump()
    payload["answers"] = answers.model_dump()
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    (GENERATED_DIR / f"{response.job_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (GENERATED_DIR / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/generate", response_model=DiyBountyGenerateResponse)
async def generate_bounty(
    reference_image: UploadFile = File(...),
    answers: str = Form(...),
    num_variants: int = Form(1),
    user_id: str | None = Form(default=None),
    hand_image: UploadFile | None = File(default=None),
):
    import time
    t_start_perf = time.perf_counter()
    created_at_dt = datetime.now(timezone.utc)

    if not reference_image.content_type or not reference_image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a nail inspiration image.")

    try:
        parsed_answers = DiyBountyAnswers.model_validate(json.loads(answers))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid answers payload: {exc}") from exc

    image_bytes = await reference_image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Reference image is empty.")

    hand_bytes: bytes | None = None
    if hand_image and hand_image.content_type and hand_image.content_type.startswith("image/"):
        hand_bytes = await hand_image.read() or None

    t_val_done = time.perf_counter()
    val_ms = round((t_val_done - t_start_perf) * 1000, 1)

    try:
        prompt, variants, payload = await generate_diy_bounty_variants(image_bytes, parsed_answers, num_variants, hand_image_bytes=hand_bytes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DIY generation failed: {type(exc).__name__}: {str(exc)[:240]}") from exc

    t_gen_done = time.perf_counter()
    gen_timings = payload.get("timings_ms", {})

    mode = payload.get("mode", "mock-diy-bounty")
    channel_map = {"qwen-wan-diy": "qwen-wan-diy", "doubao-seedream-diy": "doubao-seedream-diy"}
    job_id = f"diy-{uuid4().hex[:12]}"
    
    # Pack assets info so they are saved in history record
    payload["assets"] = {
        "reference_image_url": f"/generated/diy-audit/{job_id}/reference_image.jpg",
        "hand_image_url": f"/generated/diy-audit/{job_id}/hand_image.jpg" if hand_bytes else None,
    }

    response = DiyBountyGenerateResponse(
        job_id=job_id,
        status="succeeded",
        channel=channel_map.get(mode, "mock-diy-bounty"),
        prompt=prompt,
        variants=variants,
        provider_payload=payload,
    )
    _persist_generation(response, parsed_answers)

    # Measure audit saving time
    t_save_start = time.perf_counter()
    try:
        # Construct exact timings dict dynamically
        timings_ms = {
            "input_validation": val_ms,
            "prompt_build": gen_timings.get("prompt_build", 10.0),
            "reference_image_normalize": gen_timings.get("reference_image_normalize", 50.0),
            "image_generation_api": gen_timings.get("image_generation_api", 1000.0),
        }
        
        # Save audit record synchronously
        _save_diy_audit_record(
            response.job_id,
            image_bytes,
            hand_bytes,
            response,
            parsed_answers,
            timings_ms=timings_ms,
            created_at=created_at_dt,
            completed_at=datetime.now(timezone.utc)
        )
        
        # Calculate full elapsed time including saving
        t_save_done = time.perf_counter()
        save_ms = round((t_save_done - t_save_start) * 1000, 1)
        total_ms = round((t_save_done - t_start_perf) * 1000, 1)
        
        # Finalize timings with audit saving time
        timings_ms["provider_total"] = total_ms
        timings_ms["total"] = total_ms
        
        # Re-save the summary file with the final timings
        audit_dir = Path("generated/diy-audit") / response.job_id
        summary_path = audit_dir / "request_summary.json"
        if summary_path.exists():
            try:
                summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
                summary_data["timings_ms"] = timings_ms
                summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
    except Exception as exc:
        logging.warning(f"Failed to save DIY audit record: {exc}")

    append_history_record(
        user_id,
        "diy-bounty",
        {
            "job_id": response.job_id,
            "status": response.status,
            "channel": response.channel,
            "prompt": response.prompt,
            "variants": [variant.model_dump() for variant in response.variants],
            "answers": parsed_answers.model_dump(),
            "provider_payload": payload,
        },
    )
    return response


@router.get("/latest", response_model=DiyBountyGenerateResponse | None)
async def latest_bounty_generation():
    latest_path = GENERATED_DIR / "latest.json"
    if not latest_path.exists():
        return Response(status_code=204)
    try:
        return DiyBountyGenerateResponse.model_validate(json.loads(latest_path.read_text(encoding="utf-8")))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Latest DIY generation is unreadable: {exc}") from exc


@router.post("/publish", response_model=DiyBountyPublishResponse)
async def publish_bounty(request: DiyBountyPublishRequest):
    bounty_id = f"bounty-{uuid4().hex[:8]}"
    bounty_data = {
        "id": bounty_id,
        "title": request.title,
        "budget": request.budget,
        "status": "待接单",
        "image": request.image,
        "participants": 0,
        "deadline": "3天后截止",
        "description": request.description,
        "selected_variant_id": request.selected_variant_id,
        "answers": request.answers.model_dump()
    }
    
    import time
    t_pub_start = time.perf_counter()
    from app.services.supabase_db import publish_bounty as run_publish_db
    saved = await run_publish_db(bounty_data)
    pub_ms = round((time.perf_counter() - t_pub_start) * 1000, 1)

    try:
        _update_diy_audit_publish_status(
            selected_variant_id=request.selected_variant_id,
            bounty_id=saved["id"],
            image_url=saved["image"],
            title=saved["title"],
            publish_ms=pub_ms
        )
    except Exception as exc:
        logging.warning(f"Failed to update DIY audit publish status: {exc}")
    return DiyBountyPublishResponse(
        id=saved["id"],
        title=saved["title"],
        budget=saved["budget"],
        status=saved["status"],
        image=saved["image"],
        participants=saved["participants"],
        deadline=saved["deadline"],
        description=saved.get("description", ""),
        selected_variant_id=saved.get("selected_variant_id", "")
    )
