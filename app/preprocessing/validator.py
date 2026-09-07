import io
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings


class ImageValidationError(ValueError):
    pass


def validate_image_bytes(data: bytes, settings: Settings) -> None:
    if not data:
        raise ImageValidationError("empty image upload")
    if len(data) > settings.max_upload_bytes:
        raise ImageValidationError(
            f"image exceeds max_upload_bytes={settings.max_upload_bytes}"
        )

    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise ImageValidationError("invalid image dimensions")
            if width * height > settings.max_image_pixels:
                raise ImageValidationError(
                    f"image exceeds max_image_pixels={settings.max_image_pixels}"
                )
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("corrupted or unsupported image") from exc
