from app.schemas.common import BBox, Point, Polygon
from app.schemas.image import TransformMetadata


def restore_bbox_to_source(
    bbox: BBox,
    transform: TransformMetadata,
    source_width: int,
    source_height: int,
) -> BBox:
    """Map a processed-image bbox back to EXIF-corrected source pixels."""
    x1 = max(0.0, min(source_width, bbox.x1 / transform.scale_x))
    y1 = max(0.0, min(source_height, bbox.y1 / transform.scale_y))
    x2 = max(0.0, min(source_width, bbox.x2 / transform.scale_x))
    y2 = max(0.0, min(source_height, bbox.y2 / transform.scale_y))
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def source_bbox_to_processed(bbox: BBox, transform: TransformMetadata) -> BBox:
    return BBox(
        x1=bbox.x1 * transform.scale_x,
        y1=bbox.y1 * transform.scale_y,
        x2=bbox.x2 * transform.scale_x,
        y2=bbox.y2 * transform.scale_y,
    )


def restore_polygon_to_source(
    polygon: Polygon,
    transform: TransformMetadata,
    source_width: int,
    source_height: int,
) -> Polygon:
    return Polygon(
        points=[
            Point(
                x=max(0.0, min(source_width, point.x / transform.scale_x)),
                y=max(0.0, min(source_height, point.y / transform.scale_y)),
            )
            for point in polygon.points
        ]
    )


def source_polygon_to_processed(polygon: Polygon, transform: TransformMetadata) -> Polygon:
    return Polygon(
        points=[
            Point(x=point.x * transform.scale_x, y=point.y * transform.scale_y)
            for point in polygon.points
        ]
    )
