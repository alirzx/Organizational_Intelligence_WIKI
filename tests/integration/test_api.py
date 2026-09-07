import json
from io import BytesIO

import httpx
from PIL import Image

from app.main import app


def image_bytes(size=(1200, 1800)):
    image = Image.new("RGB", size, "white")
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def api_client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


async def test_health():
    async with api_client() as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


async def test_each_module_endpoint_contract():
    async with api_client() as client:
        endpoints = ["ocr", "figure-table", "stamp-signature"]
        for endpoint in endpoints:
            response = await client.post(
                f"/api/v1/{endpoint}",
                files={"image": ("page.png", image_bytes(), "image/png")},
                data={"document_id": "doc_contract", "page_number": "1"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["document_id"] == "doc_contract"
            assert body["page_id"] == "doc_contract:p1"
            assert body["status"]["state"] == "success"
            assert isinstance(body["objects"], list)


async def test_document_extract_merges_multiple_pages_and_keeps_page_provenance():
    files = [
        ("images", ("p1.png", image_bytes(), "image/png")),
        ("images", ("p2.png", image_bytes((1000, 1400)), "image/png")),
    ]
    pages = [
        {"page_id": "doc_42:scan_001", "page_number": 1, "metadata": {"scanner": "A"}},
        {"page_id": "doc_42:scan_002", "page_number": 2, "metadata": {"scanner": "A"}},
    ]
    async with api_client() as client:
        response = await client.post(
            "/api/v1/extract",
            files=files,
            data={
                "document_id": "doc_42",
                "document_metadata_json": json.dumps({"source": "pdf_scan", "source_file_id": "file_900"}),
                "pages_metadata_json": json.dumps(pages),
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["document_id"] == "doc_42"
    assert body["page_count"] == 2
    assert len(body["pages"]) == 2
    assert len(body["objects"]) == sum(len(page["objects"]) for page in body["pages"])
    assert {obj["page_number"] for obj in body["objects"]} == {1, 2}
    assert {obj["page_id"] for obj in body["objects"]} == {"doc_42:scan_001", "doc_42:scan_002"}
    assert body["object_counts"] == {
        "paragraph": 2,
        "table": 2,
        "figure": 2,
        "stamp": 2,
        "signature": 2,
    }
    assert body["processing"]["state"] == "success"


async def test_invalid_page_rejects_document_before_module_execution():
    async with api_client() as client:
        response = await client.post(
            "/api/v1/extract",
            files=[
                ("images", ("valid.png", image_bytes(), "image/png")),
                ("images", ("broken.png", b"not an image", "image/png")),
            ],
            data={"document_id": "doc_invalid"},
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["document_id"] == "doc_invalid"
    assert detail["page_number"] == 2
    assert "corrupted or unsupported image" in detail["error"]
