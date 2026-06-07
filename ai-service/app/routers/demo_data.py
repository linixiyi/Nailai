from fastapi import APIRouter
import asyncio
import base64
import json
from io import BytesIO
from pathlib import Path
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 数据加载 ──────────────────────────────────────────
# 优先从 JSON 配置文件加载，缺失时回退到内联常量。
# JSON 文件路径相对于 ai-service/ 根目录。

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_json_data(filename: str, fallback: list[dict]) -> list[dict]:
    """从 data/ 目录加载 JSON，失败时使用 fallback。"""
    path = _DATA_DIR / filename
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
    except Exception:
        logger.debug("Failed to load %s, using fallback data", filename)
    return fallback


SHOPS = _load_json_data("shops.json", [
    {
        "id": "celins-nail-futian",
        "name": "Celins Nail瑟琳日式美甲美睫",
        "distance": "1.8km",
        "rating": 4.8,
        "price": "¥158+",
        "address": "福田区福华三路88号财富大厦15C",
        "image": "/modao-assets/modao-14.jpg",
        "tags": ["会展中心", "日系", "高空环境"],
        "availableStyles": ["library-20260514-001", "library-20260514-002", "library-20260514-003"],
    },
    {
        "id": "orchid-zhiguo-gangxia",
        "name": "兰花芷国风·美甲美睫",
        "distance": "2.1km",
        "rating": 4.7,
        "price": "¥168+",
        "address": "福田区岗厦城E座1606室",
        "image": "/modao-assets/modao-19.jpg",
        "tags": ["国风", "咬残甲修复", "岗厦"],
        "availableStyles": ["library-20260514-005", "library-20260514-012", "library-20260514-017"],
    },
    {
        "id": "franli-jinzhonghuan",
        "name": "法兰黎美甲美睫",
        "distance": "2.4km",
        "rating": 4.9,
        "price": "¥128+",
        "address": "福田区金田路3037号金中环商务大厦A座1131室",
        "image": "/modao-assets/modao-17.jpg",
        "tags": ["短甲友好", "来图还原", "会展中心"],
        "availableStyles": ["library-20260514-004", "library-20260514-010", "library-20260514-021"],
    },
    {
        "id": "yehe-chegongmiao",
        "name": "野禾美睫美甲艺术研究院",
        "distance": "3.0km",
        "rating": 4.8,
        "price": "¥138+",
        "address": "福田区深南大道6007号创建大厦A座1508室",
        "image": "/modao-assets/modao-22.jpg",
        "tags": ["车公庙", "轻奢", "建构塑形"],
        "availableStyles": ["library-20260514-006", "library-20260514-014", "library-20260514-024"],
    },
    {
        "id": "huaqi-nail-mixc",
        "name": "花岐美甲HUAQI Nail",
        "distance": "5.8km",
        "rating": 4.8,
        "price": "¥167+",
        "address": "南山区大冲新城花园2栋1D座2512室",
        "image": "/modao-assets/modao-20.jpg",
        "tags": ["万象天地", "日式流程", "开店14年"],
        "availableStyles": ["library-20260514-008", "library-20260514-018", "library-20260514-030"],
    },
    {
        "id": "pink-panda-mixc-world",
        "name": "Pink Panda美甲美睫",
        "distance": "6.2km",
        "rating": 4.7,
        "price": "¥300/人",
        "address": "南山区深南大道大冲万象天地华润置地大厦E座27楼B",
        "image": "/modao-assets/modao-23.jpg",
        "tags": ["万象天地", "客制化", "设计感空间"],
        "availableStyles": ["library-20260514-011", "library-20260514-023", "library-20260514-032"],
    },
])

BOUNTIES = _load_json_data("bounties.json", [
    {
        "id": "bounty-crystal-long",
        "title": "钻饰豹纹长甲复刻",
        "budget": "¥250-350",
        "status": "竞价中",
        "image": "/modao-assets/bounty-013.png",
        "participants": 8,
        "deadline": "2天后截止",
        "description": "想保留透明长甲、银色细闪、豹纹斑点和钻饰，可按手型微调。",
    },
    {
        "id": "bounty-black-star",
        "title": "黑色星星长甲改良",
        "budget": "¥200-300",
        "status": "待确认",
        "image": "/modao-assets/bounty-011.png",
        "participants": 5,
        "deadline": "明晚截止",
        "description": "保留黑色亮面、裸透底和星星元素，希望更适合日常拍照。",
    },
    {
        "id": "bounty-silver-leopard",
        "title": "银闪豹纹尖甲复刻",
        "budget": "¥250-350",
        "status": "竞价中",
        "image": "/modao-assets/bounty-010.png",
        "participants": 12,
        "deadline": "3天后截止",
        "description": "复刻银色渐变、豹纹点缀和尖形长甲，要求饰品位置自然。",
    },
])

