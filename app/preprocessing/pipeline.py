import io

from PIL import Image, ImageOps

from app.core.config import Settings
from app.preprocessing.types import PreparedPage
from app.preprocessing.validator import validate_image_bytes
from app.schemas.image import ImageMetadata, ImageSourceMetadata, TransformMetadata


def _resize_for_models(image: Image.Image, max_long_edge: int) -> Image.Image:
    width, height = image.size
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return image.copy()

    scale = max_long_edge / long_edge
    target = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(target, Image.Resampling.LANCZOS)


def prepare_page(
    *,
    data: bytes,
    filename: str,
    mime_type: str | None,
    document_id: str,
    page_id: str,
    page_number: int,
    page_metadata: dict,
    settings: Settings,
    source: ImageSourceMetadata | None = None,
) -> PreparedPage:
    validate_image_bytes(data, settings)

    with Image.open(io.BytesIO(data)) as opened:
        exif = opened.getexif()
        original_orientation = exif.get(274, 1) if exif else 1
        oriented = ImageOps.exif_transpose(opened)
        source_image = oriented.convert("RGB")

    processed = _resize_for_models(source_image, settings.preprocess_max_long_edge)
    source_width, source_height = source_image.size
    processed_width, processed_height = processed.size

    transform = TransformMetadata(
        exif_orientation_applied=original_orientation not in (None, 1),
        scale_x=processed_width / source_width,
        scale_y=processed_height / source_height,
        notes=[
            "Shared preprocessing performs geometry/color normalization only; "
            "backend-specific tensor normalization belongs inside each model backend."
        ],
    )
    image_metadata = ImageMetadata(
        filename=filename,
        mime_type=mime_type,
        source_width=source_width,
        source_height=source_height,
        processed_width=processed_width,
        processed_height=processed_height,
        source=source,
    )

    return PreparedPage(
        document_id=document_id,
        page_id=page_id,
        page_number=page_number,
        page_metadata=page_metadata,
        source_image=source_image,
        processed_image=processed,
        image_metadata=image_metadata,
        transform=transform,
    )
