# MinIO integration

## Purpose

Wiki Hami does not require the product backend to upload image bytes. Production module APIs accept a MinIO object URL and obtain the object themselves through an authenticated MinIO/S3 client. Local development keeps multipart upload support and can also exercise the same MinIO acquisition path.

The storage layer is deliberately upstream of image preprocessing and model execution:

```text
Product backend -> image_url -> validate MinIO URL -> bucket/object key
                                           |
                                           v
                                  authenticated MinIO client
                                           |
                                           v
                                       image bytes
                                           |
Local upload -------------------------------+
                                           v
                              shared validation/preprocessing
                                           |
                        +------------------+------------------+
                        |                  |                  |
                     OCR CPU          Layout CPU         RF-DETR CPU
```

No model backend imports MinIO code.

## Two endpoint concepts

Storage routing must distinguish two addresses:

- `WIKI_HAMI_MINIO_ENDPOINT`: where Wiki Hami itself connects. Inside a Compose network this can be `minio:9000`.
- `WIKI_HAMI_MINIO_PUBLIC_BASE_URL`: the external/public base found in backend-provided object URLs, for example `http://192.168.4.209:9002`.

They may be identical, but they do not need to be. This handles Docker mappings such as host `9002 -> container 9000` without hardcoding either port in application code.

Example:

```env
WIKI_HAMI_MINIO_ENABLED=true
WIKI_HAMI_MINIO_ENDPOINT=minio:9000
WIKI_HAMI_MINIO_PUBLIC_BASE_URL=http://192.168.4.209:9002
WIKI_HAMI_MINIO_ACCESS_KEY=<secret>
WIKI_HAMI_MINIO_SECRET_KEY=<secret>
WIKI_HAMI_MINIO_SECURE=false
WIKI_HAMI_MINIO_BUCKET=wiki-documents
```

Credentials belong in the real `.env`/GitLab file variable, never in Git.

## URL handling and security

The backend-supplied URL is not downloaded with `requests.get`. Wiki Hami parses it and requires:

- `http` or `https`;
- host and port matching `WIKI_HAMI_MINIO_PUBLIC_BASE_URL`;
- the configured bucket;
- a non-empty object key;
- no embedded credentials, fragments, or dot/dot-dot path segments.

The validated bucket/key is then passed to the MinIO SDK. This prevents the model API from becoming a general-purpose URL fetcher and avoids SSRF-style access to unrelated hosts.

Query strings can be present in supplied URLs; object identity comes from the path. Credentials/presigned secrets are never echoed in canonical source metadata.

## Product API flow

The three production APIs use one JSON contract:

```json
{
  "document_id": "DOC-100",
  "image_url": "http://storage.example:9002/wiki-documents/docs/DOC-100/page-001.jpg",
  "page_number": 1,
  "page_id": "DOC-100:p1",
  "page_metadata": {"asset_id": "asset-991"}
}
```

The response remains `ModulePageResponse`. `image.source` records safe acquisition provenance: source type, bucket, object key and ETag.

## Local full extraction

Two complete-document paths are available:

- `POST /api/v1/extract`: existing multipart local-upload workflow.
- `POST /api/v1/extract/minio`: JSON workflow with one or more MinIO page URLs.

Both converge on the same `prepare_page()` function and the same `ExtractionOrchestrator`, so geometry, models, adapters, failure isolation and output schemas remain identical.

## Local storage inspection endpoints

The Streamlit inspector uses:

- `GET /api/v1/storage/minio/health`
- `GET /api/v1/storage/minio/objects?prefix=...`
- `GET /api/v1/storage/minio/object?object_key=...`

Object listing and source proxy are controlled by `WIKI_HAMI_MINIO_BROWSER_ENABLED`. They are intended for internal development/inspection. Disable them in a production deployment that does not expose the Streamlit storage browser.

## Errors

- invalid URL or image: `422`;
- missing object: `404`;
- storage connectivity/read failure: `502`;
- disabled/missing MinIO configuration: `503`.

Model inference errors on independent product endpoints still surface as server errors; `/extract` and `/extract/minio` retain the existing per-module partial-success boundary once page acquisition/preparation has succeeded.
