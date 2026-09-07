from fastapi import APIRouter, File, Form, UploadFile

from app.api.v1.request_parsing import parse_json_object, prepare_uploaded_page
from app.core.config import get_settings
from app.core.runtime import get_ocr_service
from app.schemas.extraction import ModulePageResponse
from app.schemas.image import PageDescriptor
from app.utils.ids import default_page_id, new_request_id

router = APIRouter(tags=["ocr"])
settings = get_settings()
service = get_ocr_service()


@router.post("/ocr", response_model=ModulePageResponse)
async def run_ocr(
    image: UploadFile = File(...),
    document_id: str = Form(...),
    page_number: int = Form(1),
    page_id: str | None = Form(None),
    page_metadata_json: str | None = Form(None),
):
    request_id = new_request_id()
    descriptor = PageDescriptor(
        page_id=page_id or default_page_id(document_id, page_number),
        page_number=page_number,
        metadata=parse_json_object(page_metadata_json, "page_metadata_json"),
    )
    page = await prepare_uploaded_page(
        upload=image,
        document_id=document_id,
        descriptor=descriptor,
        fallback_page_number=page_number,
        settings=settings,
    )
    return await service.run(page, request_id)
