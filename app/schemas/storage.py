from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MODULE_REQUEST_EXAMPLE = {
    "document_id": "DOC-100",
    "image_url": "http://minio.example:9000/wiki-documents/docs/DOC-100/page-001.jpg",
    "page_number": 1,
    "page_id": "DOC-100:p1",
    "page_metadata": {"source_asset_id": "asset_991"},
}


class ModuleImageRequest(BaseModel):
    """Production request for one model pipeline using a MinIO object URL."""

    model_config = ConfigDict(json_schema_extra={"examples": [MODULE_REQUEST_EXAMPLE]})

    document_id: str = Field(min_length=1, description="Logical document identifier.")
    image_url: str = Field(
        min_length=1,
        description=(
            "MinIO/S3 object URL supplied by the backend. Its public host/port and bucket "
            "must match the configured Wiki Hami MinIO policy."
        ),
    )
    page_number: int = Field(default=1, ge=1)
    page_id: str | None = Field(
        default=None,
        description="Defaults to <document_id>:p<page_number> when omitted.",
    )
    page_metadata: dict[str, Any] = Field(default_factory=dict)


class MinioPageRequest(BaseModel):
    image_url: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    page_id: str | None = None
    filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MinioDocumentRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_id": "DOC-100",
                    "document_metadata": {"source": "minio"},
                    "pages": [
                        {
                            "image_url": "http://minio.example:9000/wiki-documents/docs/DOC-100/page-001.jpg",
                            "page_number": 1,
                            "page_id": "DOC-100:p1",
                        },
                        {
                            "image_url": "http://minio.example:9000/wiki-documents/docs/DOC-100/page-002.jpg",
                            "page_number": 2,
                            "page_id": "DOC-100:p2",
                        },
                    ],
                }
            ]
        }
    )

    document_id: str = Field(min_length=1)
    pages: list[MinioPageRequest] = Field(min_length=1)
    document_metadata: dict[str, Any] = Field(default_factory=dict)


class MinioHealthResponse(BaseModel):
    status: Literal["ok", "disabled"]
    enabled: bool
    connected: bool
    endpoint: str
    public_base_url: str
    bucket: str
    browser_enabled: bool


class MinioObjectInfo(BaseModel):
    object_key: str
    image_url: str
    size: int = Field(ge=0)
    etag: str | None = None
    last_modified: datetime | None = None
    content_type: str | None = None


class MinioObjectListResponse(BaseModel):
    bucket: str
    prefix: str
    count: int
    truncated: bool = False
    objects: list[MinioObjectInfo] = Field(default_factory=list)
