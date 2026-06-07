import base64
import json
import logging
import re
from io import BytesIO
from typing import Any

import httpx
from PIL import Image, ImageOps

from app.config import settings
from app.services.nail_segmenter import segment_nails

logger = logging.getLogger(__name__)


def _image_data_url(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _extract_message_text(body: dict[str, Any]) -> str | None:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        value = content.strip()
        return value or None
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                txt = item.get("text")
                if isinstance(txt, str) and txt.strip():
                    texts.append(txt.strip())
        if texts:
            return "\n".join(texts)
    return None


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    # Qwen VL occasionally emits `"box_2d":":123, ...]` instead of
    # `"box_2d":[123, ...]`. Repair only this known coordinate-field drift.
    text = re.sub(r'("box_2d"\s*:\s*)":\s*(-?\d)', r"\1[\2", text)
    text = re.sub(r'("bbox_2d"\s*:\s*)":\s*(-?\d)', r"\1[\2", text)
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            logger.debug("Failed to parse fenced JSON, trying raw text")

    try:
        return json.loads(text)
    except Exception:
        logger.debug("Failed to parse raw text as JSON, trying substring")
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def _parse_qwen_grounding_nails(payload: dict[str, Any], width: int, height: int) -> list[dict[str, Any]]:
    nails_raw = payload.get("nails")
    if not isinstance(nails_raw, list):
        # compatible with {"detections":[{"box_2d":[...],"label":"nail_1"}]}
        detections = payload.get("detections")
        if isinstance(detections, list):
            nails_raw = detections
        else:
            return []
    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(nails_raw):
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox_2d") or item.get("box_2d")
        if not (isinstance(bbox, list) and len(bbox) == 4):
            continue
        try:
            x1, y1, x2, y2 = [float(v) for v in bbox]
        except Exception:
            continue
        coordinate_space = str(payload.get("coordinate_space", "")).lower()
        if coordinate_space in {"normalized_1000", "0-1000", "normalized"}:
            x1, x2 = x1 * width / 1000.0, x2 * width / 1000.0
            y1, y2 = y1 * height / 1000.0, y2 * height / 1000.0
        x1 = max(0.0, min(x1, float(width - 1)))
        y1 = max(0.0, min(y1, float(height - 1)))
        x2 = max(x1 + 1.0, min(x2, float(width)))
        y2 = max(y1 + 1.0, min(y2, float(height)))
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        parsed.append(
            {
                "index": index,
                "finger": (
                    item.get("finger")
                    if isinstance(item.get("finger"), str)
                    else (item.get("label") if isinstance(item.get("label"), str) else f"nail-{index + 1}")
                ),
                "box": {"x": round(x1, 1), "y": round(y1, 1), "w": round(w, 1), "h": round(h, 1)},
                "center": {"x": round(cx, 1), "y": round(cy, 1)},
                "norm": {
                    "x": round(x1 / width, 4),
                    "y": round(y1 / height, 4),
                    "w": round(w / width, 4),
                    "h": round(h / height, 4),
                    "cx": round(cx / width, 4),
                    "cy": round(cy / height, 4),
                },
                "aspect": round(h / max(w, 1.0), 3),
                "confidence": round(float(item.get("confidence", 0.0) or 0.0), 4),
            }
        )
    return sorted(parsed, key=lambda item: item["center"]["x"])


async def analyze_nail_style_geometry(style_image_bytes: bytes) -> dict[str, Any]:
    image = Image.open(BytesIO(style_image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    result: dict[str, Any] = {
        "image_size": {"width": width, "height": height},
        "nails": [],
        "nail_count": 0,
        "style_level": None,
        "analysis_source": "none",
    }
    if not settings.vision_analyzer_enabled:
        return result
    if not (settings.vision_analyzer_api_key or settings.qwen_chat_api_key or settings.qwen_image_api_key):
        return result

    prompt = (
        "请分析这张美甲款式参考图，并只输出一个 JSON 对象（不要 markdown，不要解释）。\n"
        "识别图中所有甲片。坐标统一使用 0 到 1000 的归一化坐标系，不要使用图片原始像素。\n"
        "判断整体甲长等级：SHORT、MEDIUM 或 LONG。判断主要甲型，并简要描述款式视觉元素。\n"
        "输出格式严格如下：\n"
        "{\n"
        '  "coordinate_space": "normalized_1000",\n'
        '  "nails": [{"label":"nail_1","box_2d":[x1,y1,x2,y2],"confidence":0.0}],\n'
        '  "style_level": "SHORT|MEDIUM|LONG",\n'
        '  "nail_shape": "",\n'
        '  "visual_description": ""\n'
        "}\n"
        "注意：如果款式图中的甲片是倒置展示，也按甲片本身识别，不要误判长度。"
    )
    try:
        body = await _call_vision_api(prompt, style_image_bytes)
        content = _extract_message_text(body)
        parsed = _extract_json_blob(content or "")
        if isinstance(parsed, dict):
            nails = _parse_qwen_grounding_nails(parsed, width, height)
            style_level = str(parsed.get("style_level", "")).upper()
            if style_level not in {"SHORT", "MEDIUM", "LONG"}:
                style_level = None
            result.update(
                {
                    "nails": nails,
                    "nail_count": len(nails),
                    "style_level": style_level,
                    "nail_shape": parsed.get("nail_shape"),
                    "visual_description": parsed.get("visual_description"),
                    "vision_raw_json": parsed,
                    "analysis_source": "qwen3-vl-style-analysis",
                }
            )
    except Exception as exc:
        result["vision_error"] = f"{type(exc).__name__}: {str(exc)[:180]}"
    return result


async def _call_vision_api(prompt: str, image_bytes: bytes) -> dict[str, Any]:
    base_url = (
        settings.vision_analyzer_api_url
        or settings.qwen_chat_api_url
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    api_key = settings.vision_analyzer_api_key or settings.qwen_chat_api_key or settings.qwen_image_api_key
    if not endpoint or not api_key:
        raise ValueError("Missing vision analyzer endpoint or api key")
    payload = {
        "model": settings.vision_analyzer_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_data_url(image_bytes)}},
                ],
            }
        ],
        "temperature": 0.0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=min(settings.image2_timeout_seconds, 35)) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def analyze_nail_style_image(style_image_bytes: bytes) -> str | None:
    if not settings.vision_analyzer_enabled:
        return None
    if not (settings.vision_analyzer_api_key or settings.qwen_chat_api_key or settings.qwen_image_api_key):
        return None

    prompt = (
        "请只分析这张美甲设计参考图，输出给图像编辑模型使用的简洁中文视觉描述。"
        "不要编造图片中没有的内容。重点描述："
        "1. 甲长：短甲/本甲/中长甲/长甲；"
        "2. 甲型：圆形/方形/杏仁形/尖形/梯形等；"
        "3. 每个手指或每枚甲片的颜色、图案、渐变、亮片、饰品、水钻、金属件、手绘元素；"
        "4. 光泽和材质：亮面/哑光/镜面/猫眼/果冻/透明等；"
        "5. 如果左右手或不同甲片设计不同，要保留差异。"
        "只输出视觉描述，不要输出标题、解释或建议。"
    )

    body = await _call_vision_api(prompt, style_image_bytes)
    content = _extract_message_text(body)
    return content[:1200] if content else None


