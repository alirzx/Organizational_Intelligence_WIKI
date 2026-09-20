from fastapi import APIRouter

from app.api.v1.request_parsing import prepare_minio_page
from app.core.config import get_settings
from app.core.runtime import get_minio_storage_service, get_ocr_service
from app.schemas.extraction import ModulePageResponse
from app.schemas.image import PageDescriptor
from app.schemas.storage import ModuleImageRequest
from app.utils.ids import default_page_id, new_request_id

router = APIRouter(tags=["OCR"])
settings = get_settings()
service = get_ocr_service()
storage = get_minio_storage_service()


@router.post(
    "/ocr",
    response_model=ModulePageResponse,
    summary="Run OCR for one MinIO image",
    description=(
        "Production OCR endpoint. Send the MinIO object URL supplied by the backend. "
        "Wiki Hami validates the configured public MinIO host/bucket, retrieves the object "
        "through its authenticated MinIO client, performs shared image preprocessing, then "
        "runs PaddleOCR and paragraph grouping. The URL is never fetched as an arbitrary HTTP URL."
    ),
    responses={
        404: {"description": "MinIO object not found"},
        422: {"description": "Invalid MinIO URL, request, or image"},
        502: {"description": "MinIO read/connectivity failure"},
        503: {"description": "MinIO integration disabled or misconfigured"},
    },
)
async def run_ocr(payload: ModuleImageRequest):
    request_id = new_request_id()
    descriptor = PageDescriptor(
        page_id=payload.page_id or default_page_id(payload.document_id, payload.page_number),
        page_number=payload.page_number,
        metadata=payload.page_metadata,
    )
    page = await prepare_minio_page(
        image_url=payload.image_url,
        document_id=payload.document_id,
        descriptor=descriptor,
        fallback_page_number=payload.page_number,
        settings=settings,
        storage=storage,
    )
    return await service.run(page, request_id)
