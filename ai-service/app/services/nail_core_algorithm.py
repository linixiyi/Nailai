import base64
import json
import logging
from io import BytesIO
import base64
from pathlib import Path
from uuid import uuid4
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import cv2
import numpy as np
import httpx
from PIL import Image

from app.config import settings
from app.schemas import NailStyle
from app.services.image2_client import generate_try_on
from app.services.nail_segmenter import segment_nails
from app.services.style_vision_analyzer import analyze_hand_image_geometry, analyze_nail_style_geometry

logger = logging.getLogger(__name__)

# Try to import YOLO, assuming ultralytics is installed
try:
    from ultralytics import YOLO
    import torch
    _original_load = torch.load
    def _patched_load(*args, **kwargs):
        kwargs["weights_only"] = False
        return _original_load(*args, **kwargs)
    torch.load = _patched_load
except ImportError:
    YOLO = None

STYLE_LEVEL = Literal["SHORT", "MEDIUM", "LONG"]

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_path() -> Path:
    path = Path(settings.nail_segmentation_model_path)
    if path.is_absolute():
        return path
    return _project_root() / path


_MODEL = None

def get_yolo_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if YOLO is None:
        raise RuntimeError("ultralytics is not installed.")
    path = _model_path()
    if not path.exists():
        raise FileNotFoundError(f"YOLO model not found: {path}")
    _MODEL = YOLO(str(path))
    return _MODEL


def upload_to_oss(file_bytes: bytes, ext: str = "png") -> str:
    """
    Mock OSS Upload.
    Since DashScope APIs accept Base64 encoded images directly in the format 'data:image/png;base64,...',
    we can simulate the upload by returning the encoded data URL.
    """
    encoded = base64.b64encode(file_bytes).decode("ascii")
    mime_type = "image/jpeg" if ext.lower() in ("jpg", "jpeg") else "image/png"
    return f"data:{mime_type};base64,{encoded}"


def analyze_style_length(style_image_bytes: bytes) -> STYLE_LEVEL:
    """
    Pipeline A: Style Image Analysis
    """
    try:
        model = get_yolo_model()
    except Exception as exc:
        logger.warning("Style length analysis unavailable, falling back to MEDIUM: %s", exc)
        return "MEDIUM"

    try:
        image = Image.open(BytesIO(style_image_bytes)).convert("RGB")
        conf_threshold = getattr(settings, "nail_segmentation_min_confidence", 0.1)
        results = model.predict(source=np.array(image), imgsz=640, conf=conf_threshold, verbose=False)

        if not results or not results[0].boxes:
            # Default to MEDIUM if no nails detected in style ref
            return "MEDIUM"

        boxes = results[0].boxes.xyxy.cpu().numpy()
        aspect_ratios = []

        for box in boxes:
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            if width > 0:
                aspect_ratios.append(height / width)

        if not aspect_ratios:
            return "MEDIUM"

        avg_aspect_ratio = sum(aspect_ratios) / len(aspect_ratios)

        if avg_aspect_ratio < 1.2:
            return "SHORT"
        elif avg_aspect_ratio < 1.6:
            return "MEDIUM"
        else:
            return "LONG"
    except Exception as exc:
        logger.warning("Style length analysis failed, falling back to MEDIUM: %s", exc)
        return "MEDIUM"


def _extract_contours(mask_np: np.ndarray) -> list[dict]:
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    items: list[dict] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 4 or h < 4:
            continue
        items.append(
            {
                "contour": contour,
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h),
                "cx": float(x + w / 2),
                "cy": float(y + h / 2),
                "aspect": float(h / max(w, 1)),
                "area": float(w * h),
            }
        )
    items.sort(key=lambda item: item["cx"])
    return items


def _normalize_fingers(items: list[dict], width: int, height: int) -> list[dict]:
    normalized: list[dict] = []
    for index, item in enumerate(items):
        normalized.append(
            {
                "index": index,
                "x1": item["x"],
                "y1": item["y"],
                "x2": item["x"] + item["w"],
                "y2": item["y"] + item["h"],
                "cx": item["cx"],
                "cy": item["cy"],
                "w": item["w"],
                "h": item["h"],
                "aspect": round(item["aspect"], 4),
                "x1_norm": round(item["x"] / max(width, 1), 5),
                "y1_norm": round(item["y"] / max(height, 1), 5),
                "x2_norm": round((item["x"] + item["w"]) / max(width, 1), 5),
                "y2_norm": round((item["y"] + item["h"]) / max(height, 1), 5),
            }
        )
    return normalized