TASKS = [
    {
        "id": "task-001",
        "customer": "Coco",
        "styleName": "极光蝴蝶",
        "price": "¥218",
        "distance": "3.2km",
        "status": "待抢单",
        "image": "/modao-assets/modao-05.jpg",
    },
    {
        "id": "task-002",
        "customer": "小林",
        "styleName": "清透法式",
        "price": "¥168",
        "distance": "2.4km",
        "status": "可接单",
        "image": "/modao-assets/modao-01.jpg",
    },
    {
        "id": "task-003",
        "customer": "Mia",
        "styleName": "彩虹琉璃",
        "price": "¥258",
        "distance": "5.1km",
        "status": "竞价中",
        "image": "/modao-assets/modao-22.jpg",
    },
]


@router.get("/shops")
async def shops():
    from app.services.supabase_db import get_shop_info, get_custom_local_styles
    merchant_shop = await get_shop_info()

    merchant_mapped = {
        "id": merchant_shop.get("id", "library-nail-spa-futian"),
        "name": merchant_shop.get("name", "Library Nail Spa (福田星河COCO Park店)"),
        "distance": "1.2km",
        "rating": merchant_shop.get("rating", 4.8),
        "price": "¥158+",
        "address": merchant_shop.get("address", "福田区福华三路星河COCO Park三楼"),
        "image": "/modao-assets/modao-14.jpg",
        "tags": ["推荐", "AI提取款", "星河COCO Park"],
        "availableStyles": ["aurora-holo", "clean-french"],
        "wait_time": merchant_shop.get("wait_time", "无需等待"),
        "schedule": merchant_shop.get("schedule", "排期充裕"),
        "facilities": merchant_shop.get("facilities", {"wifi": True, "parking": True, "tea": True, "private_room": False})
    }

    custom_styles = await get_custom_local_styles()
    for s in custom_styles:
        if s["id"] not in merchant_mapped["availableStyles"]:
            merchant_mapped["availableStyles"].append(s["id"])

    result_shops = [merchant_mapped]

    for s in SHOPS:
        s_copy = dict(s)
        if s_copy["id"] == merchant_mapped["id"]:
            continue
        if "wait_time" not in s_copy:
            s_copy["wait_time"] = "排队约15分钟" if s_copy["id"] == "celins-nail-futian" else "无需等待"
        if "schedule" not in s_copy:
            s_copy["schedule"] = "今日已约满" if s_copy["id"] == "celins-nail-futian" else "排期充裕"
        if "facilities" not in s_copy:
            s_copy["facilities"] = {
                "wifi": True,
                "parking": True if s_copy["id"] != "orchid-zhiguo-gangxia" else False,
                "tea": True if s_copy["id"] in ["celins-nail-futian", "yehe-chegongmiao"] else False,
                "private_room": True if s_copy["id"] == "pink-panda-mixc-world" else False
            }
        result_shops.append(s_copy)

    return {"shops": result_shops}


@router.get("/bounties")
async def bounties():
    from app.services.supabase_db import list_bounties
    data = await list_bounties()
    return {"bounties": data}


@router.get("/store/tasks")
async def store_tasks():
    from app.services.supabase_db import list_bounties
    bounties_list = await list_bounties()
    tasks_list = []
    for b in bounties_list:
        tasks_list.append({
            "id": b["id"],
            "customer": "顾客 " + b["id"][-4:] if "-" in b["id"] else "用户",
            "styleName": b["title"],
            "price": b["budget"],
            "distance": "1.5km" if "aurora" in b["id"] else ("2.3km" if "pearl" in b["id"] else "3.2km"),
            "status": "待抢单" if b["status"] == "待接单" else b["status"],
            "image": b["image"],
            "description": b.get("description", "")
        })
    return {"tasks": tasks_list}


from fastapi import File, UploadFile, Form, HTTPException
from uuid import uuid4
from pathlib import Path
from PIL import Image
from app.services.supabase_db import get_shop_info, update_shop_info, accept_bounty, save_uploaded_style
from app.services.style_vision_analyzer import analyze_nail_style_image
from app.services.image2_client import _ensure_data_url, _extract_gpt_image2_result
from app.services.nail_segmenter import segment_nails
from app.services.nail_taxonomy import LENGTH_MAP
from app.config import settings

_GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated"
_CUSTOM_STYLE_DIR = _GENERATED_DIR / "custom-styles"
_CUSTOM_STYLE_DRAFTS_PATH = _GENERATED_DIR / "custom-style-drafts.json"

