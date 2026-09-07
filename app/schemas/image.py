from typing import Any
from pydantic import BaseModel, Field


class PageDescriptor(BaseModel):
    page_id: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageMetadata(BaseModel):
    filename: str
    mime_type: str | None = None
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    processed_width: int = Field(gt=0)
    processed_height: int = Field(gt=0)
    source_coordinate_space: str = "exif_corrected_source_pixels"


class TransformMetadata(BaseModel):
    exif_orientation_applied: bool = False
    scale_x: float = Field(gt=0)
    scale_y: float = Field(gt=0)
    model_input_color_space: str = "RGB"
    notes: list[str] = Field(default_factory=list)
