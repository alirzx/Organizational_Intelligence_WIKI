from enum import StrEnum
from pydantic import BaseModel, Field


class ProcessingState(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class ModuleName(StrEnum):
    OCR = "ocr"
    FIGURE_TABLE = "figure_table"
    STAMP_SIGNATURE = "stamp_signature"


class ModuleStatus(BaseModel):
    module: ModuleName
    state: ProcessingState
    duration_ms: float = Field(ge=0)
    model_id: str | None = None
    backend: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class ProcessingStatus(BaseModel):
    state: ProcessingState
    duration_ms: float = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