@router.get("/store/shop-info")
async def get_store_shop_info():
    info = await get_shop_info()
    return info

@router.post("/store/shop-info")
async def post_store_shop_info(payload: dict):
    name = payload.get("name", "Library Nail Spa")
    address = payload.get("address", "")
    active_score = float(payload.get("active_score", 0.95))
    wait_time = payload.get("wait_time", "无需等待")
    schedule = payload.get("schedule", "排期充裕")
    facilities = payload.get("facilities", {"wifi": True, "parking": True, "tea": True, "private_room": False})
    updated = await update_shop_info(name, address, active_score, wait_time, schedule, facilities)
    return updated

@router.post("/store/bounties/{bounty_id}/accept")
async def accept_diy_bounty(bounty_id: str, payload: dict):
    shop_id = payload.get("shop_id", "library-nail-spa-futian")
    result = await accept_bounty(bounty_id, shop_id)
    if not result:
        raise HTTPException(status_code=404, detail="Bounty not found")
    return result

def extract_taxonomy_from_text(name: str, description: str = "") -> dict[str, list[str]]:
    text = (name + " " + description).lower()
    colors_map = {
        "粉": "粉色系", "红": "红色系", "黑": "黑色系", "白": "白色系", "灰": "灰色系",
        "绿": "绿色系", "蓝": "蓝色系", "金": "金属色系", "银": "金属色系", "裸": "裸色系",
        "大地": "大地色系", "咖": "大地色系", "茶": "大地色系", "黄": "彩色", "紫": "彩色",
        "彩色": "彩色", "多色": "多色"
    }
    techniques_map = {
        "手绘": "手绘", "花": "花卉", "立体": "立体花", "法式": "法式", "钻": "钻饰",
        "宝石": "宝石", "珍珠": "珍珠", "猫眼": "猫眼", "魔镜": "魔镜", "极光": "极光",
        "亮片": "亮片", "闪": "闪粉", "爆闪": "爆闪", "渐变": "渐变", "腮红": "腮红",
        "冰透": "冰透", "纯色": "纯色", "跳色": "跳色", "几何": "几何", "动物": "动物纹"
    }
    shapes_map = {
        "方圆": "方圆型", "尖": "尖型", "杏仁": "杏仁型", "梯": "梯型", "圆": "圆形", "椭圆": "椭圆型"
    }
    styles_map = {
        "复古": "复古", "老钱": "老钱", "莫兰迪": "莫兰迪", "日系": "日系", "清新": "清新",
        "可爱": "可爱", "欧美": "欧美", "辣妹": "辣妹", "y2k": "Y2K", "奢华": "奢华",
        "巴洛克": "巴洛克", "千金": "千金", "仙气": "仙气", "温柔": "温柔", "梦幻": "梦幻",
        "极简": "极简", "冷淡": "冷淡", "ins": "INS", "暗黑": "暗黑", "朋克": "朋克",
        "酷": "酷感", "轻奢": "轻奢", "气质": "气质", "高级": "高级感"
    }
    occasions_map = {
        "日常": "日常", "通勤": "通勤", "上班": "通勤", "约会": "约会", "婚礼": "婚礼",
        "新娘": "新娘", "宴会": "宴会", "派对": "派对", "蹦迪": "蹦迪", "晚宴": "晚宴",
        "节日": "节日", "新年": "新年", "圣诞": "圣诞", "度假": "度假", "清凉": "清凉",
        "春": "春夏", "夏": "春夏", "秋": "秋冬", "冬": "秋冬"
    }
    lengths_map = {
        "短": "短款", "中长": "中长款", "长": "长款"
    }

    extracted = {
        "colors": [],
        "techniques": [],
        "shapes": [],
        "styles": [],
        "occasions": [],
        "lengths": []
    }
    for kw, val in colors_map.items():
        if kw in text:
            extracted["colors"].append(val)
    for kw, val in techniques_map.items():
        if kw in text:
            extracted["techniques"].append(val)
    for kw, val in shapes_map.items():
        if kw in text:
            extracted["shapes"].append(val)
    for kw, val in styles_map.items():
        if kw in text:
            extracted["styles"].append(val)
    for kw, val in occasions_map.items():
        if kw in text:
            extracted["occasions"].append(val)
    for kw, val in lengths_map.items():
        if kw in text:
            extracted["lengths"].append(val)

    for k in extracted:
        extracted[k] = list(dict.fromkeys(extracted[k]))

    if not extracted["colors"]:
        extracted["colors"] = ["裸色系"]
    if not extracted["techniques"]:
        extracted["techniques"] = ["纯色"]
    if not extracted["shapes"]:
        extracted["shapes"] = ["方圆型"]
    if not extracted["styles"]:
        extracted["styles"] = ["温柔"]
    if not extracted["occasions"]:
        extracted["occasions"] = ["日常"]
    if not extracted["lengths"]:
        extracted["lengths"] = ["短款"]
    return extracted


