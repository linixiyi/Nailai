import asyncio
import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urljoin
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.config import settings
from app.schemas import NailStyle
from app.services.style_vision_analyzer import analyze_nail_style_image

logger = logging.getLogger(__name__)


def _debug_dump_tryon_request(
    *,
    channel: str,
    endpoint: str,
    model: str | None,
    hand_bytes: bytes,
    style_bytes: bytes,
    prompt: str,
    mask_data_url: str | None = None,
    pixel_control: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
    payload_summary: dict[str, Any] | None = None,
) -> str | None:
    try:
        audit_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}"
        debug_dir = Path("generated/tryon-audit") / audit_id
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "hand_input.jpg").write_bytes(hand_bytes)
        (debug_dir / "style_input.jpg").write_bytes(style_bytes)
        (debug_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        if mask_data_url:
            (debug_dir / "mask_input.png").write_bytes(_decode_data_url(mask_data_url))
        elif (debug_dir / "mask_input.png").exists():
            (debug_dir / "mask_input.png").unlink()
        summary = {
            "id": audit_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "submitted",
            "channel": channel,
            "endpoint": endpoint,
            "model": model,
            "assets": {
                "hand_image_url": f"/generated/tryon-audit/{audit_id}/hand_input.jpg",
                "style_image_url": f"/generated/tryon-audit/{audit_id}/style_input.jpg",
                "mask_image_url": f"/generated/tryon-audit/{audit_id}/mask_input.png" if mask_data_url else None,
                "prompt_url": f"/generated/tryon-audit/{audit_id}/prompt.txt",
            },
            "sent_to_model": {
                "hand_image": True,
                "style_image": True,
                "mask_image": bool(mask_data_url),
                "pixel_prompt": bool(pixel_control),
            },
            "pixel_control": pixel_control or {},
            "hand_analysis": hand_analysis or {},
            "timings_ms": (pixel_control or {}).get("timings_ms", {}),
            "payload_summary": payload_summary or {},
        }
        (debug_dir / "request_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return audit_id
    except Exception as exc:
        logger.warning("Failed to dump try-on request debug artifacts: %s", exc)
        return None


def _finalize_debug_tryon_request(
    audit_id: str | None,
    *,
    status: str,
    result_image_url: str | None = None,
    error: str | None = None,
    timings_ms: dict[str, float] | None = None,
) -> None:
    if not audit_id:
        return
    try:
        summary_path = Path("generated/tryon-audit") / audit_id / "request_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["status"] = status
        summary["completed_at"] = datetime.now(timezone.utc).isoformat()
        summary["result_image_url"] = result_image_url
        summary["error"] = error
        if timings_ms:
            summary["timings_ms"] = {
                **summary.get("timings_ms", {}),
                **timings_ms,
            }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to finalize try-on audit record: %s", exc)


def _mock_try_on_image(image_bytes: bytes, style: NailStyle) -> str:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((1024, 1024))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    colors = style.palette
    for index in range(5):
        x = width * (0.28 + index * 0.11)
        y = height * 0.42
        color = colors[index % len(colors)]
        draw.rounded_rectangle(
            (x - width * 0.025, y - height * 0.05, x + width * 0.025, y + height * 0.055),
            radius=max(8, int(width * 0.02)),
            fill=color,
            outline="#ffffff",
            width=max(1, int(width * 0.004)),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.4))
    result = Image.alpha_composite(image.convert("RGBA"), overlay)
    buffer = BytesIO()
    result.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _crop_style_card_if_present(style_image_bytes: bytes) -> bytes:
    try:
        img = Image.open(BytesIO(style_image_bytes))
        img = ImageOps.exif_transpose(img).convert("RGB")
        width, height = img.size
        # Remove light metadata/card areas when the exported asset includes extra UI chrome.
        bottom_start = int(height * 0.9)
        sample_pixels = []
        for y in range(bottom_start, height, 5):
            for x in range(0, width, 20):
                r, g, b = img.getpixel((x, y))
                sample_pixels.append((r, g, b))
        avg_color = sum(sum(p) for p in sample_pixels) / (len(sample_pixels) * 3)
        if avg_color > 235:
            img = img.crop((0, 0, width, int(height * 0.75)))
            width, height = img.size

        # Tight-crop the actual nail artwork so image2 sees the style, not blank white space.
        pixels = img.load()
        xs: list[int] = []
        ys: list[int] = []
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                brightness = (r + g + b) / 3
                saturation = max(r, g, b) - min(r, g, b)
                if brightness < 246 or saturation > 14:
                    xs.append(x)
                    ys.append(y)
        if xs and ys:
            pad = max(16, int(min(width, height) * 0.04))
            left = max(0, min(xs) - pad)
            top = max(0, min(ys) - pad)
            right = min(width, max(xs) + pad)
            bottom = min(height, max(ys) + pad)
            if right - left > width * 0.12 and bottom - top > height * 0.12:
                img = img.crop((left, top, right, bottom))

        # Current inventory exports place fingertips at the bottom. Crop first,
        # then rotate so downstream models always receive fingertips at the top.
        img = img.rotate(180, expand=True)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=96)
        return buf.getvalue()
    except Exception:
        logger.debug("Failed to normalize style image, using original bytes")
    return style_image_bytes


