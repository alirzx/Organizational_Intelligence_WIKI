from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.common import BBox, Polygon
from app.schemas.status import ModuleName


class ObjectType(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    STAMP = "stamp"
    SIGNATURE = "signature"


class Provenance(BaseModel):
    module: ModuleName
    backend: str
    model_id: str
    model_version: str | None = None


class DetectedObject(BaseModel):
    object_id: str
    document_id: str
    page_id: str
    page_number: int = Field(ge=1)
    type: ObjectType
    bbox: BBox
    polygon: Polygon | None = None
    confidence: float = Field(ge=0, le=1)
    text: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
