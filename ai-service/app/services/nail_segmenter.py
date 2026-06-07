import base64
import os
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import settings


@dataclass
class NailSegmentationResult:
    available: bool
    nail_count: int = 0
    confidence: float = 0.0
    mask_image_url: str | None = None
    message: str = "not-run"
    boxes: list[dict[str, float]] = field(default_factory=list)


_MODEL: Any | None = None
_MODEL_ERROR: str | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_path() -> Path:
    path = Path(settings.nail_segmentation_model_path)
    if path.is_absolute():
        return path
    return _project_root() / path


def _load_model() -> Any:
    global _MODEL, _MODEL_ERROR
    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERROR:
        raise RuntimeError(_MODEL_ERROR)

    try:
        from ultralytics import YOLO

        # Compatibility for newer torch defaults (weights_only=True) with legacy YOLO checkpoints.
        os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
        path = _model_path()
        if not path.exists():
            raise FileNotFoundError(f"Nail segmentation model not found: {path}")
        _MODEL = YOLO(str(path))
        return _MODEL
    except Exception as exc:
        _MODEL_ERROR = f"{type(exc).__name__}: {exc}"
        raise RuntimeError(_MODEL_ERROR) from exc


def _encode_mask(mask: Image.Image) -> str:
    buffer = BytesIO()
    mask.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _confidence_values(result: Any) -> list[float]:
    boxes = getattr(result, "boxes", None)
    conf = getattr(boxes, "conf", None)
    if conf is None:
        return []
    return [float(value) for value in conf.detach().cpu().numpy().tolist()]


def _box_values(result: Any, keep_indexes: set[int]) -> list[dict[str, float]]:
    boxes = getattr(result, "boxes", None)
    xyxy = getattr(boxes, "xyxy", None)
    conf = _confidence_values(result)
    if xyxy is None:
        return []

    rows = xyxy.detach().cpu().numpy().tolist()
    payload: list[dict[str, float]] = []
    for index, row in enumerate(rows):
        if index not in keep_indexes:
            continue
        x1, y1, x2, y2 = [float(value) for value in row[:4]]
        payload.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "confidence": conf[index] if index < len(conf) else 0.0,
            }
        )
    return payload


async def segment_nails(image_bytes: bytes) -> NailSegmentationResult:
    if not settings.nail_segmentation_enabled:
        return NailSegmentationResult(available=False, message="disabled")

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        width, height = image.size
        model = _load_model()
        results = model.predict(
            source=np.array(image),
            imgsz=640,
            conf=settings.nail_segmentation_min_confidence,
            verbose=False,
        )
        if not results:
            return NailSegmentationResult(available=True, message="no-result")

        result = results[0]
        conf = _confidence_values(result)
        keep_indexes = {
            index for index, value in enumerate(conf) if value >= settings.nail_segmentation_min_confidence
        }

        masks = getattr(result, "masks", None)
        mask_data = getattr(masks, "data", None)
        if mask_data is None or not keep_indexes:
            return NailSegmentationResult(
                available=True,
                nail_count=0,
                confidence=max(conf, default=0.0),
                message="no-nail-mask",
                boxes=[],
            )

        combined = np.zeros((height, width), dtype=np.uint8)
        for index, tensor in enumerate(mask_data):
            if index not in keep_indexes:
                continue
            mask = tensor.detach().cpu().numpy()
            mask_image = Image.fromarray((mask > 0.5).astype(np.uint8) * 255, mode="L")
            if mask_image.size != (width, height):
                mask_image = mask_image.resize((width, height), Image.Resampling.NEAREST)
            combined = np.maximum(combined, np.array(mask_image, dtype=np.uint8))

        mask_image = Image.fromarray(combined, mode="L")
        kept_conf = [conf[index] for index in keep_indexes if index < len(conf)]
        return NailSegmentationResult(
            available=True,
            nail_count=len(keep_indexes),
            confidence=max(kept_conf, default=0.0),
            mask_image_url=_encode_mask(mask_image),
            message="nail-segmentation-pass" if keep_indexes else "no-nails-detected",
            boxes=_box_values(result, keep_indexes),
        )
    except Exception as exc:
        return NailSegmentationResult(
            available=False,
            message=f"nail-segmentation-unavailable: {type(exc).__name__}: {str(exc)[:180]}",
        )
