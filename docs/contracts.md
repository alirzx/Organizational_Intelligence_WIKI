# Extraction V1 Contract Notes

## Coordinate space

Public detections use `exif_corrected_source_pixels`: the source image after EXIF display orientation is applied and before any model resize. Model backends may work in any internal coordinate space, but adapters must restore geometry before returning canonical objects.

## Document identity

One logical document has one `document_id` and one or more page images. Each page has a stable `page_id`, `page_number`, and arbitrary page metadata. Every detected object repeats `document_id`, `page_id`, and `page_number` so flattened document-level results never lose provenance.

## `/extract` multipart fields

- `document_id`: required string
- `images`: repeated file field, 1..N
- `document_metadata_json`: optional JSON object
- `pages_metadata_json`: optional JSON array, exactly one descriptor per image

Example page descriptor:

```json
{
  "page_id": "doc_42:p7",
  "page_number": 7,
  "filename": "scan_0007.png",
  "metadata": {"source_asset_id": "asset_991"}
}
```

## Shared vs model-specific normalization

Shared preprocessing owns validation, decode, display orientation, color space, resizing, and geometry transforms. Mean/std normalization, tensor layout, tokenization, and model-specific resize/padding belong inside each backend adapter.

## Status and failure boundary

`/extract` preserves successful module results when another module fails or times out and reports `success`, `partial_success`, or `failed` in page/document `processing`. These post-validation outcomes use HTTP 200. Upload, JSON, descriptor, and image validation happen before inference and are all-or-nothing: any invalid page rejects the request with HTTP 422 rather than returning a partial document.
