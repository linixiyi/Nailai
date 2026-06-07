from __future__ import annotations

import json
import time
from typing import Any
from pathlib import Path

import httpx

from app.config import settings
from app.schemas import NailStyle
from app.services.nail_taxonomy import enrich_style_dict, taxonomy_tokens_for_style_dict


OCCASIONS = {
    "wedding": "婚礼",
    "work": "通勤",
    "date": "约会",
    "party": "派对",
    "travel": "旅行",
    "new-year": "新年",
}

_STYLE_CACHE: tuple[float, list[NailStyle]] | None = None
_CANONICAL_STYLE_OVERRIDES: dict[str, dict[str, Any]] = {}


def _load_canonical_style_overrides() -> dict[str, dict[str, Any]]:
    data_path = Path(__file__).with_name("nail_taxonomy_data.json")
    if not data_path.exists():
        return {}
    try:
        raw = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    overrides: dict[str, dict[str, Any]] = {}
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            overrides[item["id"]] = item
    return overrides


_CANONICAL_STYLE_OVERRIDES = _load_canonical_style_overrides()


def _normalize_array(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        return [value] if value else []
    return []


def _normalize_style_row(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["occasion"] = _normalize_array(data.get("occasion"))
    data["tags"] = _normalize_array(data.get("tags"))
    data["palette"] = _normalize_array(data.get("palette"))
    data["prompt"] = data.get("prompt") or f"{data.get('name', 'nail style')} manicure, realistic salon quality"
    data["difficulty"] = data.get("difficulty") or "medium"
    data["price_level"] = data.get("price_level") or "¥¥"
    data["nail_length"] = data.get("nail_length") or "natural"
    normalized = enrich_style_dict(data)
    normalized["is_active"] = row.get("is_active", normalized.get("is_active", True))
    canonical = _CANONICAL_STYLE_OVERRIDES.get(str(normalized.get("id", "")))
    if canonical:
        merged = dict(normalized)
        merged.update(
            {
                "name": canonical.get("name", merged.get("name")),
                "color": canonical.get("color", merged.get("color")),
                "finish": canonical.get("finish", merged.get("finish")),
                "occasion": canonical.get("occasion", merged.get("occasion", [])),
                "tags": canonical.get("tags", merged.get("tags", [])),
                "palette": canonical.get("palette", merged.get("palette", [])),
                "prompt": canonical.get("prompt", merged.get("prompt")),
                "difficulty": canonical.get("difficulty", merged.get("difficulty")),
                "price_level": canonical.get("price_level", merged.get("price_level")),
                "image_url": canonical.get("image_url", merged.get("image_url")),
                "nail_length": canonical.get("nail_length", merged.get("nail_length")),
                "taxonomy": canonical.get("taxonomy", merged.get("taxonomy", {})),
                "stock_total": canonical.get("stock_total", merged.get("stock_total")),
                "stock_reserved": canonical.get("stock_reserved", merged.get("stock_reserved")),
                "is_active": canonical.get("is_active", merged.get("is_active", True)),
            }
        )
        return merged
    return normalized


def _fetch_styles_from_supabase() -> list[NailStyle]:
    supabase_url = settings.supabase_url or settings.next_public_supabase_url
    if not supabase_url:
        return []
    api_key = (
        settings.supabase_service_role_key
        or settings.supabase_anon_key
        or settings.next_public_supabase_anon_key
    )
    if not api_key:
        return []

    base_url = supabase_url.rstrip("/")
    params = {
        "select": "*",
        "order": "created_at.desc",
    }
    response = httpx.get(
        f"{base_url}/rest/v1/nail_styles",
        params=params,
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
        },
        timeout=8.0,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        return []
    styles = [NailStyle(**_normalize_style_row(row)) for row in rows if isinstance(row, dict)]
    # 过滤掉指定问题款式
    styles = [s for s in styles if not _is_blocked_style(s)]
    # Prefer styles that have concrete images and available stock for visible catalog slots.
    return sorted(
        styles,
        key=lambda style: (
            not bool(style.image_url),
            -max((style.stock_total or 0) - (style.stock_reserved or 0), 0),
            style.name,
        ),
    )


RAW_STYLES: list[dict] = [
    {"id": "milk-tea-glaze", "name": "奶茶琉璃", "color": "奶茶", "finish": "透亮", "occasion": ["通勤", "约会"], "tags": ["显白", "温柔", "短甲友好"], "palette": ["#d7b89b", "#f3e3d2", "#b98064"], "difficulty": "easy", "price_level": "¥¥"},
    {"id": "rose-cat-eye", "name": "玫瑰猫眼", "color": "玫瑰", "finish": "猫眼", "occasion": ["约会", "派对"], "tags": ["氛围感", "闪", "中长甲"], "palette": ["#9f4155", "#e7a3b1", "#602735"], "difficulty": "medium", "price_level": "¥¥¥"},
    {"id": "french-pearl", "name": "珍珠法式", "color": "白色", "finish": "珍珠", "occasion": ["婚礼", "通勤"], "tags": ["优雅", "低调", "法式"], "palette": ["#fffaf0", "#d8c7ad", "#f6e8d8"], "difficulty": "medium", "price_level": "¥¥¥"},
    {"id": "black-ribbon", "name": "黑丝带芭蕾", "color": "黑色", "finish": "手绘", "occasion": ["派对", "约会"], "tags": ["酷甜", "蝴蝶结", "法式边"], "palette": ["#151414", "#f1d6dc", "#ffffff"], "difficulty": "hard", "price_level": "¥¥¥"},
    {"id": "matcha-jelly", "name": "抹茶果冻", "color": "绿色", "finish": "果冻", "occasion": ["旅行", "通勤"], "tags": ["清新", "短甲", "夏天"], "palette": ["#9eb77e", "#dce8c8", "#61754a"], "difficulty": "easy", "price_level": "¥¥"},
    {"id": "blue-hour-aura", "name": "蓝调腮红", "color": "蓝色", "finish": "渐变", "occasion": ["旅行", "派对"], "tags": ["冷感", "腮红甲", "显白"], "palette": ["#597ea8", "#d8e6f3", "#f3dfe8"], "difficulty": "medium", "price_level": "¥¥"},
    {"id": "cherry-mirror", "name": "樱桃镜面", "color": "红色", "finish": "镜面", "occasion": ["新年", "约会"], "tags": ["复古", "气色", "亮面"], "palette": ["#b8152f", "#ffced8", "#7a0f20"], "difficulty": "medium", "price_level": "¥¥¥"},
    {"id": "silver-y2k", "name": "银色 Y2K", "color": "银色", "finish": "金属", "occasion": ["派对"], "tags": ["未来感", "金属", "个性"], "palette": ["#c8ccd1", "#f7f7f7", "#656a72"], "difficulty": "hard", "price_level": "¥¥¥"},
    {"id": "lavender-cloud", "name": "薰衣草云朵", "color": "紫色", "finish": "晕染", "occasion": ["旅行", "约会"], "tags": ["梦幻", "柔和", "晕染"], "palette": ["#b7a5d8", "#f4efff", "#7b6ca8"], "difficulty": "medium", "price_level": "¥¥"},
    {"id": "latte-line", "name": "拿铁线条", "color": "咖色", "finish": "线条", "occasion": ["通勤"], "tags": ["极简", "高级", "细节"], "palette": ["#8f6951", "#f4e5d7", "#39281f"], "difficulty": "easy", "price_level": "¥¥"},
]


FIXED_TARGET_STYLE = {
    "id": "fixed-target-red-black-spider",
    "name": "指定款：红黑棋盘蜘蛛",
    "color": "红黑",
    "finish": "亮面",
    "occasion": ["派对", "万圣节", "个性写真"],
    "tags": ["指定款", "红黑棋盘", "蜘蛛", "高对比"],
    "palette": ["#cf1f2e", "#0f0f11", "#6d4f45"],
    "prompt": "red and black checkerboard manicure, glossy black nails, translucent smoky brown nails with tiny black spider and dot details, high contrast, salon quality, keep hand pose unchanged",
    "difficulty": "hard",
    "price_level": "¥¥¥",
    "image_url": "/style-images/custom/fixed-target-style.png",
    "stock_total": 99,
    "stock_reserved": 0,
}


_LIBRARY_STYLE_NAMES = [
    "樱花琉璃", "蜜桃果冻", "星空猫眼", "落日渐变", "法式奶油",
    "玫瑰金箔", "薄荷冰透", "琥珀晕染", "腮红渐变", "冰透裸粉",
    "极光猫眼", "蜜桃乌龙", "蝴蝶贝壳", "焦糖玛奇朵", "雪花晶石",
    "海棠花语", "柠檬气泡", "紫藤流苏", "珊瑚日出", "珍珠奶茶",
    "森林苔藓", "荔枝冰沙", "薰衣草田", "蜜桃甜心", "海盐太妃",
    "杜鹃花语", "芒果奶冻", "月光石", "红茶拿铁", "草莓奶昔",
    "紫薯芋泥", "海盐焦糖",
]


def _library_style(index: int) -> dict:
    finishes = ["镜面", "果冻", "猫眼", "渐变", "法式"]
    finish = finishes[(index - 1) % len(finishes)]
    color = "红粉"
    name = _LIBRARY_STYLE_NAMES[index - 1] if index <= len(_LIBRARY_STYLE_NAMES) else f"图鉴款 {index:03d}"
    tags = ["长甲", "实拍", "图库导入", finish]
    palette = ["#d94b62", "#f5d7dc", "#b81f42"]
    prompt = f"{name} nail art, {finish}, realistic salon quality"
    
    if index == 6:
        color = "粉黑"
        finish = "手绘"
        tags = ["长甲", "实拍", "图库导入", "棋盘格", "手绘"]
        palette = ["#ffc0cb", "#000000", "#ffffff"]
        prompt = "pink and black checkerboard patterns, handpainted, realistic salon quality"
        
    return enrich_style_dict({
        "id": f"library-20260514-{index:03d}",
        "name": name,
        "color": color,
        "finish": finish,
        "occasion": ["约会", "通勤"],
        "tags": tags,
        "palette": palette,
        "prompt": prompt,
        "difficulty": "medium",
        "price_level": "¥¥¥",
        "image_url": f"/style-images/library-20260514/library-20260514-{index:03d}.png",
        "stock_total": 15,
        "stock_reserved": (index - 1) % 5,
    })


def _variant(base: dict, index: int) -> dict:
    seasons = ["春日", "夏日", "秋冬", "节日", "日常"]
    accents = ["细闪", "法式边", "贝壳片", "水晶点缀", "微晕染"]
    variant = dict(base)
    variant["id"] = f"{base['id']}-{index + 1}"
    variant["name"] = f"{base['name']} {accents[index % len(accents)]}"
    variant["tags"] = [*base["tags"], accents[index % len(accents)], seasons[index % len(seasons)]]
    variant["prompt"] = (
        f"{variant['name']} manicure, {base['color']} tone, {base['finish']} finish, "
        "natural nail bed, glossy salon quality, realistic hand photo inpainting"
    )
    test_group_image_map = {
        "cherry-mirror-1": "/style-images/group-20260514-212714/1.png",
        "cherry-mirror-2": "/style-images/group-20260514-212714/2.png",
        "cherry-mirror-3": "/style-images/group-20260514-212714/3.png",
        "cherry-mirror-4": "/style-images/group-20260514-212714/4.png",
        "cherry-mirror-5": "/style-images/group-20260514-212714/5.png",
    }
    if image_url := test_group_image_map.get(variant["id"]):
        variant["image_url"] = image_url
        variant["stock_total"] = 12
        variant["stock_reserved"] = min(index + 1, 4)
    return variant


def _fallback_styles() -> list[NailStyle]:
    styles: list[NailStyle] = [NailStyle(**FIXED_TARGET_STYLE)]
    styles.extend(NailStyle(**_library_style(index)) for index in range(1, 33))
    for base in RAW_STYLES:
        for index in range(5):
            styles.append(NailStyle(**_variant(base, index)))
            
    for style in styles:
        if style.taxonomy.get("lengths"):
            continue
        text_content = style.name + " " + " ".join(style.tags)
        if any(w in text_content for w in ["延长", "长甲", "芭蕾", "梯形", "尖甲", "长梯形"]):
            style.nail_length = "long"
        elif any(w in text_content for w in ["短甲", "本甲"]):
            style.nail_length = "natural"
        elif "中长" in text_content:
            style.nail_length = "medium"
            
    return styles


_BLOCKED_STYLE_IDS = {
    "cross-yellow-black-sexy",
    "regression-test-style",
    "library-20260514-006",
    "library-20260514-032",
}
_BLOCKED_STYLE_KEYWORDS = ("十字架黄黑", "回归测试", "夏日清凉奶黄包", "测试转换", "隔离测试", "图库测试")


def _has_visible_stock(s: NailStyle) -> bool:
    if s.stock_total is None and s.stock_reserved is None:
        return True
    return max((s.stock_total or 0) - (s.stock_reserved or 0), 0) > 0


def _is_blocked_style(s: NailStyle) -> bool:
    if not getattr(s, "is_active", True):
        return True
    if s.id in _BLOCKED_STYLE_IDS:
        return True
    # 商家上传款式（custom-style-xxx）始终放行
    if s.id.startswith("custom-style-"):
        return False
    if not s.id.startswith("library-20260514-"):
        return True
    if s.id.startswith("seed-"):
        return True
    if "deprecated" in s.tags or "隐藏" in s.occasion:
        return True
    if not _has_visible_stock(s):
        return True
    name = s.name or ""
    return any(kw in name for kw in _BLOCKED_STYLE_KEYWORDS)


def _load_custom_uploaded_styles() -> list[NailStyle]:
    """从本地 custom-styles-db.json 读取商家上传款式，不受 Supabase 状态影响。"""
    from app.services.supabase_db import GENERATED_DIR
    path = GENERATED_DIR / "custom-styles-db.json"
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            return []
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                result.append(NailStyle(**_normalize_style_row(row)))
            except Exception:
                pass
        return result
    except Exception:
        return []


def list_styles() -> list[NailStyle]:
    global _STYLE_CACHE
    now = time.monotonic()
    if _STYLE_CACHE and now - _STYLE_CACHE[0] < settings.style_catalog_cache_seconds:
        return _STYLE_CACHE[1]

    try:
        styles = _fetch_styles_from_supabase()
    except Exception:
        styles = []

    # Supabase is the source of truth once it has the six-dimensional catalog.
    if not styles:
        styles = _fallback_styles()

    # 合并本地商家上传款式（custom-styles-db.json），排在最前面
    custom_styles = _load_custom_uploaded_styles()
    if custom_styles:
        existing_ids = {s.id for s in styles}
        local_by_id = {style.id: style for style in custom_styles}
        styles = [local_by_id.get(style.id, style) for style in styles]
        for cs in custom_styles:
            if cs.id not in existing_ids:
                styles = [cs] + styles
                existing_ids.add(cs.id)

    # 过滤掉指定问题款式
    styles = [s for s in styles if not _is_blocked_style(s)]

    _STYLE_CACHE = (now, styles)
    return styles


def get_merchant_styles() -> list[NailStyle]:
    """获取商家上传的所有款式（包含已下架款式），用于管理后台。"""
    styles = []
    
    # 1. 从 Supabase 读取
    supabase_url = settings.supabase_url or settings.next_public_supabase_url
    if supabase_url:
        try:
            api_key = (
                settings.supabase_service_role_key
                or settings.supabase_anon_key
                or settings.next_public_supabase_anon_key
            )
            if api_key:
                base_url = supabase_url.rstrip("/")
                response = httpx.get(
                    f"{base_url}/rest/v1/nail_styles",
                    params={"select": "*", "order": "created_at.desc"},
                    headers={
                        "apikey": api_key,
                        "Authorization": f"Bearer {api_key}",
                    },
                    timeout=8.0,
                )
                if response.status_code == 200:
                    rows = response.json()
                    if isinstance(rows, list):
                        for row in rows:
                            if isinstance(row, dict) and str(row.get("id", "")).startswith("custom-style-"):
                                try:
                                    styles.append(NailStyle(**_normalize_style_row(row)))
                                except Exception:
                                    pass
        except Exception:
            pass

    # 2. 从本地 JSON 读取
    custom_styles = _load_custom_uploaded_styles()
    if custom_styles:
        existing_ids = {s.id for s in styles}
        local_by_id = {style.id: style for style in custom_styles}
        styles = [local_by_id.get(style.id, style) for style in styles]
        for cs in custom_styles:
            if cs.id not in existing_ids:
                styles.append(cs)
                existing_ids.add(cs.id)

    return styles


def get_style(style_id: str | None) -> NailStyle:
    styles = list_styles()
    if not style_id:
        return styles[0]
    return next((style for style in styles if style.id == style_id), styles[0])


def build_style_from_payload(style_payload: str | None) -> NailStyle | None:
    if not style_payload:
        return None
    try:
        return NailStyle.model_validate_json(style_payload)
    except Exception:
        return None


def search_styles(query: str, limit: int = 5) -> list[NailStyle]:
    normalized = query.lower()
    scored: list[tuple[int, NailStyle]] = []
    
    # Detect intended length using semantic rules
    intended_length = None
    if ("长" in normalized or "延长" in normalized) and ("短" in normalized or "本甲" in normalized):
        if any(pat in normalized for pat in ["换成短", "改成短", "做短", "要短", "选短", "做短甲", "换短", "改短", "怕断"]):
            intended_length = "natural"
        elif any(pat in normalized for pat in ["换成长", "改成长", "做长", "要长", "选长", "做长甲", "换长", "改长"]):
            intended_length = "long"
            
    if not intended_length:
        if any(kw in normalized for kw in ["短甲", "短款", "本甲", "短指甲", "短的", "短甲友好"]):
            intended_length = "natural"
        elif any(kw in normalized for kw in ["中长", "中长款", "中长甲", "中等"]):
            intended_length = "medium"
        elif any(kw in normalized for kw in ["长甲", "长款", "延长", "超长", "长指甲", "长的"]):
            intended_length = "long"

    for style in list_styles():
        # Exclude styles with conflicting length targets
        if intended_length:
            style_length = style.nail_length
            style_tags_text = " ".join(style.tags or []).lower() + " " + style.name.lower()
            if intended_length == "natural":
                if style_length == "long" or any(kw in style_tags_text for kw in ["长甲", "长款", "延长", "超长", "长指甲"]):
                    continue
            elif intended_length == "long":
                if style_length == "natural" or any(kw in style_tags_text for kw in ["短甲", "短款", "本甲", "短指甲"]):
                    continue

        taxonomy_tokens = taxonomy_tokens_for_style_dict(style.model_dump())
        haystack = " ".join([style.name, style.color, style.finish, *style.occasion, *style.tags, *taxonomy_tokens]).lower()
        
        # Word splitting match
        score = sum(1 for token in normalized.replace("，", " ").replace(",", " ").split() if token and token in haystack)
        
        # Known taxonomy/tag keyword substring match (essential for continuous Chinese search)
        for keyword in [style.color, style.finish, *style.occasion, *style.tags, *taxonomy_tokens]:
            if keyword and keyword.lower() in normalized:
                # Do not count "长甲" as a positive score if the user intended "短甲"
                if keyword.lower() in ["长甲", "长款", "延长", "超长", "长指甲"] and intended_length == "natural":
                    continue
                # Do not count "短甲" as a positive score if the user intended "长甲"
                if keyword.lower() in ["短甲", "短款", "本甲", "短指甲"] and intended_length == "long":
                    continue
                score += 3
                
        if score:
            scored.append((score, style))
            
    if not scored:
        # If no styles matched with the filter, fall back to filtered styles by length
        filtered_by_length = []
        for style in list_styles():
            if intended_length:
                style_length = style.nail_length
                style_tags_text = " ".join(style.tags or []).lower() + " " + style.name.lower()
                if intended_length == "natural":
                    if style_length == "long" or any(kw in style_tags_text for kw in ["长甲", "长款", "延长", "超长", "长指甲"]):
                        continue
                elif intended_length == "long":
                    if style_length == "natural" or any(kw in style_tags_text for kw in ["短甲", "短款", "本甲", "短指甲"]):
                        continue
            filtered_by_length.append(style)
        return filtered_by_length[:limit]
        
    return [style for _, style in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


_TAXONOMY_FILTER_CACHE: tuple[float, dict] | None = None


def get_taxonomy_filters() -> dict[str, list[str]]:
    """Collect all unique taxonomy values across all styles, grouped by dimension."""
    global _TAXONOMY_FILTER_CACHE
    now = time.monotonic()
    if _TAXONOMY_FILTER_CACHE and now - _TAXONOMY_FILTER_CACHE[0] < settings.style_catalog_cache_seconds:
        return _TAXONOMY_FILTER_CACHE[1]

    dimensions = ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]
    collected: dict[str, set[str]] = {d: set() for d in dimensions}

    for style in list_styles():
        style_dict = style.model_dump()
        # Use taxonomy from style object or from nail_taxonomy.py
        taxonomy = style_dict.get("taxonomy") or {}
        if not taxonomy or not any(taxonomy.get(d) for d in dimensions):
            # Fallback: get from nail_taxonomy.py
            from app.services.nail_taxonomy import STYLE_TAXONOMY_BY_ID, _style_lookup_id
            lookup_id = _style_lookup_id(style.id)
            profile = STYLE_TAXONOMY_BY_ID.get(lookup_id)
            if profile:
                taxonomy = profile.get("taxonomy", {})

        for dim in dimensions:
            values = taxonomy.get(dim, [])
            if isinstance(values, list):
                for v in values:
                    if v and isinstance(v, str):
                        collected[dim].add(v)

    result = {dim: sorted(vals) for dim, vals in collected.items() if vals}
    _TAXONOMY_FILTER_CACHE = (now, result)
    return result
