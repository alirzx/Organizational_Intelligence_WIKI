from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st

from ui.artifacts import build_run_zip, canonical_json_bytes
from ui.visualizer import annotate_page, legend_html, open_source_image


API_BASE = os.getenv("WIKI_HAMI_API_BASE", "http://localhost:8000/api/v1").rstrip("/")
REQUEST_TIMEOUT = 300

st.set_page_config(
    page_title="Wiki Hami · Extraction Inspector",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    .wiki-card {border:1px solid rgba(128,128,128,.25);border-radius:.8rem;padding:.8rem 1rem;margin-bottom:.8rem;}
    .muted {opacity:.72;font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, **kwargs):
    return requests.get(f"{API_BASE}{path}", timeout=30, **kwargs)


def api_post(path: str, **kwargs):
    return requests.post(f"{API_BASE}{path}", timeout=REQUEST_TIMEOUT, **kwargs)


def parse_metadata(raw: str, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def safe_response(response: requests.Response) -> dict:
    if response.ok:
        return response.json()
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise RuntimeError(f"API {response.status_code}: {detail}")


def minio_health() -> tuple[bool, dict | None, str | None]:
    try:
        response = api_get("/storage/minio/health")
        if response.ok:
            body = response.json()
            return bool(body.get("connected")), body, None
        return False, None, response.text
    except requests.RequestException as exc:
        return False, None, str(exc)


def fetch_minio_source(object_key: str) -> bytes:
    response = api_get("/storage/minio/object", params={"object_key": object_key})
    if not response.ok:
        raise RuntimeError(f"Could not load MinIO source {object_key}: {response.text}")
    return response.content


def store_run(result: dict, sources: list[dict[str, Any]]) -> None:
    st.session_state["extraction_run"] = {"result": result, "sources": sources}


with st.sidebar:
    st.title("Wiki Hami")
    st.caption("Extraction V1 · engineering inspector")
    st.markdown("**API**")
    st.code(API_BASE, language=None)
    try:
        health_response = api_get("/health")
        if health_response.ok:
            health = health_response.json()
            st.success("API connected")
            modules = health.get("modules", {})
            st.caption(
                " · ".join(
                    f"{name}: {cfg.get('backend', '?')}" for name, cfg in modules.items()
                )
            )
        else:
            st.error(f"API health: {health_response.status_code}")
    except requests.RequestException as exc:
        st.error(f"API unavailable: {exc}")
    st.divider()
    st.caption("Product APIs consume MinIO URLs. Local upload remains available only through the full-extraction development workflow.")

st.title("Document Extraction Inspector")
st.caption(
    "Inspect the same preprocessing and three CPU model pipelines used by the product. "
    "Choose local upload or authenticated MinIO acquisition, then review overlays, ordered detections, statuses and canonical JSON."
)

input_tab, result_tab, api_tab = st.tabs(["Input & Run", "Results", "Integration"])

with input_tab:
    identity_left, identity_right = st.columns([1, 1.6])
    with identity_left:
        document_id = st.text_input("Document ID", value="doc_demo_001")
    with identity_right:
        document_metadata = st.text_area(
            "Document metadata JSON",
            value='{"source_type":"scanned_document","language_hint":["fa","en"]}',
            height=90,
        )

    source_mode = st.radio(
        "Image source",
        ["Local upload", "MinIO"],
        horizontal=True,
        help="Both paths converge on the same validation, preprocessing, model services and canonical response.",
    )

    if source_mode == "Local upload":
        st.subheader("Upload pages")
        files = st.file_uploader(
            "Choose one or more page images from the same logical document",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            help="Upload order becomes page_number 1..N.",
        )
        if files:
            st.caption(f"{len(files)} page(s) selected")
            preview_columns = st.columns(min(4, len(files)))
            for index, uploaded in enumerate(files[:4]):
                with preview_columns[index % len(preview_columns)]:
                    st.image(uploaded.getvalue(), caption=f"{index + 1}. {uploaded.name}", use_container_width=True)

        if st.button("Run full extraction", type="primary", disabled=not files, key="run_upload"):
            try:
                metadata_obj = parse_metadata(document_metadata, "Document metadata")
                uploads = [
                    {"name": item.name, "type": item.type, "data": item.getvalue()}
                    for item in files
                ]
                descriptors = [
                    {
                        "page_number": index,
                        "filename": item["name"],
                        "metadata": {"source": "streamlit_upload", "upload_index": index - 1},
                    }
                    for index, item in enumerate(uploads, start=1)
                ]
                multipart = [
                    (
                        "images",
                        (item["name"], item["data"], item["type"] or "application/octet-stream"),
                    )
                    for item in uploads
                ]
                form = {
                    "document_id": document_id.strip(),
                    "document_metadata_json": json.dumps(metadata_obj, ensure_ascii=False),
                    "pages_metadata_json": json.dumps(descriptors, ensure_ascii=False),
                }
                with st.spinner("Running OCR, layout and stamp/signature pipelines..."):
                    result = safe_response(api_post("/extract", files=multipart, data=form))
                store_run(
                    result,
                    [
                        {"kind": "upload", "name": item["name"], "data": item["data"]}
                        for item in uploads
                    ],
                )
                st.success("Extraction complete. Open the Results tab.")
            except (ValueError, RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))

    else:
        connected, storage_health, storage_error = minio_health()
        status_col, endpoint_col, bucket_col = st.columns([1, 2, 1.5])
        status_col.metric("MinIO", "Connected" if connected else "Unavailable")
        endpoint_col.metric("Client endpoint", (storage_health or {}).get("endpoint", "—"))
        bucket_col.metric("Bucket", (storage_health or {}).get("bucket", "—"))
        if storage_error:
            st.error(storage_error)

        prefix = st.text_input("Object prefix / folder", value="", placeholder="documents/2026/")
        refresh = st.button("Refresh object list", disabled=not connected)
        if connected and (refresh or "minio_objects" not in st.session_state):
            try:
                response = api_get("/storage/minio/objects", params={"prefix": prefix, "limit": 500})
                body = safe_response(response)
                st.session_state["minio_objects"] = body.get("objects", [])
                st.session_state["minio_prefix"] = prefix
            except (RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))

        objects = st.session_state.get("minio_objects", []) if connected else []
        image_objects = [
            obj for obj in objects
            if obj.get("object_key", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
        if connected:
            st.caption(f"{len(image_objects)} image object(s) available in the current listing")
        selected_keys = st.multiselect(
            "Select document pages",
            options=[obj["object_key"] for obj in image_objects],
            format_func=lambda key: key,
            disabled=not connected,
        )
        selected = [obj for obj in image_objects if obj["object_key"] in selected_keys]

        if selected:
            st.markdown("#### Selected source objects")
            st.dataframe(
                [
                    {
                        "order": index,
                        "object_key": item["object_key"],
                        "size_bytes": item.get("size"),
                        "etag": item.get("etag"),
                        "last_modified": item.get("last_modified"),
                    }
                    for index, item in enumerate(selected, start=1)
                ],
                hide_index=True,
                use_container_width=True,
            )
            preview_key = st.selectbox("Preview source", selected_keys)
            if preview_key:
                try:
                    st.image(fetch_minio_source(preview_key), caption=preview_key, use_container_width=True)
                except (RuntimeError, requests.RequestException) as exc:
                    st.warning(str(exc))

        if st.button(
            "Run full extraction from MinIO",
            type="primary",
            disabled=not selected,
            key="run_minio",
        ):
            try:
                metadata_obj = parse_metadata(document_metadata, "Document metadata")
                payload = {
                    "document_id": document_id.strip(),
                    "document_metadata": {**metadata_obj, "source": "minio"},
                    "pages": [
                        {
                            "image_url": item["image_url"],
                            "page_number": index,
                            "page_id": f"{document_id.strip()}:p{index}",
                            "filename": item["object_key"].rsplit("/", 1)[-1],
                            "metadata": {"minio_object_key": item["object_key"]},
                        }
                        for index, item in enumerate(selected, start=1)
                    ],
                }
                with st.spinner("Reading MinIO objects and running all three pipelines..."):
                    result = safe_response(api_post("/extract/minio", json=payload))
                source_records = []
                for item in selected:
                    source_records.append(
                        {
                            "kind": "minio",
                            "name": item["object_key"],
                            "object_key": item["object_key"],
                            "data": fetch_minio_source(item["object_key"]),
                        }
                    )
                store_run(result, source_records)
                st.success("Extraction complete. Open the Results tab.")
            except (ValueError, RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))

with result_tab:
    run = st.session_state.get("extraction_run")
    if not run:
        st.info("Run an extraction first. Results are kept in this Streamlit session.")
    else:
        result = run["result"]
        sources = run["sources"]
        pages = result.get("pages", [])
        source_images = [open_source_image(source["data"]) for source in sources]
        annotated_pages = [
            (page, annotate_page(source, page.get("objects", [])))
            for page, source in zip(pages, source_images, strict=True)
        ]

        state = result.get("processing", {}).get("state", "unknown")
        if state == "success":
            st.success("All page/module pipelines completed successfully.")
        elif state == "partial_success":
            st.warning("Extraction completed with partial success. Inspect module status below.")
        else:
            st.error("Extraction failed. Inspect module status and errors below.")

        counts = result.get("object_counts", {})
        metrics = st.columns(5)
        metrics[0].metric("Pages", result.get("page_count", 0))
        metrics[1].metric("Paragraphs", counts.get("paragraph", 0))
        metrics[2].metric("Tables / Figures", counts.get("table", 0) + counts.get("figure", 0))
        metrics[3].metric("Stamps / Signatures", counts.get("stamp", 0) + counts.get("signature", 0))
        metrics[4].metric("Duration", f"{result['processing']['duration_ms'] / 1000:.2f}s")

        export_left, export_right = st.columns(2)
        filename_root = "".join(c if c.isalnum() or c in "._-" else "_" for c in result["document_id"]) or "document"
        export_left.download_button(
            "Download canonical JSON",
            canonical_json_bytes(result),
            file_name=f"{filename_root}_extraction.json",
            mime="application/json",
            use_container_width=True,
        )
        export_right.download_button(
            "Download JSON + annotated pages",
            build_run_zip(result, annotated_pages),
            file_name=f"{filename_root}_extraction.zip",
            mime="application/zip",
            use_container_width=True,
        )

        st.markdown(legend_html(), unsafe_allow_html=True)
        page_index = st.selectbox(
            "Inspect page",
            options=range(len(pages)),
            format_func=lambda index: (
                f"{pages[index]['page_number']}. {pages[index]['image']['filename']} · {pages[index]['page_id']}"
            ),
        )
        page = pages[page_index]
        source = source_images[page_index]
        annotated = annotated_pages[page_index][1]

        original_col, annotated_col = st.columns(2)
        original_col.image(source, caption="EXIF-corrected source", use_container_width=True)
        annotated_col.image(annotated, caption="Canonical detections", use_container_width=True)

        module_rows = []
        for name, status in page.get("modules", {}).items():
            module_rows.append(
                {
                    "pipeline": name,
                    "state": status.get("state"),
                    "duration_ms": round(status.get("duration_ms", 0), 2),
                    "backend": status.get("backend"),
                    "model": status.get("model_id"),
                    "warnings": ", ".join(status.get("warnings") or []),
                    "error": status.get("error"),
                }
            )
        st.markdown("#### Pipeline status")
        st.dataframe(module_rows, hide_index=True, use_container_width=True)

        objects = sorted(
            page.get("objects", []),
            key=lambda obj: (obj.get("bbox", {}).get("y1", 0), obj.get("bbox", {}).get("x1", 0), obj.get("type", "")),
        )
        st.markdown("#### Ordered detections")
        st.dataframe(
            [
                {
                    "#": index,
                    "type": obj.get("type"),
                    "confidence": round(float(obj.get("confidence", 0)), 4),
                    "text": (obj.get("text") or "")[:180],
                    "x1": round(float(obj.get("bbox", {}).get("x1", 0)), 1),
                    "y1": round(float(obj.get("bbox", {}).get("y1", 0)), 1),
                    "x2": round(float(obj.get("bbox", {}).get("x2", 0)), 1),
                    "y2": round(float(obj.get("bbox", {}).get("y2", 0)), 1),
                    "model": obj.get("provenance", {}).get("model_id"),
                }
                for index, obj in enumerate(objects, start=1)
            ],
            hide_index=True,
            use_container_width=True,
        )

        pipeline_tabs = st.tabs(["OCR", "Figures & Tables", "Stamps & Signatures", "Page JSON", "Document JSON"])
        with pipeline_tabs[0]:
            paragraphs = [obj for obj in objects if obj.get("type") == "paragraph"]
            for index, obj in enumerate(paragraphs, start=1):
                with st.expander(f"Paragraph {index} · confidence {obj['confidence']:.3f}", expanded=index == 1):
                    st.text(obj.get("text") or "")
                    st.json(obj)
            if not paragraphs:
                st.info("No paragraph objects returned.")
        with pipeline_tabs[1]:
            items = [obj for obj in objects if obj.get("type") in {"figure", "table"}]
            st.json(items)
        with pipeline_tabs[2]:
            items = [obj for obj in objects if obj.get("type") in {"stamp", "signature"}]
            st.json(items)
        with pipeline_tabs[3]:
            st.json(page)
        with pipeline_tabs[4]:
            st.json(result)

with api_tab:
    st.subheader("Product integration")
    st.markdown(
        "The backend calls the three model APIs independently. Each request is JSON and carries one MinIO image URL; Wiki Hami validates that URL and reads the object with its own MinIO credentials."
    )
    st.code(
        '''POST /api/v1/ocr\nPOST /api/v1/figure-table\nPOST /api/v1/stamp-signature\n\n{\n  "document_id": "DOC-100",\n  "image_url": "http://<minio-public-host>:<port>/wiki-documents/path/page-001.jpg",\n  "page_number": 1,\n  "page_id": "DOC-100:p1",\n  "page_metadata": {}\n}''',
        language="json",
    )
    st.markdown("For exact schemas, examples and error responses use the FastAPI Swagger UI at `/docs`.")
