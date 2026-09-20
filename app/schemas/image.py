from typing import Any, Literal

from pydantic import BaseModel, Field


class PageDescriptor(BaseModel):
    page_id: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageSourceMetadata(BaseModel):
    type: Literal["upload", "minio"]
    url: str | None = None
    bucket: str | None = None
    object_key: str | None = None
    etag: str | None = None


class ImageMetadata(BaseModel):
    filename: str
    mime_type: str | None = None
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    processed_width: int = Field(gt=0)
    processed_height: int = Field(gt=0)
    source_coordinate_space: str = "exif_corrected_source_pixels"
    source: ImageSourceMetadata | None = None


class TransformMetadata(BaseModel):
    exif_orientation_applied: bool = False
    scale_x: float = Field(gt=0)
    scale_y: float = Field(gt=0)
    model_input_color_space: str = "RGB"
    notes: list[str] = Field(default_factory=list)
