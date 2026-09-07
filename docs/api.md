# Extraction V1 API reference

Base prefix: `/api/v1`. The live OpenAPI UI is `/docs`.

## Which endpoint should a caller use?

Production/backend integrations call the independent module endpoints as needed:

- `POST /api/v1/ocr`
- `POST /api/v1/figure-table`
- `POST /api/v1/stamp-signature`

Local end-to-end tools, Streamlit, demos, and evaluation call `POST /api/v1/extract`. It runs all modules through shared in-process Python services; it does not call the three HTTP endpoints and it does not replace them as the product integration boundary.

All public object geometry uses `exif_corrected_source_pixels`.

## `GET /api/v1/health`

Purpose: report process/configuration health and selected backend/model IDs. The current application has no unprefixed `GET /health`; `/api/v1/health` is the implemented route.

Content type: no request body; response is JSON. This endpoint does not load models, check weight availability, run inference, or prove model readiness.

```bash
curl -sS http://localhost:8000/api/v1/health
```

Success (`200`):

```json
{
  "status": "ok",
  "service": "Wiki Hami Extraction",
  "schema_version": "wiki-hami.extraction.v1",
  "modules": {
    "ocr": {"backend": "paddle", "model_id": "PaddlePaddle/arabic_PP-OCRv5_mobile_rec"},
    "figure_table": {"backend": "pp_doclayout", "model_id": "PaddlePaddle/PP-DocLayoutV3"},
    "stamp_signature": {"backend": "rfdetr", "model_id": "bluecopa/rf-detr-stamp-signature-detector"}
  }
}
```

## Independent module endpoints

All three accept one image and the same identity/metadata fields. They are intended for product/backend calls that need independent capabilities.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `image` | multipart file | yes | One Pillow-decodable image |
| `document_id` | string | yes | Logical document identity |
| `page_number` | integer >= 1 | no | Defaults to `1` |
| `page_id` | string | no | Defaults to `<document_id>:p<page_number>` |
| `page_metadata_json` | JSON-object string | no | Arbitrary page metadata used during preparation; a module response does not echo this field |

Content type: `multipart/form-data`. API format support is whatever the installed Pillow build can decode; filename/MIME are not allow-list validation. PNG, JPEG, and WebP are normal inputs. Each file must be non-empty, at most `max_upload_bytes` (25 MiB default), no more than `max_image_pixels` (50 million default), and fully verifiable by Pillow.

All successful calls return `ModulePageResponse`. An empty detection set is still HTTP `200`/module `success` with a `no_*_detected` warning. Multipart/Pydantic/JSON/image validation errors return `422`. A model import, load, inference, or adapter exception is not caught by these endpoints and normally returns `500`.

### `POST /api/v1/ocr`

Purpose: text detection, recognition, and Wiki Hami geometry-based paragraph grouping. Production OCR consumers should use this endpoint.

