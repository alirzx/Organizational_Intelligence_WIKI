from __future__ import annotations

from app.core.config import Settings
from app.modules.stamp_signature.types import MarkDetection
from app.preprocessing.transforms import restore_bbox_to_source
from app.preprocessing.types import PreparedPage
from app.schemas.detection import DetectedObject, ObjectType, Provenance
from app.schemas.status import ModuleName
from app.utils.ids import new_object_id


def mark_items_to_detected_objects(
    items: list[MarkDetection],
    *,
    page: PreparedPage,
    settings: Settings,
    backend_name: str,
) -> list[DetectedObject]:
    mapping = {"stamp": ObjectType.STAMP, "signature": ObjectType.SIGNATURE}
    objects: list[DetectedObject] = []
    for item in items:
        object_type = mapping.get(item.label.lower())
        if object_type is None:
            continue
        source_bbox = restore_bbox_to_source(
            item.bbox,
            page.transform,
            page.image_metadata.source_width,
            page.image_metadata.source_height,
        )
        objects.append(
            DetectedObject(
                object_id=new_object_id(object_type.value),
                document_id=page.document_id,
                page_id=page.page_id,
                page_number=page.page_number,
                type=object_type,
                bbox=source_bbox,
                confidence=item.confidence,
                metadata={
                    "source_label": item.label,
                    "source_class_id": item.class_id,
                    "ignored_model_classes": ["checkbox_checked", "checkbox_unchecked"],
                },
                provenance=Provenance(
                    module=ModuleName.STAMP_SIGNATURE,
                    backend=backend_name,
                    model_id=settings.stamp_signature_model_id,
                    model_version=settings.stamp_signature_model_revision,
                ),
            )
        )
    return objects
