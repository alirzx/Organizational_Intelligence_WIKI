from dataclasses import dataclass

from app.schemas.common import BBox


@dataclass(frozen=True)
class MarkDetection:
    label: str
    confidence: float
    bbox: BBox
    class_id: int | None = None
