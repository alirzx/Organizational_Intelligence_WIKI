from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.v1.request_parsing import (
    parse_json_object,
    parse_page_descriptors,
    prepare_uploaded_page,
)
from app.core.config import get_settings
from app.core.runtime import get_extraction_orchestrator
from app.schemas.extraction import DocumentExtractionResponse
from app.utils.ids import new_request_id

router = APIRouter(tags=["extraction"])
settings = get_settings()
orchestrator = get_extraction_orchestrator()


@router.post("/extract", response_model=DocumentExtractionResponse)
async def extract_document(
    images: list[UploadFile] = File(...),
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

    # V1: preprocessing is shared and performed exactly once for each page.
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

    # Modules run in parallel per page; pages run with bounded concurrency.
    return await orchestrator.extract_document(
        document_id=document_id,
        pages=pages,
        request_id=request_id,
        document_metadata=document_metadata,
    )
