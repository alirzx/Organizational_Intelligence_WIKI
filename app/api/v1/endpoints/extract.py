from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.v1.request_parsing import (
    parse_json_object,
    parse_page_descriptors,
    prepare_minio_page,
    prepare_uploaded_page,
)
from app.core.config import get_settings
from app.core.runtime import get_extraction_orchestrator, get_minio_storage_service
from app.schemas.extraction import DocumentExtractionResponse
from app.schemas.image import PageDescriptor
from app.schemas.storage import MinioDocumentRequest
from app.utils.ids import new_request_id

router = APIRouter(tags=["Full Extraction"])
settings = get_settings()
orchestrator = get_extraction_orchestrator()
storage = get_minio_storage_service()


@router.post(
    "/extract",
    response_model=DocumentExtractionResponse,
    summary="Run full extraction for uploaded local images",
    description=(
        "Local/development multipart workflow. Upload one or more page images and run OCR, "
        "figure/table, and stamp/signature pipelines through the shared in-process orchestrator. "
        "Production backend integration uses the three independent MinIO-URL module APIs."
    ),
)
async def extract_document(
    images: list[UploadFile] = File(..., description="1..N page images in document order."),
    document_id: str = Form(...),
    document_metadata_json: str | None = Form(None),
    pages_metadata_json: str | None = Form(None),
):
    if not images:
        raise HTTPException(status_code=422, detail="at least one image is required")
    if len(images) > settings.max_pages_per_document:
        raise HTTPException(
            status_code=422,
            detail=f"document exceeds max_pages_per_document={settings.max_pages_per_document}",
        )

    request_id = new_request_id()
    document_metadata = parse_json_object(document_metadata_json, "document_metadata_json")
    descriptors = parse_page_descriptors(pages_metadata_json, len(images))

    pages = []
    for index, (upload, descriptor) in enumerate(zip(images, descriptors, strict=True), start=1):
        pages.append(
            await prepare_uploaded_page(
                upload=upload,
                document_id=document_id,
                descriptor=descriptor,
                fallback_page_number=index,
                settings=settings,
            )
        )

    return await orchestrator.extract_document(
        document_id=document_id,
        pages=pages,
        request_id=request_id,
        document_metadata=document_metadata,
    )


@router.post(
    "/extract/minio",
    response_model=DocumentExtractionResponse,
    summary="Run full extraction for one or more MinIO image URLs",
    description=(
        "Local E2E/evaluation equivalent of the product MinIO flow. Each URL is validated "
        "against the configured MinIO public base URL and bucket, fetched through the authenticated "
        "MinIO client, prepared once, then passed to all three model services."
    ),
    responses={
        404: {"description": "A referenced MinIO object was not found"},
        422: {"description": "Invalid request, MinIO URL, or image"},
        502: {"description": "MinIO read/connectivity failure"},
        503: {"description": "MinIO integration disabled or misconfigured"},
    },
)
async def extract_minio_document(payload: MinioDocumentRequest):
    if len(payload.pages) > settings.max_pages_per_document:
        raise HTTPException(
            status_code=422,
            detail=f"document exceeds max_pages_per_document={settings.max_pages_per_document}",
        )

    request_id = new_request_id()
    pages = []
    for index, item in enumerate(payload.pages, start=1):
        descriptor = PageDescriptor(
            page_id=item.page_id,
            page_number=item.page_number,
            filename=item.filename,
            metadata=item.metadata,
        )
        pages.append(
            await prepare_minio_page(
                image_url=item.image_url,
                document_id=payload.document_id,
                descriptor=descriptor,
                fallback_page_number=index,
                settings=settings,
                storage=storage,
            )
        )

    return await orchestrator.extract_document(
        document_id=payload.document_id,
        pages=pages,
        request_id=request_id,
        document_metadata=payload.document_metadata,
    )