def _ensure_custom_style_storage() -> None:
    _CUSTOM_STYLE_DIR.mkdir(parents=True, exist_ok=True)
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _load_custom_style_drafts() -> list[dict[str, Any]]:
    if _CUSTOM_STYLE_DRAFTS_PATH.exists():
        try:
            raw = json.loads(_CUSTOM_STYLE_DRAFTS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
        except Exception:
            logger.warning("Failed to read custom style drafts, resetting local draft store")
    return []


def _save_custom_style_drafts(drafts: list[dict[str, Any]]) -> None:
    _ensure_custom_style_storage()
    _CUSTOM_STYLE_DRAFTS_PATH.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")


def _upsert_custom_style_draft(draft: dict[str, Any]) -> None:
    drafts = _load_custom_style_drafts()
    draft_id = draft.get("draft_id")
    filtered = [item for item in drafts if item.get("draft_id") != draft_id]
    filtered.append(draft)
    _save_custom_style_drafts(filtered)


def _get_custom_style_draft(draft_id: str) -> dict[str, Any] | None:
    return next((item for item in _load_custom_style_drafts() if item.get("draft_id") == draft_id), None)


def _delete_custom_style_draft(draft_id: str) -> None:
    drafts = _load_custom_style_drafts()
    filtered = [item for item in drafts if item.get("draft_id") != draft_id]
    if len(filtered) != len(drafts):
        _save_custom_style_drafts(filtered)


def _dedupe_tokens(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip() if isinstance(value, str) else ""
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _parse_price_level(price: str) -> str:
    price_level = "¥¥"
    try:
        val = int("".join(c for c in str(price) if c.isdigit()))
        if val > 250:
            price_level = "¥¥¥"
        elif val < 100:
            price_level = "¥"
    except Exception:
        logger.debug("Failed to parse price, using default price level")
    return price_level


def _normalize_taxonomy(payload: dict[str, Any] | None) -> dict[str, list[str]]:
    dimensions = ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]
    normalized: dict[str, list[str]] = {}
    for key in dimensions:
        raw = payload.get(key, []) if isinstance(payload, dict) else []
        if not isinstance(raw, list):
            raw = [raw] if raw else []
        normalized[key] = _dedupe_tokens([str(item) for item in raw])
    return normalized


def _merge_taxonomy(selected_taxonomy: dict[str, Any] | None, custom_tags_by_dimension: dict[str, Any] | None) -> dict[str, list[str]]:
    base = _normalize_taxonomy(selected_taxonomy)
    custom = _normalize_taxonomy(custom_tags_by_dimension)
    return {key: _dedupe_tokens([*base[key], *custom[key]]) for key in base}


def _taxonomy_length_to_code(taxonomy: dict[str, list[str]], fallback: str = "natural") -> str:
    for item in taxonomy.get("lengths", []):
        if item in LENGTH_MAP:
            return LENGTH_MAP[item]
    return fallback


def _taxonomy_length_label(taxonomy: dict[str, list[str]], fallback: str = "短款") -> str:
    return taxonomy.get("lengths", [fallback])[0] if taxonomy.get("lengths") else fallback


def _clear_style_catalog_cache() -> None:
    import app.services.style_catalog as style_cat
    style_cat._STYLE_CACHE = None


async def _persist_design_image_url(asset_id: str, design_image_url: str) -> str:
    normalized = (design_image_url or "").strip()
    if not normalized:
        return normalized
    if normalized.startswith("/generated/custom-styles/"):
        return normalized
    if normalized.startswith("data:image"):
        raw = base64.b64decode(normalized.split(",", 1)[1])
    elif normalized.startswith("http://") or normalized.startswith("https://"):
        timeout = httpx.Timeout(
            connect=min(15.0, settings.image2_timeout_seconds),
            write=min(30.0, settings.image2_timeout_seconds),
            read=min(60.0, settings.image2_timeout_seconds),
            pool=min(15.0, settings.image2_timeout_seconds),
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(normalized)
            response.raise_for_status()
            raw = response.content
    else:
        return normalized

    if not raw:
        raise ValueError("design image download returned empty content")

    _ensure_custom_style_storage()
    design_filename = f"{asset_id}-design.png"
    design_file_path = _CUSTOM_STYLE_DIR / design_filename
    design_file_path.write_bytes(raw)
    return f"/generated/custom-styles/{design_filename}"


async def _generate_style_render_assets(
    *,
    asset_id: str,
    source_filename_stem: str,
    source_extension: str,
    image_bytes: bytes,
    name: str,
    color: str,
    finish: str,
    nail_length_label: str,
) -> dict[str, str | None]:
    _ensure_custom_style_storage()
    source_filename = f"{source_filename_stem}.{source_extension}"
    source_file_path = _CUSTOM_STYLE_DIR / source_filename
    source_file_path.write_bytes(image_bytes)
    source_image_url = f"/generated/custom-styles/{source_filename}"

    async def generate_design_render() -> tuple[str | None, str, str | None]:
        def extract_task_id(payload: dict[str, Any]) -> str | None:
            candidates = [
                payload.get("task_id"),
                payload.get("id"),
                payload.get("task", {}).get("task_id") if isinstance(payload.get("task"), dict) else None,
                payload.get("task", {}).get("id") if isinstance(payload.get("task"), dict) else None,
                payload.get("output", {}).get("task_id") if isinstance(payload.get("output"), dict) else None,
                payload.get("result", {}).get("task_id") if isinstance(payload.get("result"), dict) else None,
            ]
            for candidate in candidates:
                if isinstance(candidate, str) and candidate:
                    return candidate
            return None

        def extract_status(payload: dict[str, Any]) -> str | None:
            candidates = [
                payload.get("status"),
                payload.get("task", {}).get("status") if isinstance(payload.get("task"), dict) else None,
                payload.get("output", {}).get("status") if isinstance(payload.get("output"), dict) else None,
                payload.get("result", {}).get("status") if isinstance(payload.get("result"), dict) else None,
            ]
            for candidate in candidates:
                if isinstance(candidate, str) and candidate:
                    return candidate.lower()
            return None

        prompt = (
            "将输入图重绘为“纯美甲片设计图”，必须剥离手部和背景，只保留甲片元素。"
            "要求：浅色纯背景，甲片整齐展示，主体清晰，不要手、不要人物、不要道具、不要文字、不要水印。"
            "保持原款颜色、图案、材质和甲型，生成电商上架用设计图。"
            f"款式名：{name}；主色：{color}；工艺：{finish}；甲长：{nail_length_label}。"
        )

        source_data_url = _ensure_data_url(image_bytes)
        endpoint = settings.gpt_image2_api_url
        api_key = settings.gpt_image2_api_key or settings.image2_api_key
        if not endpoint or not api_key:
            return None, "gpt-image2-style-render", "no_provider_configured"

        payload = {
            "n": 1,
            "image": source_data_url,
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "low",
            "background": "opaque",
            "output_format": "png",
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            timeout = httpx.Timeout(
                connect=min(20.0, settings.image2_timeout_seconds),
                write=min(120.0, settings.image2_timeout_seconds),
                read=settings.image2_timeout_seconds,
                pool=min(20.0, settings.image2_timeout_seconds),
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                submit_error: Exception | None = None
                body: dict[str, Any] | None = None
                for attempt in range(3):
                    try:
                        response = await client.post(endpoint, json=payload, headers=headers)
                        if response.status_code >= 400:
                            raise ValueError(f"GPT image2 request failed ({response.status_code}): {response.text[:400]}")
                        body = response.json()
                        break
                    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
                        submit_error = exc
                        logger.warning(
                            "Merchant style GPT image2 submit failed: attempt=%s endpoint=%s error=%s",
                            attempt + 1,
                            endpoint,
                            exc,
                        )
                        if attempt == 2:
                            raise
                        await asyncio.sleep(2 * (attempt + 1))

                if body is None:
                    raise submit_error or RuntimeError("GPT image2 submit returned no response body")

                result_url = _extract_gpt_image2_result(body)
                if result_url:
                    return result_url, "gpt-image2-style-render", None

                task_id = extract_task_id(body)
                status = extract_status(body)
                logger.warning(
                    "Merchant style GPT image2 submit: task_id=%s status=%s keys=%s",
                    task_id,
                    status,
                    sorted(body.keys()),
                )

                if task_id:
                    if "/images/edits" in endpoint:
                        base_url = endpoint.replace("/images/edits", "")
                    else:
                        base_url = endpoint.rsplit("/", 2)[0]
                    task_urls = [
                        f"{base_url.rstrip('/')}/images/generations/{task_id}",
                        f"{base_url.rstrip('/')}/tasks/{task_id}",
                    ]
                    if settings.async_task_result_url:
                        task_urls.append(f"{settings.async_task_result_url}?task_id={task_id}")
                    task_urls = list(dict.fromkeys(task_urls))

                    pending_statuses = {"queued", "running", "processing", "pending", "submitted", "in_progress"}
                    failed_statuses = {"failed", "error", "cancelled", "canceled"}
                    max_attempts = max(30, int(settings.image2_timeout_seconds // 2))
                    last_body = body

                    for attempt in range(max_attempts):
                        await asyncio.sleep(2)
                        for task_url in task_urls:
                            try:
                                poll_resp = await client.get(task_url, headers=headers)
                            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
                                logger.warning(
                                    "Merchant style GPT image2 poll transport failed: task_id=%s attempt=%s url=%s error=%s",
                                    task_id,
                                    attempt + 1,
                                    task_url,
                                    exc,
                                )
                                continue
                            if poll_resp.status_code >= 400:
                                logger.warning(
                                    "Merchant style GPT image2 poll failed: task_id=%s url=%s status=%s",
                                    task_id,
                                    task_url,
                                    poll_resp.status_code,
                                )
                                continue
                            last_body = poll_resp.json()
                            status = extract_status(last_body)
                            result_url = _extract_gpt_image2_result(last_body)
                            logger.warning(
                                "Merchant style GPT image2 poll: task_id=%s attempt=%s status=%s keys=%s url=%s",
                                task_id,
                                attempt + 1,
                                status,
                                sorted(last_body.keys()),
                                task_url,
                            )
                            if result_url:
                                return result_url, "gpt-image2-style-render", None
                            if status in failed_statuses:
                                raise ValueError(f"GPT image2 task failed: {last_body.get('error') or last_body}")
                            if status and status not in pending_statuses:
                                break
                    raise TimeoutError(f"GPT image2 task timed out: {task_id}; last_body={json.dumps(last_body)[:500]}")

            return None, "gpt-image2-style-render", f"empty_result: {json.dumps(body)}"
        except Exception as exc:
            return None, "gpt-image2-style-render", f"{type(exc).__name__}: {str(exc)[:180]}"

    rendered_url, render_channel, render_error = await generate_design_render()
    design_image_url = source_image_url
    render_status = "failed"

    if rendered_url:
        try:
            design_image_url = await _persist_design_image_url(asset_id, rendered_url)
            render_status = "ai_generated"
        except Exception as exc:
            logger.warning("Failed to persist merchant preview design image for %s: %s", asset_id, exc)
            design_image_url = rendered_url
            render_status = "ai_generated"
            render_error = f"{render_error or ''} persist_failed:{type(exc).__name__}:{str(exc)[:120]}".strip()
    else:
        render_error = render_error or "gpt_image2_render_failed"

    return {
        "source_image_url": source_image_url,
        "design_image_url": design_image_url,
        "render_status": render_status,
        "render_channel": render_channel,
        "render_error": render_error,
    }


async def _create_style_preview_draft(
    *,
    name: str,
    price: str,
    image_bytes: bytes,
    filename: str | None,
    preferred_length_label: str | None = None,
) -> dict[str, Any]:
    draft_id = f"style-draft-{uuid4().hex[:12]}"
    visual_desc = ""
    try:
        desc = await analyze_nail_style_image(image_bytes)
        if desc:
            visual_desc = desc
    except Exception:
        logger.warning("analyze_nail_style_image failed, using empty visual description for style %s", name)

    extracted_taxonomy = extract_taxonomy_from_text(name, visual_desc)
    if preferred_length_label:
        extracted_taxonomy["lengths"] = [preferred_length_label]

    source_extension = filename.split(".")[-1] if filename and "." in filename else "png"
    inferred_length_label = _taxonomy_length_label(extracted_taxonomy, preferred_length_label or "短款")
    render_assets = await _generate_style_render_assets(
        asset_id=draft_id,
        source_filename_stem=draft_id,
        source_extension=source_extension,
        image_bytes=image_bytes,
        name=name,
        color=" / ".join(extracted_taxonomy["colors"][:2]),
        finish=extracted_taxonomy["techniques"][0],
        nail_length_label=inferred_length_label,
    )

    draft = {
        "draft_id": draft_id,
        "name": name,
        "price": price,
        "source_image_url": render_assets["source_image_url"],
        "design_image_url": render_assets["design_image_url"],
        "render_status": render_assets["render_status"],
        "render_channel": render_assets["render_channel"],
        "render_error": render_assets["render_error"],
        "extracted_taxonomy": extracted_taxonomy,
    }
    _upsert_custom_style_draft(draft)
    return draft


def _build_published_style_data(
    *,
    style_id: str,
    name: str,
    price: str,
    taxonomy: dict[str, list[str]],
    source_image_url: str,
    design_image_url: str,
    render_channel: str | None,
) -> dict[str, Any]:
    color = " / ".join(taxonomy.get("colors", [])[:2]) or "裸色系"
    finish = taxonomy.get("techniques", ["纯色"])[0]
    nail_length = _taxonomy_length_to_code(taxonomy)
    tags = _dedupe_tokens([
        "商家上新",
        "实拍",
        "图库导入",
        *taxonomy.get("colors", [])[:1],
        *taxonomy.get("techniques", [])[:1],
        *taxonomy.get("shapes", [])[:1],
        *taxonomy.get("styles", [])[:2],
        *taxonomy.get("occasions", [])[:1],
        *taxonomy.get("lengths", [])[:1],
    ])

    return {
        "id": style_id,
        "name": name,
        "color": color,
        "finish": finish,
        "occasion": taxonomy.get("occasions", []) or ["日常"],
        "tags": tags,
        "palette": [],
        "prompt": (
            f"{name} manicure. Taxonomy: {', '.join(tags)}. "
            f"Required nail shape: {', '.join(taxonomy.get('shapes', [])) or 'follow reference'}. "
            f"Required nail length: {', '.join(taxonomy.get('lengths', [])) or 'follow reference'}"
        ),
        "difficulty": "medium",
        "price": price,
        "price_level": _parse_price_level(price),
        "image_url": design_image_url,
        "source_image_url": source_image_url,
        "design_image_url": design_image_url,
        "render_channel": render_channel,
        "nail_length": nail_length,
        "taxonomy": taxonomy,
        "is_active": True,
    }


def _decode_data_url(data_url: str) -> bytes:
    return base64.b64decode(data_url.split(",", 1)[1])


async def _build_isolated_design_board(image_bytes: bytes) -> bytes | None:
    """
    Fallback design rendering: isolate only nails from merchant photo and lay them on a clean board.
    """
    seg = await segment_nails(image_bytes)
    if not seg.available or not seg.boxes or not seg.mask_image_url:
        return None

    source = Image.open(BytesIO(image_bytes)).convert("RGB")
    mask = Image.open(BytesIO(_decode_data_url(seg.mask_image_url))).convert("L")
    boxes = sorted(seg.boxes, key=lambda b: (b["x1"] + b["x2"]) / 2)

    patches: list[Image.Image] = []
    for box in boxes[:10]:
        x1, y1, x2, y2 = int(box["x1"]), int(box["y1"]), int(box["x2"]), int(box["y2"])
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        pad = max(4, int(max(w, h) * 0.2))

        nx1 = max(0, x1 - pad)
        ny1 = max(0, y1 - pad)
        nx2 = min(source.width, x2 + pad)
        ny2 = min(source.height, y2 + pad)
        crop_rgb = source.crop((nx1, ny1, nx2, ny2)).convert("RGBA")
        crop_mask = mask.crop((nx1, ny1, nx2, ny2))
        crop_rgb.putalpha(crop_mask)
        patches.append(crop_rgb)

    if not patches:
        return None

    board_w, board_h = 1024, 1024
    board = Image.new("RGB", (board_w, board_h), (245, 245, 245))
    cols, rows = 5, 2
    margin_x, margin_y = 64, 88
    gap_x, gap_y = 26, 42
    cell_w = (board_w - margin_x * 2 - gap_x * (cols - 1)) // cols
    cell_h = (board_h - margin_y * 2 - gap_y * (rows - 1)) // rows

    for idx, patch in enumerate(patches[: cols * rows]):
        r, c = divmod(idx, cols)
        patch.thumbnail((int(cell_w * 0.86), int(cell_h * 0.86)), Image.Resampling.LANCZOS)
        x = margin_x + c * (cell_w + gap_x) + (cell_w - patch.width) // 2
        y = margin_y + r * (cell_h + gap_y) + (cell_h - patch.height) // 2
        board.paste(patch, (x, y), patch)

    out = BytesIO()
    board.save(out, format="PNG")
    return out.getvalue()


@router.post("/store/styles/preview")
async def preview_merchant_style(
    name: str = Form(...),
    price: str = Form(...),
    image: UploadFile = File(...),
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is required")

    draft = await _create_style_preview_draft(
        name=name,
        price=price,
        image_bytes=image_bytes,
        filename=image.filename,
    )
    return {
        "status": "success",
        "draft_id": draft["draft_id"],
        "source_image_url": draft["source_image_url"],
        "design_image_url": draft["design_image_url"],
        "render_status": draft["render_status"],
        "render_channel": draft["render_channel"],
        "render_error": draft["render_error"],
        "extracted_taxonomy": draft["extracted_taxonomy"],
    }


@router.post("/store/styles/publish")
async def publish_merchant_style(payload: dict[str, Any]):
    draft_id = str(payload.get("draft_id", "")).strip()
    name = str(payload.get("name", "")).strip()
    price = str(payload.get("price", "")).strip()

    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id is required")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    draft = _get_custom_style_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Style preview draft not found")

    taxonomy = _merge_taxonomy(payload.get("taxonomy"), payload.get("custom_tags_by_dimension"))
    missing_dimensions = [key for key, values in taxonomy.items() if not values]
    if missing_dimensions:
        raise HTTPException(status_code=400, detail=f"taxonomy incomplete: {', '.join(missing_dimensions)}")

    style_id = f"custom-style-{uuid4().hex[:12]}"
    source_image_url = str(draft["source_image_url"])
    design_image_url = str(draft["design_image_url"])
    try:
        design_image_url = await _persist_design_image_url(style_id, design_image_url)
    except Exception as exc:
        logger.warning("Failed to persist published merchant design image for %s: %s", style_id, exc)
        design_image_url = source_image_url

    style_data = _build_published_style_data(
        style_id=style_id,
        name=name,
        price=price or str(draft.get("price", "")),
        taxonomy=taxonomy,
        source_image_url=source_image_url,
        design_image_url=design_image_url,
        render_channel=str(draft.get("render_channel") or ""),
    )

    success = await save_uploaded_style(style_data, "library-nail-spa-futian")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save style")

    _delete_custom_style_draft(draft_id)
    _clear_style_catalog_cache()

    return {
        "status": "success",
        "style_id": style_id,
        "style": style_data,
    }

@router.post("/store/styles/upload")
async def upload_merchant_style(
    name: str = Form(...),
    price: str = Form(...),
    nail_length: str = Form(...),
    image: UploadFile = File(...)
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is required")

    draft = await _create_style_preview_draft(
        name=name,
        price=price,
        image_bytes=image_bytes,
        filename=image.filename,
        preferred_length_label=nail_length,
    )
    taxonomy = draft["extracted_taxonomy"]
    style_id = f"custom-style-{uuid4().hex[:12]}"
    source_image_url = str(draft["source_image_url"])
    design_image_url = str(draft["design_image_url"])
    try:
        design_image_url = await _persist_design_image_url(style_id, design_image_url)
    except Exception as exc:
        logger.warning("Failed to persist direct-upload merchant design image for %s: %s", style_id, exc)
        design_image_url = source_image_url

    style_data = _build_published_style_data(
        style_id=style_id,
        name=name,
        price=price,
        taxonomy=taxonomy,
        source_image_url=source_image_url,
        design_image_url=design_image_url,
        render_channel=str(draft.get("render_channel") or ""),
    )

    success = await save_uploaded_style(style_data, "library-nail-spa-futian")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save style")

    _delete_custom_style_draft(str(draft["draft_id"]))
    _clear_style_catalog_cache()

    return {
        "status": "success",
        "style_id": style_id,
        "extracted_taxonomy": taxonomy,
        "style": style_data,
        "render_status": draft["render_status"],
        "render_channel": draft["render_channel"],
        "render_error": draft["render_error"],
    }


@router.get("/store/styles")
async def get_store_styles():
    from app.services.style_catalog import get_merchant_styles
    from app.services.supabase_db import get_style_analytics
    
    merchant_styles = get_merchant_styles()
    result = []
    for s in merchant_styles:
        analytics = await get_style_analytics(s.id)
        style_dict = s.model_dump()
        style_dict["analytics"] = analytics
        result.append(style_dict)
    
    # Sort active styles above inactive styles
    result.sort(key=lambda x: x.get("is_active", True), reverse=True)
    return {"status": "success", "styles": result}


@router.post("/store/styles/{style_id}/toggle-active")
async def toggle_style_active(style_id: str, payload: dict):
    from app.services.supabase_db import update_style_active_status
    
    is_active = payload.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="is_active field is required")
        
    success = await update_style_active_status(style_id, bool(is_active))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update style status")
        
    _clear_style_catalog_cache()
    return {
        "status": "success",
        "style_id": style_id,
        "is_active": is_active
    }


@router.post("/styles/{style_id}/telemetry")
async def report_style_telemetry(style_id: str, event_type: str):
    from app.services.supabase_db import increment_style_analytics
    
    if event_type not in ["view", "interest", "booking"]:
        raise HTTPException(status_code=400, detail="Invalid event_type")
        
    metric_map = {
        "view": "views",
        "interest": "interests",
        "booking": "bookings"
    }
    metric = metric_map[event_type]
    success = await increment_style_analytics(style_id, metric)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to record telemetry")
        
    return {
        "status": "success",
        "style_id": style_id,
        "event_type": event_type
    }
