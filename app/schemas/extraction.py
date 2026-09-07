from typing import Any
from pydantic import BaseModel, Field

from app.schemas.detection import DetectedObject, ObjectType
from app.schemas.image import ImageMetadata, TransformMetadata
from app.schemas.status import ModuleName, ModuleStatus, ProcessingStatus


class ModulePageResponse(BaseModel):
    schema_version: str
    request_id: str
    document_id: str
    page_id: str
    page_number: int
    module: ModuleName
    image: ImageMetadata
    transform: TransformMetadata
    objects: list[DetectedObject] = Field(default_factory=list)
    status: ModuleStatus


class PageExtractionResponse(BaseModel):
    schema_version: str
    request_id: str
    document_id: str
    page_id: str
    page_number: int
    page_metadata: dict[str, Any] = Field(default_factory=dict)
    image: ImageMetadata
    transform: TransformMetadata
    objects: list[DetectedObject] = Field(default_factory=list)
    modules: dict[ModuleName, ModuleStatus]
    processing: ProcessingStatus


class DocumentExtractionResponse(BaseModel):
    schema_version: str
    request_id: str
    document_id: str
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    page_count: int
    pages: list[PageExtractionResponse]
    # Flattened document-level view. Every object still carries page provenance.
    objects: list[DetectedObject]
    object_counts: dict[ObjectType, int]
    processing: ProcessingStatus
