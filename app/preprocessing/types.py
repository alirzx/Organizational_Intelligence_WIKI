from dataclasses import dataclass
from PIL import Image

from app.schemas.image import ImageMetadata, TransformMetadata


@dataclass(frozen=True)
class PreparedPage:
    document_id: str
    page_id: str
    page_number: int
    page_metadata: dict
    source_image: Image.Image
    processed_image: Image.Image
    image_metadata: ImageMetadata
    transform: TransformMetadata