def _box_aspect(box: dict[str, Any]) -> float:
    width = max(float(box["x2"]) - float(box["x1"]), 1.0)
    height = max(float(box["y2"]) - float(box["y1"]), 1.0)
    return round(height / width, 4)


def _analysis_nails_to_boxes(nails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for item in nails:
        box = item.get("box")
        if not isinstance(box, dict):
            continue
        x = float(box.get("x", 0.0))
        y = float(box.get("y", 0.0))
        w = float(box.get("w", 0.0))
        h = float(box.get("h", 0.0))
        if w <= 0 or h <= 0:
            continue
        boxes.append(
            {
                "x1": round(x, 1),
                "y1": round(y, 1),
                "x2": round(x + w, 1),
                "y2": round(y + h, 1),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
            }
        )
    return boxes


def _build_dynamic_transfer_map(
    user_boxes: list[dict[str, Any]],
    style_boxes: list[dict[str, Any]],
    style_level: STYLE_LEVEL,
) -> list[dict[str, Any]]:
    """
    Build per-finger geometry instructions without sending a mask to the image model.
    Extension is deliberately capped: the model may extend the free edge, but must
    preserve nail-root width and the hand photo's finger anatomy.
    """
    if not user_boxes or not style_boxes:
        return []

    sorted_user = sorted(user_boxes, key=lambda item: (float(item["x1"]) + float(item["x2"])) / 2)
    sorted_style = sorted(style_boxes, key=lambda item: (float(item["x1"]) + float(item["x2"])) / 2)
    style_count = len(sorted_style)
    rules = {
        "SHORT": {"min_aspect": 0.85, "max_aspect": 1.35, "min_scale": 0.92, "max_scale": 1.05},
        "MEDIUM": {"min_aspect": 1.20, "max_aspect": 1.75, "min_scale": 1.03, "max_scale": 1.22},
        "LONG": {"min_aspect": 1.55, "max_aspect": 2.55, "min_scale": 1.12, "max_scale": 1.45},
    }[style_level]

    pairs: list[dict[str, Any]] = []
    for user_index, user_box in enumerate(sorted_user):
        style_index = min(
            style_count - 1,
            round((user_index / max(len(sorted_user) - 1, 1)) * (style_count - 1)),
        )
        style_box = sorted_style[style_index]
        user_aspect = _box_aspect(user_box)
        reference_aspect = _box_aspect(style_box)
        target_aspect = float(np.clip(reference_aspect, rules["min_aspect"], rules["max_aspect"]))
        extension_scale = float(np.clip(target_aspect / max(user_aspect, 0.01), rules["min_scale"], rules["max_scale"]))
        pairs.append(
            {
                "user_index": user_index,
                "style_index": style_index,
                "user_box": {**user_box, "aspect": user_aspect},
                "style_box": {**style_box, "aspect": reference_aspect},
                "target_aspect": round(target_aspect, 4),
                "extension_scale": round(extension_scale, 4),
                "rule": "extend-free-edge-only" if style_level != "SHORT" else "preserve-short-free-edge",
            }
        )
    return pairs


def generate_joint_mask(
    user_image_bytes: bytes,
    style_image_bytes: bytes,
    style_level: STYLE_LEVEL,
) -> tuple[bytes, dict]:
    """
    Pipeline B: Hand Image Segmentation & Dynamic Joint Mask Generation
    """
    model = get_yolo_model()
    image = Image.open(BytesIO(user_image_bytes)).convert("RGB")
    width, height = image.size
    
    conf_threshold = getattr(settings, "nail_segmentation_min_confidence", 0.1)
    results = model.predict(source=np.array(image), imgsz=640, conf=conf_threshold, verbose=False)
    masks = getattr(results[0], "masks", None)
    if not results or masks is None or masks.data is None:
        raise ValueError("未检测到手部或指甲，请重新上传")
        
    # Combine all masks into a single binary image
    mask_data = masks.data.cpu().numpy()
    combined_mask = np.zeros((results[0].masks.data.shape[1], results[0].masks.data.shape[2]), dtype=np.uint8)
    
    for mask_tensor in mask_data:
        mask = (mask_tensor > 0.5).astype(np.uint8) * 255
        combined_mask = np.maximum(combined_mask, mask)
        
    # Resize mask to original image size
    mask_image = Image.fromarray(combined_mask, mode="L").resize((width, height), Image.Resampling.NEAREST)
    base_mask_np = np.array(mask_image)
    
    user_items = _extract_contours(base_mask_np)
    style_items = user_items
    style_width = width
    style_height = height

    # Try style-image nail geometry, fallback to user geometry when style mask is unavailable.
    try:
        style_image = Image.open(BytesIO(style_image_bytes)).convert("RGB")
        style_width, style_height = style_image.size
        style_results = model.predict(source=np.array(style_image), imgsz=640, conf=conf_threshold, verbose=False)
        style_masks = getattr(style_results[0], "masks", None) if style_results else None
        style_mask_data = getattr(style_masks, "data", None)
        if style_mask_data is not None:
            style_h = int(style_mask_data.shape[1])
            style_w = int(style_mask_data.shape[2])
            style_combined = np.zeros((style_h, style_w), dtype=np.uint8)
            for tensor in style_mask_data.cpu().numpy():
                style_combined = np.maximum(style_combined, (tensor > 0.5).astype(np.uint8) * 255)
            style_items = _extract_contours(style_combined) or user_items
    except Exception:
        style_items = user_items

    processed_mask = np.zeros_like(base_mask_np)
    control_pairs: list[dict] = []
    style_count = max(1, len(style_items))
    for user_index, user_item in enumerate(user_items):
        style_index = min(style_count - 1, round((user_index / max(len(user_items) - 1, 1)) * (style_count - 1)))
        style_item = style_items[style_index]
        aspect_ratio_scale = style_item["aspect"] / max(user_item["aspect"], 0.01)
        aspect_ratio_scale = float(np.clip(aspect_ratio_scale, 0.75, 1.9))

        if style_level == "LONG":
            base_scale = 1.35
        elif style_level == "MEDIUM":
            base_scale = 1.05
        else:
            base_scale = 0.9
        final_scale = float(np.clip(base_scale * aspect_ratio_scale, 0.7, 2.2))

        x = user_item["x"]
        y = user_item["y"]
        w = user_item["w"]
        h = user_item["h"]
        extend_h = int(h * max(0.0, final_scale - 1.0))
        dilate_size = max(3, int(min(w, h) * 0.12))
        local = np.zeros_like(base_mask_np)
        cv2.drawContours(local, [user_item["contour"]], -1, 255, -1)
        if extend_h > 0:
            new_y = max(0, y - extend_h)
            cv2.rectangle(local, (x, new_y), (x + w, y), 255, -1)
            center_x = x + w // 2
            axes = (max(1, w // 2), max(1, extend_h))
            cv2.ellipse(local, (center_x, new_y + extend_h), axes, 0, 180, 360, 255, -1)
        kernel = np.ones((dilate_size, dilate_size), np.uint8)
        local = cv2.dilate(local, kernel, iterations=1)
        processed_mask = np.maximum(processed_mask, local)

        control_pairs.append(
            {
                "user_index": user_index,
                "style_index": int(style_index),
                "user_box": {
                    "x1": x,
                    "y1": y,
                    "x2": x + w,
                    "y2": y + h,
                    "w": w,
                    "h": h,
                    "aspect": round(float(user_item["aspect"]), 4),
                },
                "style_box": {
                    "w": int(style_item["w"]),
                    "h": int(style_item["h"]),
                    "aspect": round(float(style_item["aspect"]), 4),
                },
                "scale": round(final_scale, 4),
                "extend_h_px": int(extend_h),
                "dilate_size": int(dilate_size),
            }
        )

    feathered_mask = cv2.GaussianBlur(processed_mask, (5, 5), 0)
    
    out_buffer = BytesIO()
    Image.fromarray(feathered_mask).save(out_buffer, format="PNG")
    control_payload = {
        "style_level": style_level,
        "user_nails": _normalize_fingers(user_items, width, height),
        "style_nails": _normalize_fingers(style_items, style_width, style_height),
        "pairing": control_pairs,
        "image_size": {"width": width, "height": height},
    }
    return out_buffer.getvalue(), control_payload


async def execute_commercial_try_on(
    user_image_bytes: bytes,
    style_image_bytes: bytes,
    style: NailStyle,
    generation_mode: str = "hd",
) -> tuple[str, str, dict]:
    """
    GPT image2 commercial try-on path.

    Mask-free try-on path: use hand-vision geometry analysis + style reference image
    to build strict edit instructions for the image model.
    """
    pipeline_started = perf_counter()
    step_started = pipeline_started
    yolo_style_level = analyze_style_length(style_image_bytes)
    timings_ms = {"style_length_analysis": round((perf_counter() - step_started) * 1000, 1)}

    step_started = perf_counter()
    user_seg = await segment_nails(user_image_bytes)
    timings_ms["hand_nail_detection"] = round((perf_counter() - step_started) * 1000, 1)

    step_started = perf_counter()
    style_seg = await segment_nails(style_image_bytes)
    timings_ms["style_nail_detection"] = round((perf_counter() - step_started) * 1000, 1)

    step_started = perf_counter()
    hand_analysis = await analyze_hand_image_geometry(user_image_bytes)
    timings_ms["qwen_vl_grounding"] = round((perf_counter() - step_started) * 1000, 1)

    step_started = perf_counter()
    style_analysis = await analyze_nail_style_geometry(style_image_bytes)
    timings_ms["qwen_vl_style_analysis"] = round((perf_counter() - step_started) * 1000, 1)

    style_level = style_analysis.get("style_level") or yolo_style_level
    qwen_user_boxes = _analysis_nails_to_boxes(hand_analysis.get("nails", []))
    qwen_style_boxes = _analysis_nails_to_boxes(style_analysis.get("nails", []))
    user_boxes = qwen_user_boxes or user_seg.boxes
    style_boxes = qwen_style_boxes or style_seg.boxes
    dynamic_pairs = _build_dynamic_transfer_map(user_boxes, style_boxes, style_level)
    control_payload = {
        "style_level": style_level,
        "style_level_source": (
            "qwen3-vl-style-analysis" if style_analysis.get("style_level") else "yolo-style-aspect-fallback"
        ),
        "image_size": hand_analysis.get("image_size", {}),
        "user_nails": user_boxes,
        "user_nails_source": (
            "qwen3-vl-grounding" if qwen_user_boxes else "yolo-nail-segmentation-fallback"
        ),
        "style_nails": style_boxes,
        "style_nails_source": (
            "qwen3-vl-style-analysis" if qwen_style_boxes else "yolo-nail-segmentation-fallback"
        ),
        "pairing": dynamic_pairs,
        "length_control": {
            "detected_style_level": style_level,
            "transfer_mode": "free-edge-extension-only",
            "preserve_root_width": True,
            "preserve_finger_anatomy": True,
            "pairs": dynamic_pairs,
        },
        "style_analysis": style_analysis,
        "timings_ms": timings_ms,
    }

    result_image, channel, payload = await generate_try_on(
        user_image_bytes,
        style,
        style_image_bytes,
        None,
        control_payload=control_payload,
        hand_analysis=hand_analysis,
        generation_mode=generation_mode,
    )
    # Normalize provider output URL (external URL / data URL) into local static file
    # so the frontend can always load the result reliably.
    result_image = await _persist_tryon_result_image(result_image)
    timings_ms["total_pipeline"] = round((perf_counter() - pipeline_started) * 1000, 1)
    payload["pipeline"] = {
        "generation_mode": generation_mode,
        "style_level": style_level,
        "mask_guided": False,
        "mask_source": "disabled",
        "pixel_control": control_payload,
        "hand_analysis": hand_analysis,
        "style_analysis": style_analysis,
        "timings_ms": timings_ms,
    }
    return result_image, channel, payload


async def _persist_tryon_result_image(result_image_url: str) -> str:
    out_dir = Path("generated/tryon-results")
    out_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid4().hex

    if result_image_url.startswith("data:image/"):
        header, b64_data = result_image_url.split(",", 1)
        suffix = ".png" if "png" in header else ".jpg"
        raw = base64.b64decode(b64_data)
        file_path = out_dir / f"{file_id}{suffix}"
        file_path.write_bytes(raw)
        return f"/generated/tryon-results/{file_path.name}"

    if result_image_url.startswith("http://") or result_image_url.startswith("https://"):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(result_image_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "png" in content_type:
                suffix = ".png"
            elif "webp" in content_type:
                suffix = ".webp"
            else:
                suffix = ".jpg"
            file_path = out_dir / f"{file_id}{suffix}"
            file_path.write_bytes(response.content)
            return f"/generated/tryon-results/{file_path.name}"

    return result_image_url
