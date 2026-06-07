import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_DIR = Path(__file__).resolve().parents[2] / "generated" / "user-history"
MAX_HISTORY_ITEMS = 80


def _safe_user_id(user_id: str | None) -> str:
    value = (user_id or "anonymous").strip()
    value = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    return value[:80] or "anonymous"


def append_history_record(user_id: str | None, kind: str, record: dict[str, Any]) -> dict[str, Any]:
    safe_user_id = _safe_user_id(user_id)
    user_dir = HISTORY_DIR / safe_user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    record = {
        **record,
        "kind": kind,
        "user_id": safe_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    history_path = user_dir / f"{kind}-history.json"
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            history = []
    else:
        history = []

    if not isinstance(history, list):
        history = []

    history.insert(0, record)
    history = history[:MAX_HISTORY_ITEMS]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    (user_dir / f"{kind}-latest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
