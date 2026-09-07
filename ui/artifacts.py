"""In-memory exports for local Extraction V1 evaluation."""

from __future__ import annotations

import json
import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image


def canonical_json_bytes(result: dict) -> bytes:
    return json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")


def image_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _safe_component(value: object, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return sanitized or fallback


def build_run_zip(
    result: dict,
    annotated_pages: list[tuple[dict, Image.Image]],
) -> bytes:
    """Bundle canonical JSON, annotated pages, and a small page manifest."""
    root = _safe_component(result.get("document_id"), "document")
    manifest = {
        "document_id": result.get("document_id"),
        "schema_version": result.get("schema_version"),
        "pages": [],
    }
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{root}/extraction.json", canonical_json_bytes(result))
        for index, (page, image) in enumerate(annotated_pages, start=1):
            page_number = int(page.get("page_number", index))
            basename = f"page_{page_number:04d}_annotated.png"
            # Preserve every page even if a caller supplied duplicate page numbers.
            path = f"{root}/pages/{basename}"
            if path in archive.namelist():
                path = f"{root}/pages/page_{page_number:04d}_{index:04d}_annotated.png"
            archive.writestr(path, image_png_bytes(image))
            manifest["pages"].append(
                {
                    "page_id": page.get("page_id"),
                    "page_number": page_number,
                    "original_filename": (page.get("image") or {}).get("filename"),
                    "annotated_file": path.removeprefix(f"{root}/"),
                }
            )
        archive.writestr(
            f"{root}/manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    return output.getvalue()
