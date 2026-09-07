import pytest

from app.preprocessing.transforms import (
    restore_bbox_to_source,
    restore_polygon_to_source,
    source_bbox_to_processed,
    source_polygon_to_processed,
)
from app.schemas.common import BBox, Point, Polygon
from app.schemas.image import TransformMetadata


def test_bbox_roundtrip_source_processed_source():
    source = BBox(x1=100, y1=200, x2=900, y2=1400)
    transform = TransformMetadata(scale_x=0.5, scale_y=0.5)

    processed = source_bbox_to_processed(source, transform)
    restored = restore_bbox_to_source(processed, transform, 2000, 3000)

    assert restored.x1 == pytest.approx(source.x1)
    assert restored.y1 == pytest.approx(source.y1)
    assert restored.x2 == pytest.approx(source.x2)
    assert restored.y2 == pytest.approx(source.y2)


def test_polygon_roundtrip_source_processed_source():
    source = Polygon(
        points=[Point(x=10, y=20), Point(x=80, y=25), Point(x=75, y=90)]
    )
    transform = TransformMetadata(scale_x=0.25, scale_y=0.5)

    processed = source_polygon_to_processed(source, transform)
    restored = restore_polygon_to_source(processed, transform, 100, 100)

    for actual, expected in zip(restored.points, source.points, strict=True):
        assert actual.x == pytest.approx(expected.x)
        assert actual.y == pytest.approx(expected.y)
