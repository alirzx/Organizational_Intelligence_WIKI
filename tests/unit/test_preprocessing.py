from io import BytesIO
from PIL import Image

from app.core.config import Settings
from app.preprocessing.pipeline import prepare_page


def make_png(width=4000, height=2000):
    image = Image.new("RGB", (width, height), "white")
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_preprocessing_resizes_and_keeps_source_dimensions():
    settings = Settings(preprocess_max_long_edge=1000)
    page = prepare_page(
        data=make_png(),
        filename="p1.png",
        mime_type="image/png",
        document_id="doc1",
        page_id="doc1:p1",
        page_number=1,
        page_metadata={},
        settings=settings,
    )

    assert page.image_metadata.source_width == 4000
    assert page.image_metadata.source_height == 2000
    assert page.image_metadata.processed_width == 1000
    assert page.image_metadata.processed_height == 500
    assert page.transform.scale_x == 0.25
    assert page.transform.scale_y == 0.25


def test_preprocessing_applies_exif_orientation_before_source_coordinates():
    image = Image.new("RGB", (40, 20), "white")
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise for display.
    buf = BytesIO()
    image.save(buf, format="JPEG", exif=exif)

    page = prepare_page(
        data=buf.getvalue(),
        filename="rotated.jpg",
        mime_type="image/jpeg",
        document_id="doc1",
        page_id="doc1:p1",
        page_number=1,
        page_metadata={},
        settings=Settings(preprocess_max_long_edge=1000),
    )

    assert page.source_image.size == (20, 40)
    assert page.image_metadata.source_width == 20
    assert page.image_metadata.source_height == 40
    assert page.transform.exif_orientation_applied is True