def _ensure_data_url(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _normalize_image_bytes(image_bytes: bytes, max_side: int = 1024, quality: int = 86) -> bytes:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _decode_data_url(data_url: str) -> bytes:
    if "," not in data_url:
        return base64.b64decode(data_url)
    return base64.b64decode(data_url.split(",", 1)[1])


def _build_mask_control_image_data_url(image_bytes: bytes, mask_image_url: str) -> str:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGBA")
    mask = Image.open(BytesIO(_decode_data_url(mask_image_url))).convert("L")
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.NEAREST)

    red_overlay = Image.new("RGBA", image.size, (255, 0, 70, 0))
    red_overlay.putalpha(mask.point(lambda value: 120 if value > 0 else 0))
    control_image = Image.alpha_composite(image, red_overlay)

    buffer = BytesIO()
    control_image.convert("RGB").save(buffer, format="JPEG", quality=92)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _build_transparent_edit_mask_data_url(
    image_bytes: bytes,
    mask_image_url: str,
    nail_length: str = "natural",
    style_expansion_scale: float = 1.0,
) -> str:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGBA")
    mask = Image.open(BytesIO(_decode_data_url(mask_image_url))).convert("L")
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.NEAREST)

    max_side = max(image.size)
    if nail_length == "long":
        expand_radius = max(36, int(max_side * 0.07))
    elif nail_length == "medium":
        expand_radius = max(22, int(max_side * 0.045))
    else:
        expand_radius = max(8, int(max_side * 0.018))
    expand_radius = max(3, int(expand_radius * style_expansion_scale))
    mask = mask.filter(ImageFilter.MaxFilter(expand_radius * 2 + 1))

    # GPT image edit masks use fully transparent pixels as the editable area.
    alpha = mask.point(lambda value: 0 if value > 0 else 255)
    edit_mask = Image.new("RGBA", image.size, (0, 0, 0, 255))
    edit_mask.putalpha(alpha)

    buffer = BytesIO()
    edit_mask.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _fit_image_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    src_w, src_h = image.size
    dst_w, dst_h = size
    scale = max(dst_w / src_w, dst_h / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - dst_w) // 2)
    top = max(0, (resized.height - dst_h) // 2)
    return resized.crop((left, top, left + dst_w, top + dst_h))


def _style_reference_colors(style_image_bytes: bytes, fallback: list[str]) -> list[tuple[int, int, int]]:
    try:
        image = Image.open(BytesIO(_crop_style_card_if_present(style_image_bytes)))
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((360, 360))
        pixels: list[tuple[int, int, int]] = []
        for r, g, b in image.getdata():
            brightness = (r + g + b) / 3
            saturation = max(r, g, b) - min(r, g, b)
            if brightness > 248 and saturation < 12:
                continue
            if brightness < 18:
                continue
            pixels.append((r, g, b))
        if len(pixels) < 80:
            raise ValueError("not enough style pixels")

        palette_source = Image.new("RGB", (len(pixels), 1))
        palette_source.putdata(pixels)
        quantized = palette_source.quantize(colors=6, method=Image.Quantize.MEDIANCUT).convert("RGB")
        colors = list(dict.fromkeys(quantized.getdata()))
        colors.sort(key=lambda color: (max(color) - min(color), sum(color)), reverse=True)
        return colors[:5]
    except Exception:
        colors: list[tuple[int, int, int]] = []
        for value in fallback:
            value = value.strip().lstrip("#")
            if len(value) == 6:
                try:
                    colors.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
                except ValueError:
                    pass
        return colors or [(214, 75, 98), (245, 215, 220), (184, 31, 66)]


def _build_local_style_draft_data_url(
    image_bytes: bytes,
    mask_image_url: str,
    style_image_bytes: bytes | None,
    style: NailStyle,
) -> str:
    hand = Image.open(BytesIO(image_bytes))
    hand = ImageOps.exif_transpose(hand).convert("RGBA")
    mask = Image.open(BytesIO(_decode_data_url(mask_image_url))).convert("L")
    if mask.size != hand.size:
        mask = mask.resize(hand.size, Image.Resampling.NEAREST)

    colors = _style_reference_colors(style_image_bytes, style.palette) if style_image_bytes else _style_reference_colors(b"", style.palette)
    width, height = hand.size
    soft_mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, min(width, height) // 320)))
    overlay = Image.new("RGBA", hand.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bbox = mask.getbbox()
    top = bbox[1] if bbox else 0
    bottom = bbox[3] if bbox else height
    span = max(1, bottom - top)

    for y in range(top, bottom):
        t = min(1.0, max(0.0, (y - top) / span))
        color_a = colors[int(t * (len(colors) - 1)) % len(colors)]
        color_b = colors[min(len(colors) - 1, int(t * (len(colors) - 1)) + 1)]
        mix = (t * (len(colors) - 1)) % 1
        color = tuple(int(color_a[i] * (1 - mix) + color_b[i] * mix) for i in range(3))
        draw.line([(0, y), (width, y)], fill=(*color, 0))

    color_layer = Image.new("RGBA", hand.size, (0, 0, 0, 0))
    color_pixels = color_layer.load()
    mask_pixels = soft_mask.load()
    for y in range(height):
        t = min(1.0, max(0.0, (y - top) / span))
        color_a = colors[int(t * (len(colors) - 1)) % len(colors)]
        color_b = colors[min(len(colors) - 1, int(t * (len(colors) - 1)) + 1)]
        mix = (t * (len(colors) - 1)) % 1
        color = tuple(int(color_a[i] * (1 - mix) + color_b[i] * mix) for i in range(3))
        for x in range(width):
            alpha = mask_pixels[x, y]
            if alpha:
                color_pixels[x, y] = (*color, int(alpha * 0.78))

    glossy = Image.new("RGBA", hand.size, (255, 255, 255, 0))
    gloss_alpha = mask.filter(ImageFilter.GaussianBlur(radius=max(2, min(width, height) // 180))).point(
        lambda value: int(value * 0.18)
    )
    glossy.putalpha(gloss_alpha)

    draft = Image.alpha_composite(hand, color_layer)
    if "镜面" in style.finish or "金属" in style.finish or any(tag in style.tags for tag in ["水钻", "亮片", "金属", "镜面"]):
        draft = Image.alpha_composite(draft, glossy)

    buffer = BytesIO()
    draft.convert("RGB").save(buffer, format="JPEG", quality=92)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"



def _extract_dashscope_image_url(body: dict[str, Any]) -> str | None:
    choices = body.get("output", {}).get("choices", [])
    if not isinstance(choices, list):
        return None
    for choice in choices:
        content = choice.get("message", {}).get("content", []) if isinstance(choice, dict) else []
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("image"):
                return item["image"]
    return None


def _provider_error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, httpx.HTTPStatusError):
        return {
            "error_type": type(exc).__name__,
            "status_code": exc.response.status_code,
            "response": exc.response.text[:800],
        }
    return {"error_type": type(exc).__name__, "message": str(exc)[:300]}


def _build_nail_tryon_prompt(
    style: NailStyle | None = None,
    pixel_control: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
) -> str:
    configured_nail_length = getattr(style, "nail_length", "natural") if style else "natural"
    detected_style_level = str((pixel_control or {}).get("style_level", "")).upper()
    nail_length = {
        "LONG": "long",
        "MEDIUM": "medium",
        "SHORT": "natural",
    }.get(detected_style_level, configured_nail_length)
    if nail_length == "long":
        length_rule = (
            "本次动态检测判定第二张参考图为长甲/延长甲。最终结果必须呈现自然长甲。\n"
            "【甲长调整特殊指令（必须执行）】若第一张手图中的指甲本来是短指甲/中长指甲，生成时必须沿指尖远端方向自然延伸、延长指甲，呈现修长完美的比例；绝对不可将长款美甲强行压缩并平铺贴在原有的短指甲范围之内。\n"
            "仅允许沿每根指甲的远端自由边向外延伸，甲根宽度、甲沟位置、手指宽度和手指形态绝对不能改变。\n"
            "延长比例必须遵守逐指几何控制中的 extension_scale 上限，不得拉成过细、过宽或不对称的甲片。\n"
            "延长部分要与原甲床自然衔接，保持参考图的长宽比、甲型、厚度、边缘和阴影。"
        )
    elif nail_length == "medium":
        length_rule = (
            "本次动态检测判定第二张参考图为中长甲。最终结果必须呈现克制的中长甲比例。\n"
            "【甲长调整特殊指令（必须执行）】若第一张手图中的指甲本来是短指甲，生成时必须沿指尖远端方向适度延长指甲，呈现完美比例；绝对不可将款式强行压缩贴在原有的短指甲上。\n"
            "仅允许沿每根指甲的远端自由边做有限延长；禁止改变甲根宽度、甲沟位置、手指宽度或手指形态。"
            "延长比例必须遵守逐指几何控制中的 extension_scale 上限，甲型与长宽比贴近参考图。"
        )
    else:
        length_rule = (
            "第二张参考图是短甲/本甲时，最终结果必须保持短甲，不要随意延长。\n"
            "【甲长调整特殊指令（核心重点）】若第一张手图中的指甲是长美甲/中长甲，最终生成时必须将指甲“修短”为贴合自然本甲床的短甲；必须在生成中将超出短甲范围的指甲多余部分彻底抹除，并替换为与手指自然融合的指尖皮肤和背景，严禁将短甲贴图或图案直接平铺贴在原来的长指甲形状上而导致形状穿帮。\n"
            "短甲必须有自己的真实短甲几何，而不是把长甲设计缩小后强行贴到原轮廓上；只在原本甲床范围附近迁移颜色、图案、质感和光泽。\n"
        )
    taxonomy_clause = ""
    shape_clause = ""
    if style and getattr(style, "taxonomy", None):
        taxonomy = style.taxonomy or {}
        colors = taxonomy.get("colors", [])
        techniques = taxonomy.get("techniques", [])
        shapes = taxonomy.get("shapes", [])
        styles = taxonomy.get("styles", [])
        occasions = taxonomy.get("occasions", [])
        lengths = taxonomy.get("lengths", [])
        taxonomy_clause = (
            "\n【款式标注约束（来自库存 taxonomy，必须尽量满足）】\n"
            f"- colors: {colors}\n"
            f"- techniques: {techniques}\n"
            f"- shapes: {shapes}\n"
            f"- styles: {styles}\n"
            f"- occasions: {occasions}\n"
            f"- lengths: {lengths}\n"
            "- 上述标签用于约束生成方向（颜色、工艺、甲型与长度），但若与第二张参考图视觉细节冲突，以第二张图为准。\n"
        )
        if shapes:
            shape_clause = (
                "\n【甲型硬约束（必须优先满足）】\n"
                f"- 参考款式的甲型仅允许使用: {shapes}\n"
                "- 生成时必须先保证甲型正确，再处理颜色、图案、亮片和饰品。\n"
                "- 不得把方圆型改成杏仁型，不得把杏仁型改成尖型，不得为了适配手型擅自改型。\n"
            )

    pixel_clause = ""
    geometry_clause = ""
    if pixel_control:
        image_size = pixel_control.get("image_size", {})
        user_nails = pixel_control.get("user_nails", [])
        style_nails = pixel_control.get("style_nails", [])
        pairing = pixel_control.get("pairing", [])
        length_control = pixel_control.get("length_control", {})
        compact_map = [
            {
                "i": item.get("user_index"),
                "style_i": item.get("style_index"),
                "box": item.get("user_box"),
                "style_box": item.get("style_box"),
                "target_aspect": item.get("target_aspect"),
                "extension_scale": item.get("extension_scale"),
                "rule": item.get("rule"),
            }
            for item in pairing[:10]
        ]
        pixel_clause = (
            "\n【像素级编辑控制（必须遵守）】\n"
            f"- 手图尺寸: {image_size}\n"
            f"- 本次款式图动态甲长等级: {detected_style_level or 'UNKNOWN'}\n"
            f"- 长度控制: {length_control}\n"
            f"- 识别到的手图指甲框(手图坐标系): {user_nails}\n"
            f"- 识别到的款式图甲片框(款式图坐标系): {style_nails}\n"
            f"- 款式图->手图映射控制: {compact_map}\n"
            "- 只能编辑手图中的指甲区域。长甲或中长甲只允许沿远端自由边方向延伸，不得侵入甲根、皮肤或相邻手指。\n"
            "- extension_scale 是逐指延长上限，不是必须拉满的倍率。优先保持自然比例和原图手指结构。\n"
            "- 每个指甲必须保持独立映射，不得把某个手指的纹样错贴到其他手指。\n"
        )
        geometry_clause = (
            "\n【甲型与长度几何合同（必须优先满足）】\n"
            "- 甲型和甲长都是硬约束，不是装饰建议；模型必须重建真实甲片几何，而不是把参考图当成贴图直接贴在原指甲上。\n"
            "- 若源手图的指甲比参考款更长，必须只从远端自由边开始修短，直到达到参考图的目标长度与目标长宽比；禁止保留原长甲轮廓再叠加短款图案。\n"
            "- 若源手图的指甲比参考款更短，必须只从远端自由边开始延长，直到达到参考图的目标长度与目标长宽比；禁止把长款美甲压缩、截断或塞进原有短甲轮廓里。\n"
            "- 无论延长还是修短，甲根宽度、甲沟位置、指腹形态、手指宽度与姿势都必须保持不变；变化只允许发生在远端自由边、甲片厚度、阴影和装饰细节上。\n"
            "- 每根指甲都必须单独遵守自己的 target_aspect 与 extension_scale，不得全手套用同一长度。\n"
        )
    hand_clause = ""
    if hand_analysis:
        hand_compact = hand_analysis.get("compact_json")
        hand_desc = hand_analysis.get("vision_description")
        hand_clause = (
            "\n【手图视觉分析（必须遵守）】\n"
            f"- 手图结构化识别: {hand_compact}\n"
            + (f"- 视觉说明: {hand_desc}\n" if hand_desc else "")
            + "- 仅在识别到的指甲区域进行编辑，不得改动手部其他皮肤、关节、饰品和背景。\n"
            "- 若参考款式为长甲，可沿每个指尖法向自然延长；若为短甲，只在甲床范围内编辑。\n"
        )

    return (
        "【输入】\n"
        "第一张图片是人物/手部照片，第二张图片是美甲设计参考图。\n"
        "第二张参考图已完成方向标准化：甲根在下、指尖在上。请严格按这个正向参考迁移，不得上下颠倒图案或饰品。\n"
        "不要读取或依赖任何库存款式文字描述；美甲设计只能来自第二张图片本身。\n"
        "\n"
        "【核心目标 — 局部替换】\n"
        "基于第一张人物照片，仅将指甲部分替换为第二张图中的美甲设计。"
        "脸部、手部形态、手部姿势、背景等全部保持不变。核心是只自然更换指甲区域的设计。\n"
        "\n"
        "【身份与画面锁定 — 必须】\n"
        "严禁修改人物的脸部、肤色、五官。保持手的形状、手指长度、角度与姿势。"
        "保持手在画面中的位置与构图。背景、光线、色调、镜头构图全部不变。"
        "效果必须像原图只换了美甲。\n"
        "【极其关键的手型与画布硬性锁定】用户上传的手图是唯一的基准画布。用户的手型、骨骼结构、手指长度与粗细、皮肤纹理、毛孔、背景环境以及原始的手图画布必须保持100%原封不动，绝对不能发生任何形变、改变或被模型重新绘制。只允许且必须在指甲轮廓范围内修改美甲款式，严禁改动手部其他部分。效果必须像在原始手图上直接美甲一样。\n"
        "\n"
        "【美甲设计迁移 — 重点】\n"
        "完整还原第二张图中的美甲设计，包括颜色、图案、亮片、饰品、渐变、光泽、甲片长宽比例与甲型。"
        f"{length_rule}"
        f"{shape_clause}"
        f"{taxonomy_clause}"
        f"{geometry_clause}"
        "甲型必须以参考图为准，先锁定甲型再迁移设计内容；例如圆形、方形、杏仁形、尖形、梯形等，只能从参考图中选择对应的形态。"
        "必须与手指结构自然衔接。精确还原亮片颗粒、反光效果、饰品位置。"
        "若不同手指设计不同，必须完整保留差异。不要把款式简化成单一色块、普通渐变或常见模板，不要让美甲款式变形。\n"
        "\n"
        "【光影与材质匹配 — 非常重要】\n"
        "指甲反光必须符合人物照片的光源方向，高光位置自然合理，禁止过亮或突兀。"
        "指甲与皮肤边缘自然融合，严禁出现贴上去的感觉。\n"
        "\n"
        "【高精度渲染约束】\n"
        "(Masterpiece, top quality, ultra-detailed), close-up female hand, photorealistic skin texture, "
        "clean nail contours, realistic cuticle details, glossy gel reflection, macro-lens realism.\n"
        "\n"
        "【阴影与立体感】\n"
        "在指甲下方添加自然细微阴影，保持手与指甲之间的空间层次，表现真实立体质感，例如胶甲、哑光、镜面等材质。\n"
        "\n"
        "【输出限制】\n"
        "最终只能输出一张完整人物/手部照片，严禁拼图、左右分屏、对比图、款式参考板、白底商品图、单独甲片、文字或边框。"
        "\n"
        "【反向约束（禁止）】\n"
        "deformed fingers, extra digits, missing fingers, blurred nails, distorted nail shapes, asymmetric nails, "
        "messy cuticles, fake plastic texture, low quality, bad anatomy, drawing, painting, collage, split screen, "
        "over-extended nails, needle-thin nails, widened nail roots, warped nail tips, melted decorations, mismatched nail lengths."
        + pixel_clause
        + hand_clause
    )


def _build_flux_kontext_prompt(style: NailStyle, style_visual_description: str | None = None) -> str:
    length = getattr(style, "nail_length", "natural")
    shapes = getattr(style, "taxonomy", {}).get("shapes", []) if getattr(style, "taxonomy", None) else []
    if length == "long":
        length_rule = (
            "If nails in image #2 are long/extended, make nails in image #1 long as well by naturally extending beyond fingertip."
        )
    elif length == "medium":
        length_rule = "Match medium length from image #2 on image #1."
    else:
        length_rule = "Keep nails short and natural like image #2."

    shape_rule = "Keep nail shape exactly consistent with image #2. Do not reinterpret the nail shape to fit the hand."
    if shapes:
        shape_rule = (
            f"Nail shape is a hard constraint. If image #2 taxonomy specifies {shapes}, preserve that nail shape exactly. "
            "Do not change shape to a different geometry during generation."
        )

    visual = f"Style details from image #2: {style_visual_description}." if style_visual_description else ""
    return (
        "Image #1 is the base hand photo to edit. Image #2 is the nail style reference.\n"
        "Task: replace ONLY nail design on image #1 using image #2.\n"
        "Hard constraints:\n"
        "1) Preserve hand identity, skin, pose, fingers, jewelry, background, framing and lighting exactly.\n"
        "2) Do not output collage, split-screen, extra text, product board, nail tips sheet.\n"
        "3) Copy pattern/color/gloss/decor placement from image #2 with high fidelity.\n"
        f"4) {length_rule}\n"
        f"5) {shape_rule}\n"
        "6) Output one realistic photo-level result only.\n"
        f"{visual}"
    )


def _extract_gpt_image2_result(body: dict[str, Any]) -> str | None:
    direct_keys = ["url", "image", "image_url", "result_image_url", "output_url"]
    for key in direct_keys:
        value = body.get(key)
        if isinstance(value, str) and value:
            return value

    b64_value = body.get("b64_json") or body.get("image_base64")
    if isinstance(b64_value, str) and b64_value:
        return f"data:image/png;base64,{b64_value}"

    list_keys = ["data", "images", "output", "results"]
    for key in list_keys:
        items = body.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str) and item:
                return item
            if not isinstance(item, dict):
                continue
            for image_key in direct_keys:
                value = item.get(image_key)
                if isinstance(value, str) and value:
                    return value
            b64_item = item.get("b64_json") or item.get("image_base64")
            if isinstance(b64_item, str) and b64_item:
                return f"data:image/png;base64,{b64_item}"

    choices = body.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            for image_key in direct_keys:
                                value = item.get(image_key)
                                if isinstance(value, str) and value:
                                    return value
                            b64_item = item.get("b64_json") or item.get("image_base64")
                            if isinstance(b64_item, str) and b64_item:
                                return f"data:image/png;base64,{b64_item}"

    nested_keys = ["output", "result"]
    for key in nested_keys:
        nested_value = body.get(key)
        if isinstance(nested_value, dict):
            nested_result = _extract_gpt_image2_result(nested_value)
            if nested_result:
                return nested_result
    return None


def _extract_async_task_image_url(body: dict[str, Any]) -> str | None:
    images = body.get("images")
    if isinstance(images, list):
        for item in images:
            if isinstance(item, dict):
                value = item.get("image_url")
                if isinstance(value, str) and value:
                    return value
            if isinstance(item, str) and item:
                return item
    return None


async def _estimate_style_mask_geometry(style_image_bytes: bytes, fallback_length: str) -> dict[str, Any]:
    base_scale = {"long": 1.2, "medium": 1.0, "natural": 0.75}.get(fallback_length, 1.0)
    try:
        from app.services.nail_segmenter import segment_nails

        segmentation = await segment_nails(style_image_bytes)
        aspects: list[float] = []
        areas: list[float] = []
        for box in segmentation.boxes:
            width = max(1.0, box["x2"] - box["x1"])
            height = max(1.0, box["y2"] - box["y1"])
            aspects.append(height / width)
            areas.append(width * height)
        if not aspects:
            return {
                "source": "fallback-style-length",
                "nail_count": segmentation.nail_count,
                "expansion_scale": base_scale,
                "reason": segmentation.message,
            }

        aspects.sort()
        median_aspect = aspects[len(aspects) // 2]
        if median_aspect >= 2.6:
            geometry_scale = 1.55
            inferred_length = "long"
        elif median_aspect >= 1.75:
            geometry_scale = 1.3
            inferred_length = "long"
        elif median_aspect >= 1.25:
            geometry_scale = 1.0
            inferred_length = "medium"
        else:
            geometry_scale = 0.72
            inferred_length = "natural"

        expansion_scale = max(base_scale, geometry_scale) if fallback_length in {"long", "medium"} else min(base_scale, geometry_scale)
        return {
            "source": "style-mask-geometry",
            "nail_count": segmentation.nail_count,
            "confidence": segmentation.confidence,
            "median_aspect": round(median_aspect, 3),
            "inferred_length": inferred_length,
            "expansion_scale": round(expansion_scale, 3),
            "style_box_area_avg": round(sum(areas) / len(areas), 2) if areas else 0,
        }
    except Exception as exc:
        return {
            "source": "fallback-style-length",
            "expansion_scale": base_scale,
            "reason": f"{type(exc).__name__}: {str(exc)[:160]}",
        }


async def _generate_with_gpt_image2(
    image_bytes: bytes,
    style: NailStyle,
    style_image_bytes: bytes | None = None,
    mask_image_url: str | None = None,
    pixel_control: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    provider_started = perf_counter()
    endpoint = settings.gpt_image2_api_url or settings.image2_api_url
    api_key = settings.gpt_image2_api_key or settings.image2_api_key
    if not endpoint or not api_key:
        raise ValueError("Missing GPT_IMAGE2_API_URL or GPT_IMAGE2_API_KEY")
    if not style_image_bytes:
        raise ValueError("Missing style image for GPT image2 try-on")

    preprocess_started = perf_counter()
    normalized_hand_bytes = _normalize_image_bytes(image_bytes, max_side=1024, quality=86)
    hand_normalize_ms = round((perf_counter() - preprocess_started) * 1000, 1)

    preprocess_started = perf_counter()
    cropped_style_bytes = _crop_style_card_if_present(style_image_bytes)
    style_orientation_ms = round((perf_counter() - preprocess_started) * 1000, 1)

    preprocess_started = perf_counter()
    normalized_style_bytes = _normalize_image_bytes(cropped_style_bytes, max_side=1024, quality=90)
    style_normalize_ms = round((perf_counter() - preprocess_started) * 1000, 1)

    preprocess_started = perf_counter()
    style_geometry = await _estimate_style_mask_geometry(cropped_style_bytes, getattr(style, "nail_length", "natural"))
    style_geometry_ms = round((perf_counter() - preprocess_started) * 1000, 1)
    hand_data_url = _ensure_data_url(normalized_hand_bytes)
    style_data_url = _ensure_data_url(normalized_style_bytes)
    prompt = _build_nail_tryon_prompt(style, pixel_control=pixel_control, hand_analysis=hand_analysis)
    if pixel_control is not None:
        timings = pixel_control.setdefault("timings_ms", {})
        timings["hand_image_normalize"] = hand_normalize_ms
        timings["style_orientation_normalize"] = style_orientation_ms
        timings["style_image_normalize"] = style_normalize_ms
        timings["style_geometry_analysis"] = style_geometry_ms
        timings["style_reference_preprocess"] = round(
            hand_normalize_ms + style_orientation_ms + style_normalize_ms + style_geometry_ms, 1
        )
    payload = {
        "n": 1,
        "image": [hand_data_url, style_data_url],
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "medium",
        "background": "auto",
        "output_format": "png",
    }
    mask_data_url: str | None = None
    audit_id = _debug_dump_tryon_request(
        channel="gpt-image2-hd",
        endpoint=endpoint,
        model=settings.gpt_image2_model,
        hand_bytes=normalized_hand_bytes,
        style_bytes=normalized_style_bytes,
        prompt=prompt,
        mask_data_url=mask_data_url,
        pixel_control=pixel_control,
        hand_analysis=hand_analysis,
        payload_summary={
            "image_count": len(payload["image"]),
            "has_mask": "mask" in payload,
            "size": payload["size"],
            "quality": payload["quality"],
            "output_format": payload["output_format"],
        },
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error: Exception | None = None
    try:
        request_started = perf_counter()
        async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
            for attempt in range(2):
                try:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    body = response.json()
                    break
                except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
                    last_error = exc
                    if attempt == 0:
                        await asyncio.sleep(1.5)
                        continue
                    raise
            else:
                raise last_error or TimeoutError("GPT image2 request failed")
    except Exception as exc:
        timings = (pixel_control or {}).setdefault("timings_ms", {})
        timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
        timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)
        _finalize_debug_tryon_request(audit_id, status="failed", error=str(exc)[:800], timings_ms=timings)
        raise

    timings = (pixel_control or {}).setdefault("timings_ms", {})
    timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
    timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)
    body = {
        **body,
        "_nailai_request": {
            "style_mask_geometry": style_geometry,
            "hand_mask": "disabled",
            "style_length": getattr(style, "nail_length", "natural"),
            "pixel_control": pixel_control or {},
            "hand_analysis": hand_analysis or {},
            "prompt_preview": prompt[:1200],
        },
    }
    image_url = _extract_gpt_image2_result(body)
    if image_url:
        _finalize_debug_tryon_request(audit_id, status="succeeded", result_image_url=image_url, timings_ms=timings)
        body["_nailai_audit_id"] = audit_id
        return image_url, body
    error = str(body.get("message") or body.get("error") or "GPT image2 did not return an image")
    _finalize_debug_tryon_request(audit_id, status="failed", error=error)
    raise ValueError(error)


async def _generate_with_doubao_seedream(
    image_bytes: bytes,
    style: NailStyle,
    style_image_bytes: bytes | None = None,
    mask_image_url: str | None = None,
    pixel_control: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    provider_started = perf_counter()
    endpoint = settings.doubao_image_api_url
    api_key = settings.doubao_image_api_key
    if not endpoint or not api_key:
        raise ValueError("Missing DOUBAO_IMAGE_API_URL or DOUBAO_IMAGE_API_KEY")
    if not style_image_bytes:
        raise ValueError("Missing style image for Doubao fast try-on")

    preprocess_started = perf_counter()
    normalized_hand_bytes = _normalize_image_bytes(image_bytes, max_side=1024, quality=84)
    hand_normalize_ms = round((perf_counter() - preprocess_started) * 1000, 1)

    preprocess_started = perf_counter()
    cropped_style_bytes = _crop_style_card_if_present(style_image_bytes)
    style_orientation_ms = round((perf_counter() - preprocess_started) * 1000, 1)

    preprocess_started = perf_counter()
    normalized_style_bytes = _normalize_image_bytes(cropped_style_bytes, max_side=1024, quality=88)
    style_normalize_ms = round((perf_counter() - preprocess_started) * 1000, 1)
    hand_data_url = _ensure_data_url(normalized_hand_bytes)
    style_data_url = _ensure_data_url(normalized_style_bytes)
    prompt = _build_nail_tryon_prompt(style, pixel_control=pixel_control, hand_analysis=hand_analysis)
    if pixel_control is not None:
        timings = pixel_control.setdefault("timings_ms", {})
        timings["hand_image_normalize"] = hand_normalize_ms
        timings["style_orientation_normalize"] = style_orientation_ms
        timings["style_image_normalize"] = style_normalize_ms
        timings["style_reference_preprocess"] = round(
            hand_normalize_ms + style_orientation_ms + style_normalize_ms, 1
        )

    payload = {
        "model": settings.doubao_image_model,
        "prompt": prompt,
        "image": [hand_data_url, style_data_url],
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "size": "2K",
        "stream": False,
        "watermark": True,
    }
    audit_id = _debug_dump_tryon_request(
        channel="doubao-seedream-fast",
        endpoint=endpoint,
        model=settings.doubao_image_model,
        hand_bytes=normalized_hand_bytes,
        style_bytes=normalized_style_bytes,
        prompt=prompt,
        mask_data_url=mask_image_url,
        pixel_control=pixel_control,
        hand_analysis=hand_analysis,
        payload_summary={
            "image_count": len(payload["image"]),
            "has_mask_field": False,
            "mask_used_as_api_field": False,
            "size": payload["size"],
            "watermark": payload["watermark"],
        },
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        request_started = perf_counter()
        async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        timings = (pixel_control or {}).setdefault("timings_ms", {})
        timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
        timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)
        _finalize_debug_tryon_request(audit_id, status="failed", error=str(exc)[:800], timings_ms=timings)
        raise

    timings = (pixel_control or {}).setdefault("timings_ms", {})
    timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
    timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)
    image_url = _extract_gpt_image2_result(body)
    if not image_url:
        error = str(body.get("message") or body.get("error") or "Doubao did not return an image url")
        _finalize_debug_tryon_request(audit_id, status="failed", error=error)
        raise ValueError(error)
    body = {
        **body,
        "_nailai_audit_id": audit_id,
        "_nailai_request": {
            "provider": "doubao-seedream",
            "model": settings.doubao_image_model,
            "hand_analysis": hand_analysis or {},
            "prompt_preview": prompt[:1200],
        },
    }
    _finalize_debug_tryon_request(audit_id, status="succeeded", result_image_url=image_url, timings_ms=timings)
    return image_url, body


async def _generate_with_flux_kontext_dev(
    image_bytes: bytes,
    style: NailStyle,
    style_image_bytes: bytes | None = None,
    mask_image_url: str | None = None,
) -> tuple[str, dict[str, Any]]:
    api_key = settings.gpt_image2_api_key or settings.image2_api_key
    if not api_key:
        raise ValueError("Missing API key for FLUX Kontext Dev")
    if not style_image_bytes:
        raise ValueError("Missing style image for FLUX Kontext Dev try-on")

    submit_url = settings.image2_api_url or settings.flux_kontext_async_url
    task_url = settings.async_task_result_url

    normalized_hand_bytes = _normalize_image_bytes(image_bytes, max_side=1024, quality=86)
    cropped_style_bytes = _crop_style_card_if_present(style_image_bytes)
    normalized_style_bytes = _normalize_image_bytes(cropped_style_bytes, max_side=1024, quality=90)
    style_geometry = await _estimate_style_mask_geometry(cropped_style_bytes, getattr(style, "nail_length", "natural"))

    style_visual_description = await analyze_nail_style_image(cropped_style_bytes)

    images = [
        _ensure_data_url(normalized_hand_bytes),
        _ensure_data_url(normalized_style_bytes),
    ]

    payload = {
        "prompt": _build_flux_kontext_prompt(style, style_visual_description),
        "images": images,
        "fast_mode": False,
        "size": "1024*1024",
        "num_inference_steps": 40,
        "guidance_scale": 5.5,
        "num_images": 1,
        "seed": -1,
        "output_format": "png",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
        submit_resp = await client.post(submit_url, json=payload, headers=headers)
        submit_resp.raise_for_status()
        submit_body = submit_resp.json()
        task_id = submit_body.get("task_id")
        if not task_id:
            raise ValueError(f"FLUX submit failed: {submit_body}")

        last_body: dict[str, Any] = submit_body
        attempts = max(10, int(settings.image2_timeout_seconds // 2))
        for _ in range(attempts):
            await asyncio.sleep(2)
            poll_resp = await client.get(task_url, params={"task_id": task_id}, headers=headers)
            poll_resp.raise_for_status()
            last_body = poll_resp.json()
            task = last_body.get("task", {})
            status = task.get("status")
            if status == "TASK_STATUS_SUCCEED":
                result_url = _extract_async_task_image_url(last_body)
                if result_url:
                    return result_url, {
                        "submit": submit_body,
                        "result": last_body,
                        "_nailai_request": {
                            "style_mask_geometry": style_geometry,
                            "mask_guided": False,
                            "style_length": getattr(style, "nail_length", "natural"),
                            "style_visual_description": style_visual_description,
                        },
                    }
                raise ValueError(f"FLUX task succeeded but no image url: {last_body}")
            if status == "TASK_STATUS_FAILED":
                reason = task.get("reason") or last_body.get("reason") or "unknown"
                raise ValueError(f"FLUX task failed: {reason}")

    raise TimeoutError("FLUX Kontext task polling timed out")


async def _generate_with_dashscope_wan(
    image_bytes: bytes, style: NailStyle, style_image_bytes: bytes | None = None
) -> tuple[str, dict[str, Any]]:
    if not settings.image2_api_key:
        raise ValueError("Missing IMAGE2_API_KEY")

    endpoint = settings.image2_api_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    if style_image_bytes:
        cropped_style_bytes = _crop_style_card_if_present(style_image_bytes)
        content: list[dict[str, str]] = [{"image": _ensure_data_url(image_bytes)}, {"image": _ensure_data_url(cropped_style_bytes)}]
        
        length_instruction = "⚠️ 重点提示：目标款式为【延长甲/长指甲】。请在原图手指基础上，向外延伸构建长指甲形状，改变原有本甲的长度和轮廓，生成长甲效果。" if getattr(style, "nail_length", "natural") in ["long", "medium"] else "⚠️ 重点提示：目标款式为【本甲/短甲】。请严格保留原图手部的自然指甲长度和边缘形状，绝不可拉长指甲，仅在现有甲床上进行图案替换。"
        style_semantics = f"目标款式特征：{style.name}，主色{style.color}，质感{style.finish}，设计元素包含{', '.join(style.tags[:6])}。"
        
        prompt_text = (
            "你是专业美甲试戴图像编辑助手。输入包含两张图片：第一张图片是用户上传的真实手部照片（唯一的生成画布），"
            "第二张图片是美甲款式参考图（仅用于提取颜色、图案、设计细节和质感）。\n"
            "【款式与长度约束】：\n"
            f"{style_semantics}\n"
            f"{length_instruction}\n"
            "【替换要求】：\n"
            "1. 请将第一张手图中的指甲表面替换为第二张图的款式设计，严格保留第一张图中除指甲外的所有内容：手型、手指姿势、皮肤纹理、手部饰品、背景、光照和构图。\n"
            "2. 若第二张款式参考图同时包含左手和右手（两只手），而第一张手图仅为单手，请先自动辨识第一张图是左手还是右手，并严格只对应从第二张图中对应的左手或右手提取指甲花纹与颜色。\n"
            "3. 迁移时，指甲款式必须在两张图的手指类型之间一一精确映射（大拇指对应大拇指款式，食指对应食指款式，中指、无名指、小拇指同理），绝不能发生手指错位映射花纹的情况。"
        )
        content.append(
            {
                "text": (
                    f"{prompt_text}\n"
                    "输出必须且只能是局部修改后的第一张手图（完整手部照片本身），绝对不能把第二张款式图拼贴或以画中画（Picture-in-Picture）形式嵌入，严禁双图并排、左右拼图、说明文字或款式参考边框卡片。"
                )
            }
        )
    else:
        content = [{"image": _ensure_data_url(image_bytes)}]
        prompt_text = (
            "你是专业美甲试戴图像编辑助手。请在这张用户手部照片的可见指甲区域生成目标美甲效果，"
            "保持原手型、姿势、肤色、背景、光照和构图不变。"
        )
        content.append(
            {
                "text": (
                    f"{prompt_text}"
                    f"目标款式：{style.name}，颜色：{style.color}，质感：{style.finish}。"
                    "输出必须是一张完整的用户手部照片，不要输出款式参考板、单独甲片、文字、边框、拼图或说明。"
                )
            }
        )
    payload = {
        "model": settings.image2_model,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": {"size": "2K", "n": 1, "watermark": False, "thinking_mode": True},
    }
    headers = {
        "Authorization": f"Bearer {settings.image2_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        _finalize_debug_tryon_request(audit_id, status="failed", error=str(exc)[:800])
        raise

    image_url = _extract_dashscope_image_url(body)
    if image_url:
        return image_url, body
    raise ValueError(body.get("message") or body.get("code") or "DashScope did not return an image")


async def _generate_with_qwen_image2(
    image_bytes: bytes,
    style: NailStyle,
    style_image_bytes: bytes | None = None,
    mask_image_url: str | None = None,
    pixel_control: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
    model_override: str | None = None,
) -> tuple[str, dict[str, Any]]:
    provider_started = perf_counter()
    api_key = settings.qwen_image_api_key or settings.image2_api_key
    if not api_key:
        raise ValueError("Missing QWEN_IMAGE_API_KEY")

    endpoint = settings.qwen_image_api_url
    model_name = model_override or settings.qwen_image_model
    
    hand_pre_started = perf_counter()
    normalized_hand_bytes = _normalize_image_bytes(image_bytes, max_side=1024, quality=86)
    hand_normalize_ms = round((perf_counter() - hand_pre_started) * 1000, 1)

    style_orientation_ms = 0.0
    style_normalize_ms = 0.0
    normalized_style_bytes = b""

    if style_image_bytes:
        style_pre_started = perf_counter()
        cropped_style_bytes = _crop_style_card_if_present(style_image_bytes)
        style_orientation_ms = round((perf_counter() - style_pre_started) * 1000, 1)
        prompt = _build_nail_tryon_prompt(style, pixel_control=pixel_control, hand_analysis=hand_analysis)
        content = [
            {"image": _ensure_data_url(image_bytes)},
            {"image": _ensure_data_url(cropped_style_bytes)},
            {"text": prompt},
        ]
        style_pre_started = perf_counter()
        normalized_style_bytes = _normalize_image_bytes(cropped_style_bytes, max_side=1024, quality=90)
        style_normalize_ms = round((perf_counter() - style_pre_started) * 1000, 1)
    else:
        color_notes = "、".join(style.palette[:3]) if style.palette else style.color
        prompt = (
            "这是一个极其严格的真实照片级局部修图任务。你必须把输入照片作为唯一的画布，"
            "原封不动地保留所有内容：原始手型、手指位置、粗细、皮肤纹理、毛孔、色差、戒饰、"
            "背景、光照环境、阴影、相机视角及构图，绝不能有任何改变。\n"
            "唯一允许且必须修改的区域是：每个可见指甲的表面。\n"
            f"请把所有指甲自然地修改为「{style.name}」款式：主色{style.color}，质感{style.finish}，参考色{color_notes}，"
            f"相关元素{', '.join(style.tags[:6])}。\n"
            "【极其关键的真实感约束】：\n"
            "1. 必须像真实美甲师在原本指甲上涂了凝胶甲油后拍摄的照片。\n"
            "2. 颜色和光泽必须完全服帖在原始甲床曲面上，绝不能平铺。\n"
            "3. 边缘必须顺着原图指甲的真实轮廓和甲沟自然收口，严禁溢出、严禁超出现有指甲边界。\n"
            "4. 保留甲沟、指尖皮肤与甲缘交界处的真实肉色和细微阴影。\n"
            "5. 材质反光、高光必须与原图的光源方向完全一致。\n"
            "6. 远处的指甲要遵守相机的景深，出现与原图一致的轻微模糊。\n"
            "如果款式有图案，请让图案随着指甲弧度自然透视变形，绝不能像平面贴纸。\n"
            "严禁输出：单独甲片、款式参考板、拼图、白底商品图、改变手部/背景、硬边贴纸感、浮在指甲上的图层、"
            "塑料假甲片、过度锐化、过饱和、卡通插画感。"
        )
        content = [
            {"image": _ensure_data_url(image_bytes)},
            {"text": prompt}
        ]

    payload = {
        "model": model_name,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": {"size": "2K", "n": 1, "watermark": False, "thinking_mode": True},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if not normalized_style_bytes:
        style_pre_started = perf_counter()
        cropped = _crop_style_card_if_present(style_image_bytes or b"")
        style_orientation_ms = round((perf_counter() - style_pre_started) * 1000, 1)
        style_pre_started = perf_counter()
        normalized_style_bytes = _normalize_image_bytes(cropped, max_side=1024, quality=90)
        style_normalize_ms = round((perf_counter() - style_pre_started) * 1000, 1)
    if pixel_control is not None:
        timings = pixel_control.setdefault("timings_ms", {})
        timings["hand_image_normalize"] = hand_normalize_ms
        timings["style_orientation_normalize"] = style_orientation_ms
        timings["style_image_normalize"] = style_normalize_ms
        timings["style_reference_preprocess"] = round(
            hand_normalize_ms + style_orientation_ms + style_normalize_ms, 1
        )
    audit_id = _debug_dump_tryon_request(
        channel="qwen-image-edit-fast",
        endpoint=endpoint,
        model=model_name,
        hand_bytes=normalized_hand_bytes,
        style_bytes=normalized_style_bytes,
        prompt=prompt,
        mask_data_url=mask_image_url,
        pixel_control=pixel_control,
        hand_analysis=hand_analysis,
        payload_summary={
            "image_count": sum(1 for item in content if "image" in item),
            "has_mask_field": False,
            "mask_used_as_api_field": False,
            "size": payload["parameters"]["size"],
        },
    )
    request_started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        timings = (pixel_control or {}).setdefault("timings_ms", {})
        timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
        timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)
        _finalize_debug_tryon_request(audit_id, status="failed", error=str(exc)[:800], timings_ms=timings)
        raise

    timings = (pixel_control or {}).setdefault("timings_ms", {})
    timings["image_generation_api"] = round((perf_counter() - request_started) * 1000, 1)
    timings["provider_total"] = round((perf_counter() - provider_started) * 1000, 1)

    body = {
        **body,
        "_nailai_request": {
            "style_length": getattr(style, "nail_length", "natural"),
            "pixel_control": pixel_control or {},
            "hand_analysis": hand_analysis or {},
            "prompt_preview": prompt[:1200],
        },
    }

    image_url = _extract_dashscope_image_url(body)
    if image_url:
        body["_nailai_audit_id"] = audit_id
        _finalize_debug_tryon_request(audit_id, status="succeeded", result_image_url=image_url, timings_ms=timings)
        return image_url, body
    error = str(body.get("message") or body.get("code") or "Qwen Image 2.0 did not return an image")
    _finalize_debug_tryon_request(audit_id, status="failed", error=error)
    raise ValueError(error)


async def _generate_with_dashscope_imageedit(image_bytes: bytes, style: NailStyle) -> tuple[str, dict[str, Any]]:
    if not settings.image2_api_key:
        raise ValueError("Missing IMAGE2_API_KEY")

    endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"
    if settings.image2_api_url and "dashscope" in settings.image2_api_url:
        endpoint = settings.image2_api_url
    prompt = (
        "请对这张用户手部照片进行真实美甲试戴编辑。严格保留原图的手型、手部姿势、肤色、背景、光照、构图和相机视角，"
        "只修改可见指甲区域。不要生成单独甲片，不要改变手和背景。"
        f"把所有可见指甲改成「{style.name}」风格，颜色为{style.color}，质感为{style.finish}。"
        f"风格关键词：{', '.join(style.tags[:6])}。"
        "生成自然真实的手机照片效果：颜色贴合原本甲床曲率，边缘沿甲沟自然收口，高光和阴影跟随原图光源，"
        "不要有贴纸感、硬边、浮层、塑料假甲片或过度锐化。"
    )
    payload = {
        "model": settings.image2_model,
        "input": {
            "function": "description_edit",
            "prompt": prompt[:780],
            "base_image_url": _ensure_data_url(image_bytes),
        },
        "parameters": {"n": 1, "watermark": False, "strength": 0.55},
    }
    headers = {
        "Authorization": f"Bearer {settings.image2_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
        submit_response = await client.post(endpoint, json=payload, headers=headers)
        submit_response.raise_for_status()
        submit_body = submit_response.json()
        task_id = submit_body.get("output", {}).get("task_id")
        if not task_id:
            raise ValueError(submit_body.get("message") or "DashScope image edit did not return task_id")

        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        attempts = max(1, int(settings.image2_timeout_seconds // 2))
        latest_body: dict[str, Any] = submit_body
        for _ in range(attempts):
            await asyncio.sleep(2)
            poll_response = await client.get(task_url, headers={"Authorization": f"Bearer {settings.image2_api_key}"})
            poll_response.raise_for_status()
            latest_body = poll_response.json()
            output = latest_body.get("output", {})
            status = output.get("task_status")
            if status == "SUCCEEDED":
                results = output.get("results", [])
                if results and results[0].get("url"):
                    return results[0]["url"], {"submit": submit_body, "result": latest_body}
                raise ValueError("DashScope image edit succeeded without image url")
            if status == "FAILED":
                raise ValueError(output.get("message") or output.get("code") or "DashScope image edit failed")

    raise TimeoutError(f"DashScope image edit task timed out: {task_id}")


async def _generate_with_openai_compatible(
    image_bytes: bytes, style: NailStyle, style_image_bytes: bytes | None = None
) -> tuple[str, dict]:
    base_url = settings.openai_compatible_base_url
    api_key = settings.openai_compatible_api_key or settings.image2_api_key
    if not base_url or not api_key:
        raise ValueError("Missing OPENAI_COMPATIBLE_BASE_URL or OPENAI_COMPATIBLE_API_KEY")

    endpoint = urljoin(base_url.rstrip("/") + "/", "images/edits")
    files: list[tuple[str, tuple[str, bytes, str]]] = [("image", ("hand.png", image_bytes, "image/png"))]
    if style_image_bytes:
        files.append(("image", ("style.png", style_image_bytes, "image/png")))
    data = {
        "model": settings.openai_compatible_model,
        "prompt": _build_nail_tryon_prompt(style),
        "size": "1024x1024",
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
        response = await client.post(endpoint, files=files, data=data, headers=headers)
        response.raise_for_status()
        body = response.json()

    if body.get("data") and isinstance(body["data"], list) and body["data"]:
        item = body["data"][0]
        if item.get("url"):
            return item["url"], body
        if item.get("b64_json"):
            return f"data:image/png;base64,{item['b64_json']}", body

    raise ValueError("OpenAI-compatible API did not return image url or b64_json")


async def generate_try_on(
    image_bytes: bytes,
    style: NailStyle,
    style_image_bytes: bytes | None = None,
    mask_image_url: str | None = None,
    control_payload: dict[str, Any] | None = None,
    hand_analysis: dict[str, Any] | None = None,
    generation_mode: str = "hd",
) -> tuple[str, str, dict]:
    payload_hash = hashlib.sha256(image_bytes[:2048] + style.id.encode()).hexdigest()[:16]
    if settings.enable_mock_ai:
        return _mock_try_on_image(image_bytes, style), "mock-image2", {
            "cache_key": payload_hash,
            "mode": "mock-mask-aware" if mask_image_url else "mock",
        }

    mode = generation_mode.lower().strip()
    if mode not in {"hd", "regular", "fast"}:
        logger.warning("Unknown try-on generation_mode=%s, falling back to hd", generation_mode)
        mode = "hd"
    logger.info("NailAI try-on generation mode=%s", mode)

    errors: list[dict[str, Any]] = []

    async def _try_provider(provider_name: str) -> tuple[str, str, dict] | None:
        try:
            if provider_name == "gpt":
                result_image, body = await _generate_with_gpt_image2(
                    image_bytes,
                    style,
                    style_image_bytes,
                    mask_image_url,
                    pixel_control=control_payload,
                    hand_analysis=hand_analysis,
                )
                return result_image, "gpt-image2", {
                    "provider": body,
                    "cache_key": payload_hash,
                    "mode": "jiekou-gpt-image-2-edit",
                    "model": settings.gpt_image2_model,
                    "mask_guided": bool(mask_image_url),
                    "mask_expansion": getattr(style, "nail_length", "natural"),
                }
            if provider_name == "doubao":
                result_image, body = await _generate_with_doubao_seedream(
                    image_bytes,
                    style,
                    style_image_bytes,
                    mask_image_url,
                    pixel_control=control_payload,
                    hand_analysis=hand_analysis,
                )
                return result_image, "doubao-seedream-regular", {
                    "provider": body,
                    "cache_key": payload_hash,
                    "mode": "regular-doubao-seedream",
                    "model": settings.doubao_image_model,
                    "mask_guided": bool(mask_image_url),
                }
            if provider_name == "qwen":
                result_image, body = await _generate_with_qwen_image2(
                    image_bytes,
                    style,
                    style_image_bytes,
                    mask_image_url=mask_image_url,
                    pixel_control=control_payload,
                    hand_analysis=hand_analysis,
                    model_override=settings.qwen_fast_model,
                )
                return result_image, "qwen-image-edit-fast", {
                    "provider": body,
                    "cache_key": payload_hash,
                    "mode": "fast-qwen-image-edit",
                    "model": settings.qwen_fast_model,
                    "mask_guided": bool(mask_image_url),
                }
            raise ValueError(f"unknown_provider_{provider_name}")
        except Exception as exc:
            errors.append({"provider": provider_name, "error": _provider_error_payload(exc)})
            return None

    # 降级顺序：
    # - fast: 千问优先
    # - hd: GPT → 豆包兜底
    # - regular: 豆包 → GPT 兜底
    fallback_orders = {
        "hd": ["gpt", "doubao"],
        "regular": ["doubao", "gpt"],
        "fast": ["qwen"],
    }
    for provider_name in fallback_orders[mode]:
        output = await _try_provider(provider_name)
        if output:
            result_image, channel, payload = output
            payload["fallback_chain"] = fallback_orders[mode]
            payload["fallback_errors"] = errors
            return result_image, channel, payload

    raise RuntimeError(f"try_on_all_channels_failed: {errors}")
