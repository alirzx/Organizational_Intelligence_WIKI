from io import BytesIO

import numpy as np
from PIL import Image

from app.core.config import Settings
from app.modules.figure_table.adapter import layout_items_to_detected_objects
from app.modules.figure_table.types import LayoutDetectionItem
from app.modules.ocr.paragraph_grouper import group_lines_into_paragraphs
from app.modules.ocr.types import OCRLine
from app.modules.stamp_signature.adapter import mark_items_to_detected_objects
from app.modules.stamp_signature.rfdetr_backend import RFDETRStampSignatureBackend
from app.modules.stamp_signature.types import MarkDetection
from app.preprocessing.pipeline import prepare_page
from app.schemas.common import BBox
from app.schemas.detection import ObjectType


def _prepared_page():
    image = Image.new("RGB", (1000, 1400), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return prepare_page(
        data=buffer.getvalue(),
        filename="page.png",
        mime_type="image/png",
        document_id="doc1",
        page_id="doc1:p1",
        page_number=1,
        page_metadata={},
        settings=Settings(preprocess_max_long_edge=1000),
    )


def test_paragraph_grouper_splits_distant_text_blocks():
    lines = [
        OCRLine("line one", 0.9, BBox(x1=100, y1=100, x2=800, y2=140)),
        OCRLine("line two", 0.8, BBox(x1=100, y1=150, x2=790, y2=190)),
        OCRLine("new paragraph", 0.95, BBox(x1=100, y1=400, x2=850, y2=440)),
    ]
    paragraphs = group_lines_into_paragraphs(lines, max_gap_ratio=1.8, min_x_overlap=0.15)
    assert len(paragraphs) == 2
    assert paragraphs[0].text == "line one\nline two"
    assert paragraphs[1].text == "new paragraph"


def test_layout_adapter_keeps_only_figure_and_table_classes():
    page = _prepared_page()
    settings = Settings(figure_table_backend="pp_doclayout")
    items = [
        LayoutDetectionItem("table", 0.9, BBox(x1=10, y1=20, x2=200, y2=300)),
        LayoutDetectionItem("image", 0.8, BBox(x1=300, y1=100, x2=600, y2=500)),
        LayoutDetectionItem("figure_title", 0.99, BBox(x1=300, y1=50, x2=600, y2=90)),
    ]
    objects = layout_items_to_detected_objects(
        items, page=page, settings=settings, backend_name="pp_doclayout"
    )
    assert [obj.type for obj in objects] == [ObjectType.TABLE, ObjectType.FIGURE]


def test_mark_adapter_keeps_stamp_and_signature_only():
    page = _prepared_page()
    settings = Settings(stamp_signature_backend="rfdetr")
    items = [
        MarkDetection("stamp", 0.9, BBox(x1=10, y1=20, x2=200, y2=300), 0),
        MarkDetection("signature", 0.85, BBox(x1=300, y1=100, x2=600, y2=500), 1),
        MarkDetection("checkbox_checked", 0.99, BBox(x1=20, y1=20, x2=40, y2=40), 2),
    ]
    objects = mark_items_to_detected_objects(
        items, page=page, settings=settings, backend_name="rfdetr"
    )
    assert [obj.type for obj in objects] == [ObjectType.STAMP, ObjectType.SIGNATURE]


def test_rfdetr_current_supervision_output_parser_filters_checkboxes():
    class FakeDetections:
        xyxy = np.array([[1, 2, 30, 40], [5, 6, 20, 30], [9, 9, 12, 12]], dtype=float)
        confidence = np.array([0.9, 0.8, 0.99], dtype=float)
        class_id = np.array([0, 1, 2], dtype=int)
        data = {"class_name": np.array(["stamp", "signature", "checkbox_checked"], dtype=object)}

    parsed = RFDETRStampSignatureBackend._from_supervision_detections(FakeDetections())
    assert [item.label for item in parsed] == ["stamp", "signature"]
