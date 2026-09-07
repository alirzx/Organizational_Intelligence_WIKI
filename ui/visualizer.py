"""Render canonical Extraction V1 objects in source-image coordinates."""

from __future__ import annotations

from collections import Counter
from io import BytesIO
from typing import Any, Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps


CLASS_COLORS: dict[str, str] = {
    "paragraph": "#2563EB",
    "table": "#7C3AED",
    "figure": "#059669",
    "stamp": "#DC2626",
    "signature": "#EA580C",
}


def open_source_image(data: bytes) -> Image.Image:
    """Decode bytes into the API's EXIF-corrected public coordinate space."""
    with Image.open(BytesIO(data)) as opened:
        return ImageOps.exif_transpose(opened).convert("RGB")


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:  # pragma: no cover - depends on the host font bundle
        return ImageFont.load_default()


def _clamped_points(points: Iterable[dict[str, Any]], width: int, height: int):
    return [
        (
            max(0.0, min(float(width), float(point["x"]))),
            max(0.0, min(float(height), float(point["y"]))),
        )
        for point in points
    ]


def annotate_page(image: Image.Image, objects: list[dict[str, Any]]) -> Image.Image:
    """Draw canonical objects without altering the supplied image.

    Coordinates are consumed directly; callers must supply the EXIF-corrected source
    image corresponding to the API response.
    """
    source = ImageOps.exif_transpose(image).convert("RGB")
    width, height = source.size
    line_width = max(2, round(max(width, height) / 600))
    font_size = max(12, round(max(width, height) / 85))
    font = _font(font_size)

    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")
    indexed: list[tuple[dict[str, Any], str, int]] = []
    counters: Counter[str] = Counter()

    for obj in objects:
        object_type = str(obj.get("type", "unknown"))
        color_hex = CLASS_COLORS.get(object_type, "#475569")
        color = ImageColor.getrgb(color_hex)
        counters[object_type] += 1
        indexed.append((obj, color_hex, counters[object_type]))

        polygon = obj.get("polygon") or {}
        points = _clamped_points(polygon.get("points") or [], width, height)
        if len(points) >= 3:
            overlay_draw.polygon(points, fill=(*color, 30))
            overlay_draw.line(points + [points[0]], fill=(*color, 255), width=line_width)
        else:
            box = obj.get("bbox") or {}
            xy = (
                max(0.0, min(float(width), float(box.get("x1", 0)))),
                max(0.0, min(float(height), float(box.get("y1", 0)))),
                max(0.0, min(float(width), float(box.get("x2", 0)))),
                max(0.0, min(float(height), float(box.get("y2", 0)))),
            )
            overlay_draw.rectangle(xy, fill=(*color, 24), outline=(*color, 255), width=line_width)

    rendered = Image.alpha_composite(source.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(rendered)
    padding = max(3, line_width)

    for obj, color_hex, index in indexed:
        box = obj.get("bbox") or {}
        x = max(0, min(width - 1, round(float(box.get("x1", 0)))))
        y = max(0, min(height - 1, round(float(box.get("y1", 0)))))
        confidence = obj.get("confidence")
        suffix = f" {float(confidence):.2f}" if confidence is not None else ""
        label = f"{obj.get('type', 'object')} #{index}{suffix}"
        text_box = draw.textbbox((0, 0), label, font=font)
        label_width = text_box[2] - text_box[0] + 2 * padding
        label_height = text_box[3] - text_box[1] + 2 * padding
        x = min(x, max(0, width - label_width))
        label_y = y - label_height if y >= label_height else y
        draw.rounded_rectangle(
            (x, label_y, x + label_width, label_y + label_height),
            radius=max(2, padding),
            fill=color_hex,
        )
        draw.text((x + padding, label_y + padding), label, fill="white", font=font)

    return rendered


def legend_html() -> str:
    """Return a compact, stable legend suitable for Streamlit markdown."""
    entries = []
    for object_type, color in CLASS_COLORS.items():
        entries.append(
            f'<span style="white-space:nowrap;margin-right:1rem">'
            f'<span style="display:inline-block;width:.8rem;height:.8rem;'
            f'border-radius:.2rem;background:{color};margin-right:.35rem"></span>'
            f'{object_type.replace("_", " ").title()}</span>'
        )
    return "".join(entries)
