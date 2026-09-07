from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "schema_version": settings.schema_version,
        "modules": {
            "ocr": {"backend": settings.ocr_backend, "model_id": settings.ocr_model_id},
            "figure_table": {
                "backend": settings.figure_table_backend,
                "model_id": settings.figure_table_model_id,
            },
            "stamp_signature": {
                "backend": settings.stamp_signature_backend,
                "model_id": settings.stamp_signature_model_id,
            },
        },
    }
