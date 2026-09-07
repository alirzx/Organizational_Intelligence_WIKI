"""Geometry-based grouping of OCR text lines into V1 paragraph objects.

This is intentionally conservative. It does not attempt semantic section reconstruction;
that belongs to later Wiki Hami stages.
"""

from __future__ import annotations

from statistics import median

from app.modules.ocr.types import OCRLine, OCRParagraph
from app.schemas.common import BBox, Point, Polygon


def _x_overlap_ratio(a: BBox, b: BBox) -> float:
    overlap = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    denom = max(1.0, min(a.width, b.width))
    return overlap / denom


def _union_bbox(lines: list[OCRLine]) -> BBox:
    return BBox(
        x1=min(line.bbox.x1 for line in lines),
        y1=min(line.bbox.y1 for line in lines),
        x2=max(line.bbox.x2 for line in lines),
        y2=max(line.bbox.y2 for line in lines),
    )


def _bbox_polygon(bbox: BBox) -> Polygon:
    return Polygon(
        points=[
            Point(x=bbox.x1, y=bbox.y1),
            Point(x=bbox.x2, y=bbox.y1),
            Point(x=bbox.x2, y=bbox.y2),
            Point(x=bbox.x1, y=bbox.y2),
        ]
    )


def group_lines_into_paragraphs(
    lines: list[OCRLine],
    *,
    max_gap_ratio: float = 1.8,
    min_x_overlap: float = 0.15,
) -> list[OCRParagraph]:
    if not lines:
        return []

    ordered = sorted(lines, key=lambda line: (line.bbox.y1, line.bbox.x1))
    typical_height = max(1.0, median(max(1.0, line.bbox.height) for line in ordered))
    max_gap = typical_height * max_gap_ratio

    groups: list[list[OCRLine]] = []
    current: list[OCRLine] = [ordered[0]]

    for line in ordered[1:]:
        previous = current[-1]
        vertical_gap = line.bbox.y1 - previous.bbox.y2
        same_column = _x_overlap_ratio(_union_bbox(current), line.bbox) >= min_x_overlap
        # Slightly overlapping lines are permitted because OCR polygons are not always axis-aligned.
        if vertical_gap <= max_gap and vertical_gap >= -typical_height and same_column:
            current.append(line)
        else:
            groups.append(current)
            current = [line]
    groups.append(current)

    paragraphs: list[OCRParagraph] = []
    for group in groups:
        bbox = _union_bbox(group)
        raw_text = "\n".join(line.text for line in group)
        # V1 normalization is intentionally minimal. Preserve raw OCR exactly and only trim edges.
        normalized = "\n".join(line.text.strip() for line in group if line.text.strip())
        weighted_area = [max(1.0, line.bbox.width * line.bbox.height) for line in group]
        confidence = sum(line.confidence * area for line, area in zip(group, weighted_area, strict=True)) / sum(weighted_area)
        paragraphs.append(
            OCRParagraph(
                text=normalized,
                raw_text=raw_text,
                confidence=max(0.0, min(1.0, confidence)),
                bbox=bbox,
                polygon=_bbox_polygon(bbox),
                lines=tuple(group),
            )
        )
    return paragraphs
