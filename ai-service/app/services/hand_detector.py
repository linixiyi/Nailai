from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass
class HandDetectionResult:
    confidence: float
    width: int
    height: int
    message: str


async def detect_hand(image_bytes: bytes) -> HandDetectionResult:
    image = Image.open(BytesIO(image_bytes))
    width, height = image.size
    min_side = min(width, height)
    confidence = 0.86 if min_side >= 512 else 0.72
    return HandDetectionResult(
        confidence=confidence,
        width=width,
        height=height,
        message="mock-mediapipe-pass" if confidence >= 0.8 else "image-too-small-for-confident-detection",
    )
