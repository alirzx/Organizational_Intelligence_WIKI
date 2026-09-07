import json
import os

import requests
import streamlit as st

from ui.artifacts import build_run_zip, canonical_json_bytes
from ui.visualizer import annotate_page, legend_html, open_source_image


API_BASE = os.getenv("WIKI_HAMI_API_BASE", "http://localhost:8000/api/v1").rstrip("/")

st.set_page_config(page_title="Wiki Hami Extraction V1", page_icon="🔎", layout="wide")
st.title("Wiki Hami — Extraction V1")
st.caption(
    "Local end-to-end inspection UI. It calls FastAPI `/extract`; all model and "
    "canonicalization logic remains in the API process."
)

document_id = st.text_input("Document ID", value="doc_demo_001")
document_metadata = st.text_area(
    "Document metadata JSON",
    value='{"source_type": "scanned_document", "language_hint": ["fa", "en"]}',
    height=90,
)
files = st.file_uploader(
    "Upload one or more pages from the same logical document",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    help="Upload order becomes page_number 1..N. The API preserves each filename and upload index.",
)

if st.button("Run full extraction", type="primary", disabled=not files):
    if not document_id.strip():
        st.error("Document ID is required.")
        st.stop()
    try:
        metadata_obj = json.loads(document_metadata or "{}")
        if not isinstance(metadata_obj, dict):
            raise ValueError("the value must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        st.error(f"Invalid document metadata JSON: {exc}")
        st.stop()

    uploads = [
        {"name": uploaded.name, "type": uploaded.type, "data": uploaded.getvalue()}
        for uploaded in files
    ]
    page_descriptors = [
        {
            "page_number": index,
            "filename": uploaded["name"],
            "metadata": {"upload_index": index - 1},
        }
        for index, uploaded in enumerate(uploads, start=1)
    ]
    multipart = [
        (
            "images",
            (
                uploaded["name"],
                uploaded["data"],
                uploaded["type"] or "application/octet-stream",
            ),
        )
        for uploaded in uploads
    ]
    data = {
        "document_id": document_id.strip(),
        "document_metadata_json": json.dumps(metadata_obj, ensure_ascii=False),
        "pages_metadata_json": json.dumps(page_descriptors, ensure_ascii=False),
    }

    try:
        with st.spinner("Running OCR, figure/table, and stamp/signature extraction..."):
            response = requests.post(
                f"{API_BASE}/extract", files=multipart, data=data, timeout=300
            )
        if not response.ok:
            st.error(f"API error {response.status_code}: {response.text}")
            st.stop()
        st.session_state["extraction_run"] = {
            "result": response.json(),
            "uploads": uploads,
        }
    except requests.RequestException as exc:
        st.error(f"Could not call the Extraction API at {API_BASE}: {exc}")
        st.stop()

run = st.session_state.get("extraction_run")
if run:
    result = run["result"]
    uploads = run["uploads"]
    pages = result.get("pages", [])
    source_images = [open_source_image(upload["data"]) for upload in uploads]
    annotated_pages = [
        (page, annotate_page(source, page.get("objects", [])))
        for page, source in zip(pages, source_images, strict=True)
    ]

    state = result["processing"]["state"]
    if state == "success":
        st.success("Extraction completed successfully.")
    elif state == "partial_success":
        st.warning("Extraction completed with partial success. Inspect module errors below.")
    else:
        st.error("Extraction failed. Inspect page and module errors below.")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Document", result["document_id"])
    metric_columns[1].metric("Pages", result["page_count"])
    metric_columns[2].metric("Objects", len(result.get("objects", [])))
    metric_columns[3].metric(
        "Duration", f"{result['processing']['duration_ms'] / 1000:.2f} s"
    )

    st.subheader("Document summary")
    counts = result.get("object_counts", {})
    st.dataframe(
        [{"class": name, "count": count} for name, count in counts.items()],
        hide_index=True,
        use_container_width=True,
    )
    if result["processing"].get("warnings"):
        st.warning(" · ".join(result["processing"]["warnings"]))

    download_left, download_right = st.columns(2)
    document_filename = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in result["document_id"]
    ).strip("._") or "document"
    with download_left:
        st.download_button(
            "Download canonical JSON",
            data=canonical_json_bytes(result),
            file_name=f"{document_filename}_extraction.json",
            mime="application/json",
            use_container_width=True,
        )
    with download_right:
        st.download_button(
            "Download JSON + annotated pages (ZIP)",
            data=build_run_zip(result, annotated_pages),
            file_name=f"{document_filename}_extraction.zip",
            mime="application/zip",
            use_container_width=True,
        )

    st.subheader("Page inspector")
    page_index = st.selectbox(
        "Page",
        options=range(len(pages)),
        format_func=lambda index: (
            f"Page {pages[index]['page_number']} — {pages[index]['page_id']} — "
            f"{pages[index]['image']['filename']}"
        ),
    )
    page = pages[page_index]
    source = source_images[page_index]
    annotated = annotated_pages[page_index][1]

    st.markdown(legend_html(), unsafe_allow_html=True)
    original_column, annotated_column = st.columns(2)
    with original_column:
        st.image(source, caption="Original (EXIF-corrected source)", use_container_width=True)
    with annotated_column:
        st.image(
            annotated,
            caption="All canonical detections in source coordinates",
            use_container_width=True,
        )

    st.markdown(
        f"**Page state:** `{page['processing']['state']}` · "
        f"**Objects:** `{len(page.get('objects', []))}` · "
        f"**Duration:** `{page['processing']['duration_ms']:.1f} ms`"
    )
    if page["processing"].get("warnings"):
        st.warning(" · ".join(page["processing"]["warnings"]))

    module_rows = []
    for name, status in page.get("modules", {}).items():
        module_rows.append(
            {
                "module": name,
                "state": status["state"],
                "duration_ms": round(status["duration_ms"], 2),
                "backend": status.get("backend"),
                "model_id": status.get("model_id"),
                "warnings": ", ".join(status.get("warnings") or []),
                "error": status.get("error"),
            }
        )
    st.markdown("#### Module status")
    st.dataframe(module_rows, hide_index=True, use_container_width=True)

    paragraphs = [
        obj for obj in page.get("objects", []) if obj.get("type") == "paragraph"
    ]
    st.markdown("#### OCR paragraphs")
    if paragraphs:
        for index, paragraph in enumerate(paragraphs, start=1):
            with st.expander(
                f"Paragraph #{index} · confidence {paragraph['confidence']:.2f}",
                expanded=index == 1,
            ):
                st.text(paragraph.get("text") or "")
                if paragraph.get("raw_text") != paragraph.get("text"):
                    st.caption("Raw OCR")
                    st.text(paragraph.get("raw_text") or "")
    else:
        st.info("No OCR paragraphs were returned for this page.")

    with st.expander("Page metadata and transform"):
        st.json(
            {
                "page_metadata": page.get("page_metadata", {}),
                "image": page.get("image", {}),
                "transform": page.get("transform", {}),
            }
        )
    with st.expander("Canonical page objects"):
        st.json(page.get("objects", []))
    with st.expander("Canonical document JSON"):
        st.json(result)
