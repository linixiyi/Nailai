import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _audit_root() -> Path:
    return Path("generated/tryon-audit")


def _read_summary(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@router.get("/runs")
async def list_runs():
    root = _audit_root()
    if not root.exists():
        return {"runs": []}
    summaries = [
        _read_summary(path)
        for path in root.glob("*/request_summary.json")
    ]
    runs = [summary for summary in summaries if summary.get("id")]
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    path = _audit_root() / run_id / "request_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="测试记录不存在")
    summary = _read_summary(path)
    prompt_path = _audit_root() / run_id / "prompt.txt"
    summary["prompt"] = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    return summary


@router.get("/diy-runs")
async def list_diy_runs():
    root = Path("generated/diy-audit")
    if not root.exists():
        return {"runs": []}
    summaries = []
    for path in root.glob("*/request_summary.json"):
        try:
            summaries.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    runs = [summary for summary in summaries if summary.get("id")]
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"runs": runs}


@router.get("/diy-runs/{run_id}")
async def get_diy_run(run_id: str):
    path = Path("generated/diy-audit") / run_id / "request_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="DIY测试记录不存在")
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read DIY run: {exc}")
    return summary
