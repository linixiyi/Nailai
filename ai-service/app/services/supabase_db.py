import asyncio
import os
import json
import httpx
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable
from app.config import settings

logger = logging.getLogger(__name__)

GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated"

# ── 共享连接池 ──────────────────────────────────────
# 全局复用 httpx client，避免每次调用重建连接。
# 超时：连接 10s，读取 15s，写入 15s（生图接口可能更慢，此处仅用于 Supabase CRUD）。
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is not None and not _client.is_closed:
        return _client
    async with _client_lock:
        if _client is not None and not _client.is_closed:
            return _client
        _client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
            timeout=httpx.Timeout(connect=10.0, read=15.0, write=15.0, pool=5.0),
        )
        return _client


# ── 轻量重试 ────────────────────────────────────────
# 不使用 tenacity，避免额外依赖。仅对网络错误和 5xx 重试，最多 3 次。

async def _with_retry(
    fn: Callable[..., Awaitable[httpx.Response]],
    *args: Any,
    max_retries: int = 3,
    **kwargs: Any,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = await fn(*args, **kwargs)
            # 5xx 服务端错误可重试；4xx 客户端错误不重试
            if resp.status_code < 500:
                return resp
            logger.debug("Supabase returned %d, retrying (%d/%d)", resp.status_code, attempt + 1, max_retries)
        except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            logger.debug("Supabase request failed (attempt %d/%d): %s", attempt + 1, max_retries, exc)
        except Exception:
            raise  # 非网络错误直接抛出

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # 1s → 2s → 4s

    if last_exc:
        raise last_exc
    return resp  # 最后一次尝试仍返回 5xx


async def _supabase_get(path: str, timeout: float = 10.0) -> httpx.Response:
    client = await _get_client()
    return await _with_retry(
        client.get,
        path,
        headers=_get_supabase_headers(),
        timeout=timeout,
    )


async def _supabase_post(path: str, json_data: dict, timeout: float = 10.0, extra_headers: dict | None = None) -> httpx.Response:
    client = await _get_client()
    headers = _get_supabase_headers()
    if extra_headers:
        headers = {**headers, **extra_headers}
    return await _with_retry(
        client.post,
        path,
        json=json_data,
        headers=headers,
        timeout=timeout,
    )


async def _supabase_patch(path: str, json_data: dict, timeout: float = 10.0) -> httpx.Response:
    client = await _get_client()
    return await _with_retry(
        client.patch,
        path,
        json=json_data,
        headers=_get_supabase_headers(),
        timeout=timeout,
    )

def _ensure_dir():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Supabase REST configurations
def _get_supabase_headers():
    api_key = settings.supabase_service_role_key or settings.supabase_anon_key or settings.next_public_supabase_anon_key or ""
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

# --- SHIPS / SHOPS ---
DEFAULT_SHOP_INFO = {
    "id": "library-nail-spa-futian",
    "name": "Library Nail Spa (福田星河COCO Park店)",
    "address": "福田区福华三路星河COCO Park三楼",
    "longitude": 114.053878,
    "latitude": 22.53589,
    "rating": 4.8,
    "contact": {"phone": "13800000000", "wechat": "coco_nail_spa"},
    "facilities": {"wifi": True, "parking": True, "tea": True, "private_room": False},
    "active_score": 0.95,
    "wait_time": "无需等待",
    "schedule": "排期充裕"
}

async def get_shop_info() -> dict[str, Any]:
    url = settings.supabase_url or settings.next_public_supabase_url
    if not url:
        return _get_local_shop_info()
    
    try:
        resp = await _supabase_get(
            f"{url.rstrip('/')}/rest/v1/shops?id=eq.library-nail-spa-futian"
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list):
                return data[0]
    except Exception:
        logger.debug("Supabase unavailable, falling back to local storage")
    return _get_local_shop_info()

def _get_local_shop_info() -> dict[str, Any]:
    _ensure_dir()
    path = GENERATED_DIR / "shop-info-db.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
    return DEFAULT_SHOP_INFO

async def update_shop_info(
    name: str,
    address: str,
    active_score: float,
    wait_time: str = "无需等待",
    schedule: str = "排期充裕",
    facilities: dict = None
) -> dict[str, Any]:
    url = settings.supabase_url or settings.next_public_supabase_url
    payload = {
        "name": name,
        "address": address,
        "active_score": active_score,
        "wait_time": wait_time,
        "schedule": schedule,
        "facilities": facilities or {"wifi": True, "parking": True, "tea": True, "private_room": False}
    }
    
    if url:
        try:
            resp = await _supabase_post(
                f"{url.rstrip('/')}/rest/v1/shops",
                {**DEFAULT_SHOP_INFO, **payload},
                extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                if data:
                    return data[0]
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
            
    # Fallback to local
    _ensure_dir()
    path = GENERATED_DIR / "shop-info-db.json"
    current = {**_get_local_shop_info(), **payload}
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


# --- BOUNTIES ---
DEFAULT_BOUNTIES = [
    {
        "id": "bounty-crystal-long",
        "title": "钻饰豹纹长甲复刻",
        "budget": "¥250-350",
        "status": "竞价中",
        "image": "/modao-assets/bounty-013.png",
        "participants": 8,
        "deadline": "2天后截止",
        "description": "想保留透明长甲、银色细闪、豹纹斑点和钻饰，可按手型微调。"
    },
    {
        "id": "bounty-black-star",
        "title": "黑色星星长甲改良",
        "budget": "¥200-300",
        "status": "待确认",
        "image": "/modao-assets/bounty-011.png",
        "participants": 5,
        "deadline": "明晚截止",
        "description": "保留黑色亮面、裸透底和星星元素，希望更适合日常拍照。"
    },
    {
        "id": "bounty-silver-leopard",
        "title": "银闪豹纹尖甲复刻",
        "budget": "¥250-350",
        "status": "竞价中",
        "image": "/modao-assets/bounty-010.png",
        "participants": 12,
        "deadline": "3天后截止",
        "description": "复刻银色渐变、豹纹点缀和尖形长甲，要求饰品位置自然。"
    }
]

async def list_bounties() -> list[dict[str, Any]]:
    url = settings.supabase_url or settings.next_public_supabase_url
    if url:
        try:
            resp = await _supabase_get(
                f"{url.rstrip('/')}/rest/v1/bounties?order=created_at.desc"
            )
            if resp.status_code == 200:
                db_data = resp.json()
                seen_ids = {b["id"] for b in db_data}
                merged = list(db_data)
                for b in DEFAULT_BOUNTIES:
                    if b["id"] not in seen_ids:
                        merged.append(b)
                return merged
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
            
    # Fallback to local
    _ensure_dir()
    path = GENERATED_DIR / "diy-bounties-db.json"
    if path.exists():
        try:
            local_bounties = json.loads(path.read_text(encoding="utf-8"))
            seen_ids = {b["id"] for b in local_bounties}
            merged = list(local_bounties)
            for b in DEFAULT_BOUNTIES:
                if b["id"] not in seen_ids:
                    merged.append(b)
            return merged
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
    return DEFAULT_BOUNTIES

async def publish_bounty(bounty_data: dict[str, Any]) -> dict[str, Any]:
    url = settings.supabase_url or settings.next_public_supabase_url
    bounty_data = {
        "participants": 0,
        "deadline": "3天后截止",
        "status": "待接单",
        **bounty_data
    }
    
    if url:
        try:
            resp = await _supabase_post(
                f"{url.rstrip('/')}/rest/v1/bounties",
                bounty_data,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                if data:
                    return data[0]
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
            
    # Fallback to local
    _ensure_dir()
    path = GENERATED_DIR / "diy-bounties-db.json"
    local_bounties = []
    if path.exists():
        try:
            local_bounties = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
    local_bounties = [bounty_data] + [b for b in local_bounties if b["id"] != bounty_data["id"]]
    path.write_text(json.dumps(local_bounties, ensure_ascii=False, indent=2), encoding="utf-8")
    return bounty_data

async def accept_bounty(bounty_id: str, shop_id: str) -> Optional[dict[str, Any]]:
    url = settings.supabase_url or settings.next_public_supabase_url
    if url:
        try:
            resp = await _supabase_patch(
                f"{url.rstrip('/')}/rest/v1/bounties?id=eq.{bounty_id}",
                {"status": "已接单", "shop_id": shop_id, "participants": 1},
            )
            if resp.status_code in [200, 204]:
                read_resp = await _supabase_get(
                    f"{url.rstrip('/')}/rest/v1/bounties?id=eq.{bounty_id}",
                    timeout=5.0,
                )
                if read_resp.status_code == 200:
                    data = read_resp.json()
                    if data:
                        return data[0]
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
            
    # Fallback to local
    _ensure_dir()
    path = GENERATED_DIR / "diy-bounties-db.json"
    bounties_list = await list_bounties()
    found = None
    for b in bounties_list:
        if b["id"] == bounty_id:
            b["status"] = "已接单"
            b["shop_id"] = shop_id
            b["participants"] = 1
            found = b
            break
            
    if found:
        path.write_text(json.dumps(bounties_list, ensure_ascii=False, indent=2), encoding="utf-8")
    return found


# --- STYLE UPLOADING ---
async def save_uploaded_style(style_data: dict[str, Any], shop_id: str) -> bool:
    if "is_active" not in style_data:
        style_data["is_active"] = True
    url = settings.supabase_url or settings.next_public_supabase_url
    if url:
        try:
            style_resp = await _supabase_post(
                f"{url.rstrip('/')}/rest/v1/nail_styles",
                style_data,
            )
            if style_resp.status_code in [200, 201]:
                await _supabase_post(
                    f"{url.rstrip('/')}/rest/v1/shop_styles",
                    {"shop_id": shop_id, "style_id": style_data["id"]},
                )
                return True
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
            
    # Fallback to local
    _ensure_dir()
    path = GENERATED_DIR / "custom-styles-db.json"
    custom_styles = []
    if path.exists():
        try:
            custom_styles = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
    custom_styles.append(style_data)
    path.write_text(json.dumps(custom_styles, ensure_ascii=False, indent=2), encoding="utf-8")
    return True

def get_custom_local_styles_sync() -> list[dict[str, Any]]:
    path = GENERATED_DIR / "custom-styles-db.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Supabase/local storage operation failed, using fallback")
    return []

async def get_custom_local_styles() -> list[dict[str, Any]]:
    return get_custom_local_styles_sync()

async def update_style_active_status(style_id: str, is_active: bool) -> bool:
    url = settings.supabase_url or settings.next_public_supabase_url
    success = False
    if url:
        try:
            resp = await _supabase_patch(
                f"{url.rstrip('/')}/rest/v1/nail_styles?id=eq.{style_id}",
                {"is_active": is_active}
            )
            if resp.status_code in [200, 204]:
                success = True
        except Exception as e:
            logger.debug(f"Failed to update style status on Supabase: {e}")
            
    # Always sync to local file for fallback consistency
    _ensure_dir()
    path = GENERATED_DIR / "custom-styles-db.json"
    if path.exists():
        try:
            custom_styles = json.loads(path.read_text(encoding="utf-8"))
            updated = False
            for cs in custom_styles:
                if cs.get("id") == style_id:
                    cs["is_active"] = is_active
                    updated = True
                    break
            if updated:
                path.write_text(json.dumps(custom_styles, ensure_ascii=False, indent=2), encoding="utf-8")
                success = True
        except Exception as e:
            logger.debug(f"Failed to update style status locally: {e}")
    return success

async def increment_style_analytics(style_id: str, metric: str) -> bool:
    if metric not in ["views", "try_ons", "interests", "bookings"]:
        return False
        
    url = settings.supabase_url or settings.next_public_supabase_url
    success = False
    
    if url:
        try:
            # 1. Try to read current analytics row
            read_resp = await _supabase_get(
                f"{url.rstrip('/')}/rest/v1/style_analytics?style_id=eq.{style_id}"
            )
            current_val = 0
            row_exists = False
            row_data = {}
            if read_resp.status_code == 200:
                data = read_resp.json()
                if data and isinstance(data, list):
                    row_data = data[0]
                    current_val = row_data.get(metric, 0)
                    row_exists = True
            
            # 2. Increment the metric
            row_data[metric] = current_val + 1
            row_data["style_id"] = style_id
            from datetime import datetime, timezone
            row_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            if row_exists:
                write_resp = await _supabase_patch(
                    f"{url.rstrip('/')}/rest/v1/style_analytics?style_id=eq.{style_id}",
                    {"views": row_data.get("views", 0), "try_ons": row_data.get("try_ons", 0), "interests": row_data.get("interests", 0), "bookings": row_data.get("bookings", 0), "updated_at": row_data["updated_at"]}
                )
            else:
                # Set default values for other metrics
                for key in ["views", "try_ons", "interests", "bookings"]:
                    if key not in row_data:
                        row_data[key] = 0
                row_data[metric] = 1
                write_resp = await _supabase_post(
                    f"{url.rstrip('/')}/rest/v1/style_analytics",
                    row_data
                )
                
            if write_resp.status_code in [200, 201, 204]:
                success = True
        except Exception as e:
            logger.debug(f"Failed to increment style analytics on Supabase: {e}")
            
    # Always sync to local file for fallback consistency
    _ensure_dir()
    path = GENERATED_DIR / "style-analytics-db.json"
    analytics_db = {}
    if path.exists():
        try:
            analytics_db = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            analytics_db = {}
            
    if style_id not in analytics_db:
        analytics_db[style_id] = {"views": 0, "try_ons": 0, "interests": 0, "bookings": 0}
        
    analytics_db[style_id][metric] = analytics_db[style_id].get(metric, 0) + 1
    try:
        path.write_text(json.dumps(analytics_db, ensure_ascii=False, indent=2), encoding="utf-8")
        success = True
    except Exception as e:
        logger.debug(f"Failed to write style analytics locally: {e}")
        
    return success

async def get_style_analytics(style_id: str) -> dict[str, int]:
    import hashlib
    h = int(hashlib.md5(style_id.encode("utf-8")).hexdigest(), 16)
    default_views = (h % 150) + 50
    default_try_ons = (h % 30) + 10
    default_interests = (h % 15) + 3
    default_bookings = (h % 5) + 1
    
    url = settings.supabase_url or settings.next_public_supabase_url
    db_data = {}
    if url:
        try:
            resp = await _supabase_get(
                f"{url.rstrip('/')}/rest/v1/style_analytics?style_id=eq.{style_id}"
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    db_data = data[0]
        except Exception as e:
            logger.debug(f"Failed to fetch style analytics from Supabase: {e}")
            
    local_data = {}
    _ensure_dir()
    path = GENERATED_DIR / "style-analytics-db.json"
    if path.exists():
        try:
            analytics_db = json.loads(path.read_text(encoding="utf-8"))
            local_data = analytics_db.get(style_id, {})
        except Exception:
            pass
            
    views = db_data.get("views", local_data.get("views", default_views))
    try_ons = db_data.get("try_ons", local_data.get("try_ons", default_try_ons))
    interests = db_data.get("interests", local_data.get("interests", default_interests))
    bookings = db_data.get("bookings", local_data.get("bookings", default_bookings))
    
    return {
        "views": views,
        "try_ons": try_ons,
        "interests": interests,
        "bookings": bookings
    }

async def get_all_style_analytics() -> dict[str, dict[str, int]]:
    url = settings.supabase_url or settings.next_public_supabase_url
    db_all = {}
    if url:
        try:
            resp = await _supabase_get(
                f"{url.rstrip('/')}/rest/v1/style_analytics"
            )
            if resp.status_code == 200:
                rows = resp.json()
                if isinstance(rows, list):
                    for row in rows:
                        sid = row.get("style_id")
                        if sid:
                            db_all[sid] = {
                                "views": row.get("views", 0),
                                "try_ons": row.get("try_ons", 0),
                                "interests": row.get("interests", 0),
                                "bookings": row.get("bookings", 0)
                            }
        except Exception as e:
            logger.debug(f"Failed to fetch all style analytics from Supabase: {e}")
            
    local_all = {}
    _ensure_dir()
    path = GENERATED_DIR / "style-analytics-db.json"
    if path.exists():
        try:
            local_all = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    merged = {}
    all_style_ids = set(db_all.keys()) | set(local_all.keys())
    for sid in all_style_ids:
        import hashlib
        h = int(hashlib.md5(sid.encode("utf-8")).hexdigest(), 16)
        default_views = (h % 150) + 50
        default_try_ons = (h % 30) + 10
        default_interests = (h % 15) + 3
        default_bookings = (h % 5) + 1
        
        db_s = db_all.get(sid, {})
        local_s = local_all.get(sid, {})
        
        merged[sid] = {
            "views": db_s.get("views", local_s.get("views", default_views)),
            "try_ons": db_s.get("try_ons", local_s.get("try_ons", default_try_ons)),
            "interests": db_s.get("interests", local_s.get("interests", default_interests)),
            "bookings": db_s.get("bookings", local_s.get("bookings", default_bookings)),
        }
    return merged


# ── 优雅关闭 ─────────────────────────────────────────
async def close_client():
    """关闭共享连接池，在 FastAPI shutdown 事件中调用。"""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None
        logger.debug("Supabase client closed")