def _normalize_box(box: dict[str, float], width: int, height: int, index: int) -> dict[str, Any]:
    x1 = float(box.get("x1", 0.0))
    y1 = float(box.get("y1", 0.0))
    x2 = float(box.get("x2", 0.0))
    y2 = float(box.get("y2", 0.0))
    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0
    return {
        "index": index,
        "box": {"x": round(x1, 1), "y": round(y1, 1), "w": round(w, 1), "h": round(h, 1)},
        "center": {"x": round(cx, 1), "y": round(cy, 1)},
        "norm": {
            "x": round(x1 / width, 4),
            "y": round(y1 / height, 4),
            "w": round(w / width, 4),
            "h": round(h / height, 4),
            "cx": round(cx / width, 4),
            "cy": round(cy / height, 4),
        },
        "aspect": round(h / w, 3),
        "confidence": round(float(box.get("confidence", 0.0)), 4),
    }


async def analyze_hand_image_geometry(hand_image_bytes: bytes) -> dict[str, Any]:
    image = Image.open(BytesIO(hand_image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size

    result: dict[str, Any] = {
        "image_size": {"width": width, "height": height},
        "nails": [],
        "nail_count": 0,
        "segmentation_available": False,
        "analysis_source": "none",
        "vision_description": None,
    }

    segmentation = await segment_nails(hand_image_bytes)
    if segmentation.available and segmentation.boxes:
        sorted_boxes = sorted(segmentation.boxes, key=lambda item: ((item.get("x1", 0.0) + item.get("x2", 0.0)) / 2.0))
        result["nails"] = [
            _normalize_box(box, width, height, index)
            for index, box in enumerate(sorted_boxes)
        ]
        result["nail_count"] = len(result["nails"])
        result["segmentation_available"] = True
        result["analysis_source"] = "yolo-nail-segmentation"
        result["segmentation_confidence"] = round(float(segmentation.confidence), 4)
        result["segmentation_message"] = segmentation.message

    if (
        settings.vision_analyzer_enabled
        and (settings.vision_analyzer_api_key or settings.qwen_chat_api_key or settings.qwen_image_api_key)
    ):
        prompt = (
            "请仔细分析这张手部图片，并只输出一个 JSON 对象（不要 markdown，不要解释）。\n"
            "任务：\n"
            "1) 识别所有可见指甲，返回精准 2D 边界框；\n"
            "2) 分析手部特征（肤色、手指修长程度、当前甲型）；\n"
            "3) 给出适配的美甲风格建议（显白、修长修饰）。\n"
            "输出格式严格如下：\n"
            "{\n"
            '  "coordinate_space": "normalized_1000",\n'
            '  "nails": [\n'
            '    {"label":"nail_1","box_2d":[x1,y1,x2,y2],"confidence":0.0}\n'
            "  ],\n"
            '  "hand_features": {"skin_tone":"", "finger_shape":"", "current_nail_shape":""},\n'
            '  "style_suggestions": ["", ""],\n'
            '  "summary": ""\n'
            "}\n"
            "要求：所有 box_2d 坐标必须使用 0 到 1000 的归一化坐标系。"
        )
        try:
            body = await _call_vision_api(prompt, hand_image_bytes)
            content = _extract_message_text(body)
            if content:
                parsed = _extract_json_blob(content)
                if isinstance(parsed, dict):
                    qwen_nails = _parse_qwen_grounding_nails(parsed, width, height)
                    if qwen_nails:
                        result["nails"] = qwen_nails
                        result["nail_count"] = len(qwen_nails)
                        result["analysis_source"] = "qwen-vl-grounding"
                        result["vision_summary"] = parsed.get("summary")
                        if isinstance(parsed.get("hand_features"), dict):
                            result["hand_features"] = parsed.get("hand_features")
                        if isinstance(parsed.get("style_suggestions"), list):
                            result["style_suggestions"] = parsed.get("style_suggestions")
                        result["vision_raw_json"] = parsed
                        result["segmentation_available"] = result.get("segmentation_available", False)
                result["vision_description"] = content[:1200]
                if result["analysis_source"] == "none":
                    result["analysis_source"] = "vision-only"
        except Exception as exc:
            result["vision_error"] = f"{type(exc).__name__}: {str(exc)[:180]}"

    result["compact_json"] = json.dumps(
        {
            "size": result.get("image_size"),
            "nail_count": result.get("nail_count"),
            "nails": [
                {
                    "i": item.get("index"),
                    "norm": item.get("norm"),
                    "aspect": item.get("aspect"),
                }
                for item in result.get("nails", [])[:10]
            ],
        },
        ensure_ascii=False,
    )
    return result
