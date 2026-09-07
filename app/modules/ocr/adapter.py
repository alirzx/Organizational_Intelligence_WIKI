from __future__ import annotations

from app.core.config import Settings
from app.modules.ocr.paragraph_grouper import group_lines_into_paragraphs
from app.modules.ocr.types import OCRLine
from app.preprocessing.transforms import restore_bbox_to_source, restore_polygon_to_source
from app.preprocessing.types import PreparedPage
from app.schemas.detection import DetectedObject, ObjectType, Provenance
from app.schemas.status import ModuleName
from app.utils.ids import new_object_id


def lines_to_detected_objects(
    lines: list[OCRLine],
    *,
    page: PreparedPage,
    settings: Settings,
    backend_name: str,
) -> list[DetectedObject]:
    paragraphs = group_lines_into_paragraphs(
        lines,
        max_gap_ratio=settings.ocr_paragraph_max_gap_ratio,
        min_x_overlap=settings.ocr_paragraph_min_x_overlap,
    )
    objects: list[DetectedObject] = []
    for paragraph in paragraphs:
        source_bbox = restore_bbox_to_source(
            paragraph.bbox,
            page.transform,
            page.image_metadata.source_width,
            page.image_metadata.source_height,
        )
        source_polygon = restore_polygon_to_source(
            paragraph.polygon,
            page.transform,
            page.image_metadata.source_width,
            page.image_metadata.source_height,
        ) if paragraph.polygon else None
        objects.append(
            DetectedObject(
                object_id=new_object_id("paragraph"),
                document_id=page.document_id,
                page_id=page.page_id,
                page_number=page.page_number,
                type=ObjectType.PARAGRAPH,
                bbox=source_bbox,
                polygon=source_polygon,
                confidence=paragraph.confidence,
                text=paragraph.text,
                raw_text=paragraph.raw_text,
                metadata={
                    "line_count": len(paragraph.lines),
                    "line_confidences": [round(line.confidence, 6) for line in paragraph.lines],
                    "text_detection_model": settings.ocr_text_detection_model_name,
                    "text_recognition_model": settings.ocr_model_id,
                },
                provenance=Provenance(
                    module=ModuleName.OCR,
                    backend=backend_name,
                    model_id=settings.ocr_model_id,
                ),
            )
        )
    return objects
