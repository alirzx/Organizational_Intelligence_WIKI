# Extraction V1 architecture

## Scope

Extraction V1 turns raster document pages into canonical `paragraph`, `figure`, `table`, `stamp`, and `signature` detections. Template creation, document linking, RAG/LLM mapping, table-cell extraction, signature identity and wiki generation remain outside this repository.

## Product and local boundaries

```text
Product/backend                                     Local inspector
      |                                                   |
      | image_url                                         +-- upload images
      v                                                   |
+----------------------+                                  +-- select MinIO objects
| MinIO acquisition    |<---------------------------------+
| validate URL         |                                  |
| bucket/object lookup |                                  |
| authenticated fetch  |                                  |
+----------+-----------+                                  |
           | image bytes                                  |
           +-------------------+--------------------------+
                               v
                 shared validation/preprocessing
                               |
              +----------------+----------------+
              |                |                |
          PaddleOCR       PP-DocLayoutV3       RF-DETR
              |                |                |
              +------ adapters + source-coordinate restore
                               |
                     canonical page objects
```

The three production APIs are `/ocr`, `/figure-table` and `/stamp-signature`. They accept one MinIO URL each and execute only their model pipeline. `/extract` remains the multipart local workflow. `/extract/minio` is the local/E2E multi-page equivalent of the production storage path and runs all three services.

## Acquisition boundary

MinIO is intentionally isolated under `app/storage/`. Model backends do not know whether bytes came from multipart upload or object storage. Both paths converge on `prepare_page()`, which owns validation, Pillow decode, EXIF transpose, RGB conversion, bounded resize and construction of the `PreparedPage` used by every model.

`WIKI_HAMI_MINIO_ENDPOINT` is the address used by Wiki Hami's MinIO SDK. `WIKI_HAMI_MINIO_PUBLIC_BASE_URL` is the host/port accepted in backend URLs. This separation supports Docker mappings such as internal `minio:9000` and external `192.168.x.x:9002`.

## Service lifecycle

Settings and the storage/model services are process-local cached instances. Heavy model objects continue to initialize lazily on first prediction and remain CPU-configured. MinIO client construction is also lazy. No model implementation or device behavior changes as part of storage integration.

## Canonical contract

All public detection geometry remains `exif_corrected_source_pixels`. `ImageMetadata.source` records whether a page was acquired by `upload` or `minio`; MinIO provenance may include bucket, object key and ETag. Model `Provenance` remains separate and identifies module/backend/model/revision.

The document response still provides `pages[]`, flattened `objects[]`, complete `object_counts`, and processing status.

## Failure boundaries

Image acquisition/preparation happens before inference. Invalid MinIO URLs/images are rejected before model execution. Missing objects return 404, storage failures 502 and disabled/misconfigured storage 503.

For full extraction, once page preparation succeeds the existing module isolation remains: timeouts/exceptions become failed module statuses and other successful model objects are retained. Independent production module inference exceptions still propagate as server errors.

## Security

Backend URLs are not arbitrary HTTP fetch targets. The storage service validates scheme, configured public host/port, configured bucket and object path, then uses the authenticated MinIO client to read the object. Storage credentials are environment-only and never exposed by the API/UI.

The object listing/proxy endpoints exist for the internal Streamlit inspector and are controlled by `WIKI_HAMI_MINIO_BROWSER_ENABLED`.

## Parallelism and resources

Model concurrency is unchanged: different model families can overlap; each real backend serializes prediction on its shared model instance. Keep one Uvicorn worker unless memory measurements justify duplication. MinIO integration adds network/object-read time before preparation but does not duplicate models.
