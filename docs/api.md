# Extraction V1 API reference

Base prefix: `/api/v1`. Interactive OpenAPI/Swagger documentation is available at `/docs` and contains the same request examples and endpoint descriptions.

## Integration boundaries

Production/backend integrations call the three independent module APIs. Their request body is JSON and references one MinIO object URL:

- `POST /api/v1/ocr`
- `POST /api/v1/figure-table`
- `POST /api/v1/stamp-signature`

Local E2E, Streamlit, demos and evaluation use one of the full-extraction routes:

- `POST /api/v1/extract` for multipart uploads;
- `POST /api/v1/extract/minio` for one or more MinIO URLs.

The full-extraction routes call the same in-process service objects as the production APIs and do not make loopback HTTP calls.

## Product module request

All three production APIs accept `application/json`:

```json
{
  "document_id": "DOC-100",
  "image_url": "http://storage.example:9002/wiki-documents/docs/DOC-100/page-001.jpg",
  "page_number": 1,
  "page_id": "DOC-100:p1",
  "page_metadata": {"source_asset_id": "asset_991"}
}
```

Fields:

| Field | Required | Meaning |
|---|---:|---|
| `document_id` | yes | Logical document identity |
| `image_url` | yes | MinIO object URL; host/port and bucket must match configured policy |
| `page_number` | no | Integer >= 1, default 1 |
| `page_id` | no | Defaults to `<document_id>:p<page_number>` |
| `page_metadata` | no | Arbitrary JSON object used during preparation |

The URL is parsed only to identify the configured object. Wiki Hami reads bytes through its authenticated MinIO SDK client. See [MinIO integration](minio.md).

### OCR

`POST /api/v1/ocr` performs Paddle text detection/recognition plus Wiki Hami paragraph grouping. Successful objects are `type: paragraph`.

### Figure/Table

`POST /api/v1/figure-table` performs PP-DocLayoutV3 localization and exposes only canonical `figure` and `table` objects.

### Stamp/Signature

`POST /api/v1/stamp-signature` performs RF-DETR inference and exposes only canonical `stamp` and `signature` objects. Checkbox classes remain filtered.

## Module response

All three return `ModulePageResponse`:

```json
{
  "schema_version": "wiki-hami.extraction.v1",
  "request_id": "req_example",
  "document_id": "DOC-100",
  "page_id": "DOC-100:p1",
  "page_number": 1,
  "module": "ocr",
  "image": {
    "filename": "page-001.jpg",
    "mime_type": "image/jpeg",
    "source_width": 2480,
    "source_height": 3508,
    "processed_width": 1767,
    "processed_height": 2500,
    "source_coordinate_space": "exif_corrected_source_pixels",
    "source": {
      "type": "minio",
      "url": "http://storage.example:9002/wiki-documents/docs/DOC-100/page-001.jpg",
      "bucket": "wiki-documents",
      "object_key": "docs/DOC-100/page-001.jpg",
      "etag": "..."
    }
  },
  "transform": {
    "exif_orientation_applied": false,
    "scale_x": 0.7125,
    "scale_y": 0.7127,
    "model_input_color_space": "RGB",
    "notes": []
  },
  "objects": [],
  "status": {
    "module": "ocr",
    "state": "success",
    "duration_ms": 842.3,
    "model_id": "PaddlePaddle/arabic_PP-OCRv5_mobile_rec",
    "backend": "paddle",
    "warnings": [],
    "error": null
  }
}
```

An empty detection set is still HTTP 200 / module success with the relevant `no_*_detected` warning.

Acquisition/preparation errors use `404`, `422`, `502`, or `503` as documented in Swagger. Independent model load/inference failures normally return `500`.

## Uploaded full extraction

`POST /api/v1/extract` remains the multipart local/development workflow.

Fields: repeated `images`, `document_id`, optional `document_metadata_json`, optional `pages_metadata_json`. It prepares each uploaded page once and runs all three model services.

## MinIO full extraction

`POST /api/v1/extract/minio` accepts JSON:

```json
{
  "document_id": "DOC-100",
  "document_metadata": {"source": "minio"},
  "pages": [
    {
      "image_url": "http://storage.example:9002/wiki-documents/docs/DOC-100/page-001.jpg",
      "page_number": 1,
      "page_id": "DOC-100:p1",
      "metadata": {}
    },
    {
      "image_url": "http://storage.example:9002/wiki-documents/docs/DOC-100/page-002.jpg",
      "page_number": 2,
      "page_id": "DOC-100:p2",
      "metadata": {}
    }
  ]
}
```

Its output is the existing `DocumentExtractionResponse`: `pages[]`, flattened `objects[]`, all object counts, and document processing status. Once preparation succeeds, module failures are isolated and can produce `partial_success` while preserving other objects.

## Storage/health endpoints

- `GET /api/v1/health`: process/config liveness. It does not contact MinIO or load models.
- `GET /api/v1/storage/minio/health`: verifies configured bucket connectivity.
- `GET /api/v1/storage/minio/objects`: internal/dev object browser when enabled.
- `GET /api/v1/storage/minio/object`: internal/dev object proxy for Streamlit preview when enabled.

## Canonical object

Every `DetectedObject` includes `object_id`, `document_id`, `page_id`, `page_number`, `type`, source-coordinate `bbox`, optional polygon, confidence, optional OCR text/raw text, metadata and model provenance.

Object types are `paragraph`, `table`, `figure`, `stamp`, and `signature`. Public coordinates always use `exif_corrected_source_pixels`.