Output objects: only `type: "paragraph"`; `text`, `raw_text`, line-count/confidence metadata, OCR model identifiers, source geometry, and provenance are included. Default real backend: PaddleOCR. See [models.md](models.md#ocr--paddleocr).

```bash
curl -sS -X POST http://localhost:8000/api/v1/ocr \
  -F 'image=@scan_0007.png;type=image/png' \
  -F 'document_id=DOC-100' \
  -F 'page_id=DOC-100:p7' \
  -F 'page_number=7' \
  -F 'page_metadata_json={"source_asset_id":"asset_991"}'
```

### `POST /api/v1/figure-table`

Purpose: localize whole figure/table regions. Production layout consumers should use this endpoint.

Output objects: only `figure` and `table`; captions/titles and all unrelated PP-DocLayout labels are filtered. Table structure/cells are not extracted. Default real backend: PP-DocLayoutV3.

```bash
curl -sS -X POST http://localhost:8000/api/v1/figure-table \
  -F 'image=@scan_0007.png;type=image/png' \
  -F 'document_id=DOC-100' -F 'page_number=7'
```

### `POST /api/v1/stamp-signature`

Purpose: localize stamps and signatures. Production mark-detection consumers should use this endpoint.

Output objects: only `stamp` and `signature`. The checkpoint's `checkbox_checked` and `checkbox_unchecked` results are ignored. Signature identity and stamp meaning are out of scope.

```bash
curl -sS -X POST http://localhost:8000/api/v1/stamp-signature \
  -F 'image=@scan_0007.png;type=image/png' \
  -F 'document_id=DOC-100' -F 'page_number=7'
```

Representative module success (`200`):

```json
{
  "schema_version": "wiki-hami.extraction.v1",
  "request_id": "req_d19b8c",
  "document_id": "DOC-100",
  "page_id": "DOC-100:p7",
  "page_number": 7,
  "module": "ocr",
  "image": {
    "filename": "scan_0007.png",
    "mime_type": "image/png",
    "source_width": 2480,
    "source_height": 3508,
    "processed_width": 1767,
    "processed_height": 2500,
    "source_coordinate_space": "exif_corrected_source_pixels"
  },
  "transform": {
    "exif_orientation_applied": false,
    "scale_x": 0.7125,
    "scale_y": 0.7127,
    "model_input_color_space": "RGB",
    "notes": ["Shared preprocessing performs geometry/color normalization only; backend-specific tensor normalization belongs inside each model backend."]
  },
  "objects": [
    {
      "object_id": "paragraph_89f2",
      "document_id": "DOC-100",
      "page_id": "DOC-100:p7",
      "page_number": 7,
      "type": "paragraph",
      "bbox": {"x1": 180.0, "y1": 240.0, "x2": 2260.0, "y2": 610.0},
      "polygon": {"points": [{"x": 180.0, "y": 240.0}, {"x": 2260.0, "y": 240.0}, {"x": 2260.0, "y": 610.0}, {"x": 180.0, "y": 610.0}]},
      "confidence": 0.94,
      "text": "متن شناسایی‌شده",
      "raw_text": "متن شناسایی‌شده",
      "metadata": {"line_count": 1, "line_confidences": [0.94]},
      "provenance": {"module": "ocr", "backend": "paddle", "model_id": "PaddlePaddle/arabic_PP-OCRv5_mobile_rec", "model_version": null}
    }
  ],
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

Representative invalid-image error (`422`):

```json
{
  "detail": {
    "document_id": "DOC-100",
    "page_id": "DOC-100:p7",
    "page_number": 7,
    "error": "corrupted or unsupported image"
  }
}
```

## `POST /api/v1/extract`

Purpose: execute the complete Extraction V1 workflow for one logical document. Used by Streamlit, local development, end-to-end tests, demos, and evaluation.

Content type: `multipart/form-data`.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `document_id` | string | yes | Shared logical document ID |
| `images` | repeated multipart file | yes | 1..`max_pages_per_document` page images (100 default) |
| `document_metadata_json` | JSON-object string | no | Defaults to `{}` and is echoed in the document response |
| `pages_metadata_json` | JSON-array string | no | Exactly one `PageDescriptor` per image; positionally aligned |

`PageDescriptor` fields are `page_id`, `page_number`, `filename`, and `metadata`; all are optional. Missing page numbers become upload position 1..N. Missing IDs become `<document_id>:p<page_number>`. Missing filenames use the uploaded filename. The caller is responsible for unique IDs/numbers. Descriptors and images are paired in multipart order, while returned pages are sorted by page number.

```bash
curl -sS -X POST http://localhost:8000/api/v1/extract \
  -F 'document_id=DOC-100' \
  -F 'document_metadata_json={"source":"scanner-A"}' \
  -F 'pages_metadata_json=[{"page_id":"DOC-100:p1","page_number":1,"filename":"scan_0001.png","metadata":{"asset_id":"a1"}},{"page_id":"DOC-100:p2","page_number":2,"filename":"scan_0002.png","metadata":{"asset_id":"a2"}}]' \
  -F 'images=@scan_0001.png;type=image/png' \
  -F 'images=@scan_0002.png;type=image/png'
```

Success and partial/failed orchestration responses all use HTTP `200` and `DocumentExtractionResponse`; callers must inspect `processing.state` and each page/module status. Successful detections are retained if another module fails. Validation before orchestration is all-or-nothing and returns `422`, not a partial document. The configured timeout is per module call per page.

Abbreviated partial-success response (`200`):

```json
{
  "schema_version": "wiki-hami.extraction.v1",
  "request_id": "req_6212",
  "document_id": "DOC-100",
  "document_metadata": {"source": "scanner-A"},
  "page_count": 1,
  "pages": [{
    "schema_version": "wiki-hami.extraction.v1",
    "request_id": "req_6212",
    "document_id": "DOC-100",
    "page_id": "DOC-100:p1",
    "page_number": 1,
    "page_metadata": {"asset_id": "a1"},
    "image": {"filename": "scan_0001.png", "mime_type": "image/png", "source_width": 2480, "source_height": 3508, "processed_width": 1767, "processed_height": 2500, "source_coordinate_space": "exif_corrected_source_pixels"},
    "transform": {"exif_orientation_applied": false, "scale_x": 0.7125, "scale_y": 0.7127, "model_input_color_space": "RGB", "notes": []},
    "objects": [{
      "object_id": "table_c31a", "document_id": "DOC-100", "page_id": "DOC-100:p1", "page_number": 1,
      "type": "table", "bbox": {"x1": 100, "y1": 900, "x2": 2300, "y2": 1800}, "polygon": null,
      "confidence": 0.91, "text": null, "raw_text": null, "metadata": {},
      "provenance": {"module": "figure_table", "backend": "pp_doclayout", "model_id": "PaddlePaddle/PP-DocLayoutV3", "model_version": null}
    }],
    "modules": {
      "ocr": {"module": "ocr", "state": "success", "duration_ms": 820, "model_id": "PaddlePaddle/arabic_PP-OCRv5_mobile_rec", "backend": "paddle", "warnings": [], "error": null},
      "figure_table": {"module": "figure_table", "state": "success", "duration_ms": 510, "model_id": "PaddlePaddle/PP-DocLayoutV3", "backend": "pp_doclayout", "warnings": [], "error": null},
      "stamp_signature": {"module": "stamp_signature", "state": "failed", "duration_ms": 0, "model_id": null, "backend": null, "warnings": [], "error": "RuntimeError: checkpoint unavailable"}
    },
    "processing": {"state": "partial_success", "duration_ms": 824, "warnings": ["stamp_signature_failed"]}
  }],
  "objects": [{
    "object_id": "table_c31a", "document_id": "DOC-100", "page_id": "DOC-100:p1", "page_number": 1,
    "type": "table", "bbox": {"x1": 100, "y1": 900, "x2": 2300, "y2": 1800}, "polygon": null,
    "confidence": 0.91, "text": null, "raw_text": null, "metadata": {},
    "provenance": {"module": "figure_table", "backend": "pp_doclayout", "model_id": "PaddlePaddle/PP-DocLayoutV3", "model_version": null}
  }],
  "object_counts": {"paragraph": 0, "table": 1, "figure": 0, "stamp": 0, "signature": 0},
  "processing": {"state": "partial_success", "duration_ms": 826, "warnings": ["stamp_signature_failed"]}
}
```

## Canonical schemas

Fields shown without “optional” are required in emitted responses. Pydantic serializes enum values as the strings listed here.

### `Point`

One polygon vertex: `x: float`, `y: float`. The schema itself permits any float; production adapters clamp restored points to image bounds.

```json
{"x": 125.5, "y": 480.0}
```

### `Polygon`

`points: Point[]`, minimum three points. Coordinates use the containing response's public source space.

```json
{"points": [{"x": 10, "y": 20}, {"x": 80, "y": 20}, {"x": 80, "y": 60}, {"x": 10, "y": 60}]}
```

### `BBox`

XYXY pixel box with floats `x1`, `y1`, `x2`, `y2`. Values are non-negative and must satisfy `x2 >= x1`, `y2 >= y1`. Public boxes are clamped to source width/height.

```json
{"x1": 10.0, "y1": 20.0, "x2": 80.0, "y2": 60.0}
```

### Enums

- `ObjectType`: `paragraph`, `table`, `figure`, `stamp`, `signature`
- `ModuleName`: `ocr`, `figure_table`, `stamp_signature`
- `ProcessingState`: `success`, `partial_success`, `failed`

```json
{"object_type": "paragraph", "module": "ocr", "state": "success"}
```

### `Provenance`

`module: ModuleName`, `backend: string`, `model_id: string`, and optional/nullable `model_version: string | null` (default `null`). RF-DETR uses the pinned checkpoint revision as version; current Paddle adapters leave it null.

```json
{"module": "stamp_signature", "backend": "rfdetr", "model_id": "bluecopa/rf-detr-stamp-signature-detector", "model_version": "c59fd4f451b254501700a56c7769f1a3d788c753"}
```

### `DetectedObject`

| Field | Type | Notes |
|---|---|---|
| `object_id` | string | Generated UUID-based ID; not stable across reruns |
| `document_id` | string | Repeated document provenance |
| `page_id` | string | Repeated page provenance |
| `page_number` | integer >= 1 | Repeated page provenance |
| `type` | `ObjectType` | V1 canonical class |
| `bbox` | `BBox` | Required source-coordinate XYXY box |
| `polygon` | `Polygon | null` | Optional; null when backend/adapter does not provide one |
| `confidence` | float 0..1 | Model/derived confidence |
| `text` | `string | null` | Normalized paragraph text; null for non-OCR objects |
| `raw_text` | `string | null` | Minimally altered OCR text when available |
| `metadata` | JSON object | Module-specific details; defaults to `{}` |
| `provenance` | `Provenance` | Module/backend/model lineage |

```json
{"object_id":"signature_abc","document_id":"DOC-100","page_id":"DOC-100:p2","page_number":2,"type":"signature","bbox":{"x1":1200,"y1":2600,"x2":1900,"y2":3000},"polygon":null,"confidence":0.96,"text":null,"raw_text":null,"metadata":{"source_label":"signature","source_class_id":1},"provenance":{"module":"stamp_signature","backend":"rfdetr","model_id":"bluecopa/rf-detr-stamp-signature-detector","model_version":"c59fd4f451b254501700a56c7769f1a3d788c753"}}
```

### `PageDescriptor`

Request-only descriptor: optional `page_id: string | null`, `page_number: integer >= 1 | null`, `filename: string | null`, and `metadata: object` defaulting to `{}`.

```json
{"page_id":"DOC-100:p7","page_number":7,"filename":"scan_0007.png","metadata":{"source_asset_id":"asset_991"}}
```

### `ImageMetadata`

`filename: string`; optional/nullable `mime_type`; positive source and processed dimensions; and `source_coordinate_space`, default/emitted as `exif_corrected_source_pixels`.

```json
{"filename":"scan.png","mime_type":"image/png","source_width":2480,"source_height":3508,"processed_width":1767,"processed_height":2500,"source_coordinate_space":"exif_corrected_source_pixels"}
```

### `TransformMetadata`

`exif_orientation_applied: boolean` (default false); positive `scale_x` and `scale_y`; `model_input_color_space` (default `RGB`); `notes: string[]` (default empty). Scale maps source to the shared processed image; adapters divide to restore coordinates.

```json
{"exif_orientation_applied":true,"scale_x":0.5,"scale_y":0.5,"model_input_color_space":"RGB","notes":["shared geometry normalization"]}
```

### `ModuleStatus`

`module`, `state`, non-negative `duration_ms`, optional/nullable `model_id`, optional/nullable `backend`, `warnings` defaulting to `[]`, and optional/nullable `error`. Current module services emit `success`; orchestrator-generated failures use `failed`. `partial_success` is an allowed enum value although current code does not generate it for an individual module.

```json
{"module":"ocr","state":"success","duration_ms":842.3,"model_id":"PaddlePaddle/arabic_PP-OCRv5_mobile_rec","backend":"paddle","warnings":[],"error":null}
```

### `ProcessingStatus`

Aggregate `state`, non-negative `duration_ms`, and `warnings: string[]` defaulting to empty.

```json
{"state":"partial_success","duration_ms":920.4,"warnings":["stamp_signature_failed"]}
```

### `ModulePageResponse`

Required fields: `schema_version`, `request_id`, document/page identity, `module`, `image`, `transform`, `objects` (default empty), and `status`. A complete example appears under the module endpoints.

```json
{"schema_version":"wiki-hami.extraction.v1","request_id":"req_x","document_id":"DOC-1","page_id":"DOC-1:p1","page_number":1,"module":"figure_table","image":{"filename":"p1.png","mime_type":"image/png","source_width":100,"source_height":200,"processed_width":100,"processed_height":200,"source_coordinate_space":"exif_corrected_source_pixels"},"transform":{"exif_orientation_applied":false,"scale_x":1,"scale_y":1,"model_input_color_space":"RGB","notes":[]},"objects":[],"status":{"module":"figure_table","state":"success","duration_ms":3,"model_id":"PaddlePaddle/PP-DocLayoutV3","backend":"pp_doclayout","warnings":["no_figure_or_table_detected"],"error":null}}
```

### `PageExtractionResponse`

Required fields: schema/request/document/page identity; `page_metadata` default `{}`; `image`; `transform`; merged `objects` default `[]`; `modules`, a map keyed by all three `ModuleName` values; and aggregate `processing`.

```json
{"schema_version":"wiki-hami.extraction.v1","request_id":"req_x","document_id":"DOC-1","page_id":"DOC-1:p1","page_number":1,"page_metadata":{},"image":{"filename":"p1.png","mime_type":"image/png","source_width":100,"source_height":200,"processed_width":100,"processed_height":200,"source_coordinate_space":"exif_corrected_source_pixels"},"transform":{"exif_orientation_applied":false,"scale_x":1,"scale_y":1,"model_input_color_space":"RGB","notes":[]},"objects":[],"modules":{"ocr":{"module":"ocr","state":"success","duration_ms":1,"model_id":"ocr","backend":"mock","warnings":[],"error":null},"figure_table":{"module":"figure_table","state":"success","duration_ms":1,"model_id":"layout","backend":"mock","warnings":[],"error":null},"stamp_signature":{"module":"stamp_signature","state":"success","duration_ms":1,"model_id":"marks","backend":"mock","warnings":[],"error":null}},"processing":{"state":"success","duration_ms":2,"warnings":[]}}
```

### `DocumentExtractionResponse`

Required fields: `schema_version`, `request_id`, `document_id`, `document_metadata` default `{}`, `page_count`, `pages`, flattened `objects`, `object_counts`, and `processing`. Every flattened object retains document/page identity. A complete multi-page response can be obtained from the curl example; the partial example above shows the nesting.

```json
{"schema_version":"wiki-hami.extraction.v1","request_id":"req_x","document_id":"DOC-1","document_metadata":{},"page_count":1,"pages":[{"schema_version":"wiki-hami.extraction.v1","request_id":"req_x","document_id":"DOC-1","page_id":"DOC-1:p1","page_number":1,"page_metadata":{},"image":{"filename":"p1.png","mime_type":"image/png","source_width":100,"source_height":200,"processed_width":100,"processed_height":200,"source_coordinate_space":"exif_corrected_source_pixels"},"transform":{"exif_orientation_applied":false,"scale_x":1,"scale_y":1,"model_input_color_space":"RGB","notes":[]},"objects":[],"modules":{"ocr":{"module":"ocr","state":"success","duration_ms":1,"model_id":"ocr","backend":"mock","warnings":["no_text_detected"],"error":null},"figure_table":{"module":"figure_table","state":"success","duration_ms":1,"model_id":"layout","backend":"mock","warnings":["no_figure_or_table_detected"],"error":null},"stamp_signature":{"module":"stamp_signature","state":"success","duration_ms":1,"model_id":"marks","backend":"mock","warnings":["no_stamp_or_signature_detected"],"error":null}},"processing":{"state":"success","duration_ms":2,"warnings":["no_text_detected","no_figure_or_table_detected","no_stamp_or_signature_detected"]}}],"objects":[],"object_counts":{"paragraph":0,"table":0,"figure":0,"stamp":0,"signature":0},"processing":{"state":"success","duration_ms":2,"warnings":["no_text_detected","no_figure_or_table_detected","no_stamp_or_signature_detected"]}}
```

## HTTP error shapes

FastAPI field validation uses the standard `422` detail array. Custom JSON parsing errors use a string detail, and image validation uses the identity-bearing object shown earlier. Examples:

```json
{"detail":"pages_metadata_json must be an array with one entry per uploaded image"}
```

```json
{"detail":[{"type":"missing","loc":["body","document_id"],"msg":"Field required","input":null}]}
```

Unexpected independent-module failures are HTTP `500` and may use the server's generic error body. Do not depend on a structured canonical response for that case.
