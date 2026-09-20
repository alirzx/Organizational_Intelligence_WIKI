# Extraction V1 workflows

## Shared page preparation

Both acquisition paths converge before model work:

```text
multipart UploadFile ----read bytes----+
                                      |
MinIO image_url -> validate -> SDK read+
                                      v
                              validate image bytes
                                      v
                         Pillow decode + EXIF transpose
                                      v
                      RGB + source geometry definition
                                      v
                     bounded long-edge resize (2500)
                                      v
                                PreparedPage
```

The same size/pixel/decode rules therefore apply to uploaded and MinIO images. Public coordinates are source pixels after EXIF display orientation and before shared resize.

## Production single-module workflow

```text
backend POST JSON
  document_id + image_url + page identity
        |
        v
validate URL host/port/bucket
        |
        v
MinIO SDK stat + bounded object read
        |
        v
shared prepare_page()
        |
        +--> /ocr             -> OCR service -> paragraph objects
        +--> /figure-table    -> layout service -> figure/table objects
        +--> /stamp-signature -> RF-DETR service -> stamp/signature objects
```

Each endpoint runs only the selected model and returns `ModulePageResponse`.

## Local uploaded document

`POST /extract` retains the multipart workflow used by Streamlit and local evaluation. One or more uploaded pages are prepared and passed to `ExtractionOrchestrator`, which schedules all three model families for each admitted page.

## Local MinIO document

`POST /extract/minio` accepts one or more MinIO page references. Every object is acquired through the same storage service used by production module APIs, then the resulting prepared pages enter the exact same `ExtractionOrchestrator` as uploaded pages.

This route exists so local development can validate the real storage path without making the product backend call three APIs manually.

## Streamlit workflow

The inspector has two input modes:

- Local upload: select 1..N image files and call `/extract`.
- MinIO: check storage connectivity, browse objects by prefix, multi-select pages, preview through the API proxy, then call `/extract/minio`.

After either route returns, the result workflow is identical: source/annotated image comparison, per-pipeline status, ordered detections, model-specific views, canonical page/document JSON, and JSON/ZIP export.

## Error/status workflow

Acquisition/preparation failures reject the request before inference. During full extraction, module failures remain isolated and successful objects survive. Independent model APIs do not wrap inference exceptions in a partial-success envelope.
