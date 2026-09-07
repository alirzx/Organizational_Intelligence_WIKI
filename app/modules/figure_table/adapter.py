from __future__ import annotations

from app.core.config import Settings
from app.modules.figure_table.types import LayoutDetectionItem
from app.preprocessing.transforms import restore_bbox_to_source, restore_polygon_to_source
from app.preprocessing.types import PreparedPage
from app.schemas.detection import DetectedObject, ObjectType, Provenance
from app.schemas.status import ModuleName
from app.utils.ids import new_object_id


def _map_label(label: str, settings: Settings) -> ObjectType | None:
    normalized = label.strip().lower()
    if normalized in settings.table_label_set or normalized.startswith("table") and "caption" not in normalized:
        return ObjectType.TABLE
    if normalized in settings.figure_label_set:
        return ObjectType.FIGURE
    # Keep aliases conservative: captions/titles remain out of Extraction V1 figure regions.
    if any(token in normalized for token in ("figure", "image", "chart")) and not any(
        token in normalized for token in ("caption", "title")
    ):
        return ObjectType.FIGURE
    return None


def layout_items_to_detected_objects(
    items: list[LayoutDetectionItem],
    *,
    page: PreparedPage,
    settings: Settings,
    backend_name: str,
) -> list[DetectedObject]:
    objects: list[DetectedObject] = []
    for item in items:
        object_type = _map_label(item.label, settings)
        if object_type is None:
            continue
        source_bbox = restore_bbox_to_source(
            item.bbox,
            page.transform,
            page.image_metadata.source_width,
            page.image_metadata.source_height,
        )
        source_polygon = (
            restore_polygon_to_source(
                item.polygon,
                page.transform,
                page.image_metadata.source_width,
                page.image_metadata.source_height,
            )
            if item.polygon
            else None
        )
        objects.append(
            DetectedObject(
                object_id=new_object_id(object_type.value),
                document_id=page.document_id,
                page_id=page.page_id,
                page_number=page.page_number,
                type=object_type,
                bbox=source_bbox,
                polygon=source_polygon,
                confidence=item.confidence,
                metadata={"source_label": item.label, "source_class_id": item.class_id},
                provenance=Provenance(
                    module=ModuleName.FIGURE_TABLE,
                    backend=backend_name,
                    model_id=settings.figure_table_model_id,
                ),
            )
        )
    return objects
