from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas import TryOnResponse
from app.services.hand_detector import detect_hand
from app.services.nail_segmenter import segment_nails
from app.services.nail_core_algorithm import execute_commercial_try_on
from app.services.style_catalog import build_style_from_payload, get_style
from app.services.history_store import append_history_record
router = APIRouter()


@router.post("/try-on", response_model=TryOnResponse)
async def try_on(
    image: UploadFile = File(...),
    style_image: UploadFile | None = File(default=None),
    style_id: str | None = Form(default=None),
    style_payload: str | None = Form(default=None),
    generation_mode: str = Form(default="hd"),
    user_id: str | None = Form(default=None),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a hand photo image.")

    image_bytes = await image.read()
    style_image_bytes = await style_image.read() if style_image else None
    
    if not style_image_bytes:
        raise HTTPException(status_code=422, detail="商业级管线需要提供明确的款式图。")
        
    detection = await detect_hand(image_bytes)
    if detection.confidence < 0.65:
        raise HTTPException(status_code=422, detail=detection.message)

    segmentation = await segment_nails(image_bytes)
    
    style = build_style_from_payload(style_payload) or get_style(style_id)
    try:
        result_url, channel, payload = await execute_commercial_try_on(
            image_bytes,
            style_image_bytes,
            style,
            generation_mode=generation_mode,
        )
    except ValueError as val_exc:
        raise HTTPException(status_code=422, detail=str(val_exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 生图服务调用失败：{str(exc)[:600]}") from exc
    payload = {
        **payload,
        "nail_segmentation": {
            "available": segmentation.available,
            "nail_count": segmentation.nail_count,
            "confidence": segmentation.confidence,
            "message": segmentation.message,
            "boxes": segmentation.boxes,
        },
    }
    response = TryOnResponse(
        job_id=str(uuid4()),
        status="succeeded",
        channel=channel,
        style=style,
        hand_confidence=detection.confidence,
        quality_score=max(0.84 if channel == "mock-image2" else 0.9, segmentation.confidence),
        result_image_url=result_url,
        # Keep large base64 masks internal; returning them through the web proxy can make long try-on responses brittle.
        mask_image_url=None,
        nail_count=segmentation.nail_count,
        nail_confidence=segmentation.confidence,
        provider_payload=payload,
    )
    append_history_record(
        user_id,
        "try-on",
        {
            "job_id": response.job_id,
            "status": response.status,
            "channel": response.channel,
            "style": response.style.model_dump(),
            "result_image_url": response.result_image_url,
            "mask_image_url": response.mask_image_url,
            "hand_confidence": response.hand_confidence,
            "quality_score": response.quality_score,
            "nail_count": response.nail_count,
            "nail_confidence": response.nail_confidence,
        },
    )
    try:
        from app.services.supabase_db import increment_style_analytics
        await increment_style_analytics(style.id, "try_ons")
    except Exception:
        pass
    return response
