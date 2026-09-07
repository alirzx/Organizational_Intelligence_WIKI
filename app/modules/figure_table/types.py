from dataclasses import dataclass

from app.schemas.common import BBox, Polygon


@dataclass(frozen=True)
class LayoutDetectionItem:
    label: str
    confidence: float
    bbox: BBox
    polygon: Polygon | None = None
    class_id: int | None = None
