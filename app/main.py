from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import get_settings

settings = get_settings()

TAGS_METADATA = [
    {
        "name": "OCR",
        "description": "Production OCR pipeline. Accepts a validated MinIO image URL and returns canonical paragraph objects.",
    },
    {
        "name": "Figure / Table",
        "description": "Production PP-DocLayout pipeline for canonical figure and table regions from a MinIO image URL.",
    },
    {
        "name": "Stamp / Signature",
        "description": "Production RF-DETR pipeline for canonical stamp and signature regions from a MinIO image URL.",
    },
    {
        "name": "Full Extraction",
        "description": "Local/E2E workflows that run all three model pipelines for uploaded pages or MinIO URLs.",
    },
    {
        "name": "MinIO / Dev Storage",
        "description": "MinIO connectivity, object listing, and preview endpoints used by the local inspection UI.",
    },
    {"name": "Health", "description": "Process and configuration liveness."},
]

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Wiki Hami Extraction V1. Product integrations call the independent OCR, Figure/Table, "
        "and Stamp/Signature APIs with a MinIO object URL. Local development can still upload "
        "images through /extract or exercise the same MinIO acquisition path through /extract/minio. "
        "All detections are returned in EXIF-corrected source-image pixel coordinates."
    ),
    openapi_tags=TAGS_METADATA,
)
app.include_router(v1_router, prefix=settings.api_prefix)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "minio_health": f"{settings.api_prefix}/storage/minio/health",
    }
