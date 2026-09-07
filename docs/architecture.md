# Extraction V1 architecture

## Scope and boundaries

Extraction V1 accepts raster image files representing one logical document. It detects five canonical object types: `paragraph`, `figure`, `table`, `stamp`, and `signature`. It does not create templates, link documents, extract table cells, identify signers, interpret stamps, perform RAG/LLM mapping, or generate wiki content.

The three module APIs are the production integration boundary. `/api/v1/extract` is an in-process orchestration convenience for local development, the Streamlit inspector, tests, and evaluation. It does not replace the independent APIs.

```text
Product/backend                         Local E2E / UI
      |                                      |
      +--> POST /ocr                         +--> POST /extract
      +--> POST /figure-table                         |
      +--> POST /stamp-signature                      v
                    |                        shared Python services
                    +--------------+------------------+
                                   v
                   validation -> shared preprocessing (once/page)
                                   |
                  +----------------+----------------+
                  |                |                |
              PaddleOCR      PP-DocLayoutV3      RF-DETR
                  |                |                |
                  +-------- adapters + source-coordinate restore
                                   |
                         canonical page objects
                                   |
                   pages[] + flattened document objects[]
```

## Repository responsibilities

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI application and router registration |
| `app/api/v1/endpoints/` | HTTP multipart contracts; no model logic |
| `app/api/v1/request_parsing.py` | JSON form parsing, page identity defaults, upload-to-page preparation |
| `app/core/config.py` | Environment-backed settings |
| `app/core/runtime.py` | Cached process-local service registry shared by all endpoints |
| `app/preprocessing/` | Validation, decode, EXIF transpose, RGB conversion, bounded resize, geometry transforms |
| `app/modules/*/backend.py` | Framework/model initialization and model-specific prediction/parsing |
| `app/modules/*/adapter.py` | Filtering/remapping, canonical objects, provenance, inverse geometry mapping |
| `app/modules/*/service.py` | Async module facade, thread offload, timing, module response |
| `app/orchestration/extractor.py` | Bounded page concurrency, parallel modules, failure isolation, page/document aggregation |
| `app/schemas/` | Public Pydantic contract |
| `ui/` | Streamlit API client, source-coordinate rendering, in-memory exports |
| `tests/` | Contract, aggregation, adapter, transform, failure isolation, and UI-helper tests |

`configs/` and `data/` currently contain no implementation. `data/outputs` is mounted by deployment files but the API does not write extraction results there. `models/` is a policy/placeholder directory, not the active framework cache.

## Request and service lifecycle

FastAPI imports one settings object and one cached instance of each module service. The module endpoints and the orchestrator share those services through `app/core/runtime.py`; therefore each configured real backend can load at most one model instance per process. The backend object is created at startup/import, while its heavyweight model is initialized lazily on its first prediction. A second Uvicorn worker is a second process and therefore loads another complete model set.

Each independent module endpoint prepares one uploaded page and calls one service. `/extract` prepares all pages once, then calls the same three service objects directly. It does **not** make loopback HTTP requests to the module endpoints.

## Canonical contract and provenance

The public geometry space is `exif_corrected_source_pixels`: pixels after EXIF display orientation and before the shared resize. Adapters restore every model-space box/polygon before constructing `DetectedObject`. Every object repeats `document_id`, `page_id`, and `page_number`; flattening never removes page provenance. `Provenance` identifies the responsible module, configured backend, model ID, and optional model version/revision.

The document response deliberately provides both views:

- `pages[]`: page metadata, dimensions, transform, per-module status, page status, and page objects.
- `objects[]`: all page objects flattened and sorted by page number then geometry.
- `object_counts`: all five enum keys, including zero counts.

No cross-module deduplication, reading-order reconstruction, semantic linking, or table structure extraction occurs in V1.

## Error isolation and status

There are two different failure boundaries.

1. Request preparation is all-or-nothing. Invalid JSON, a descriptor-count mismatch, too many pages, an empty/oversized/corrupt image, invalid dimensions, or an excessive pixel count produces HTTP `422` before model orchestration. If page 2 is corrupt, no partial document response is returned.
2. Once `/extract` starts module execution, each module call is isolated. Exceptions and timeouts become a failed `ModuleStatus`; successful objects from the other modules remain. The HTTP response is still `200` and reports `success`, `partial_success`, or `failed` in the payload.

A page is `success` only when all three modules report success, `failed` when none succeeds, and otherwise `partial_success`. A document is `success` when all pages succeed, `failed` when every page fails, and otherwise `partial_success`. Module endpoints do not have the orchestration recovery boundary: backend exceptions propagate as HTTP `500`.

## Parallelism and locking

`page_concurrency` (default 4) is a semaphore over whole page jobs. Within an admitted page, the three module coroutines are scheduled together with `asyncio.gather`. Real synchronous prediction calls use `asyncio.to_thread`, preventing the event loop from being blocked.

Each backend owns two thread locks:

- an initialization lock prevents duplicate first-load/download work;
- a prediction lock serializes inference against that model instance.

Consequently OCR, layout, and RF-DETR can overlap with each other, but two pages cannot simultaneously call the same model instance. With real backends, throughput is bounded by one active inference per model family per process, even though up to four page workflows are admitted. A timeout cancels the awaiting coroutine, but Python cannot forcibly stop an already-running worker-thread inference; that call may finish in the background before releasing its prediction lock.

## Configuration

`Settings` reads `.env` and `WIKI_HAMI_*` variables. Important groups are request limits, shared resize, page/module concurrency, module backend/device/threshold/model IDs, OCR paragraph geometry, and figure/table label sets. Framework cache variables (`HF_HOME`, `PADDLE_HOME`, and `PADDLE_PDX_CACHE_HOME`) are direct framework environment variables and are therefore not prefixed.

The committed example defaults to mock backends for a safe lightweight start. Real backend names are `paddle`, `pp_doclayout`, and `rfdetr`. CPU is the configured default for every model; installing a CUDA-enabled Torch build does not require selecting a CUDA RF-DETR device.

## Deployment topology

The baseline is one API container/process and an optional Streamlit container. The UI calls the API over HTTP; it never imports or executes model services. A named volume in local Compose and a bind-mounted cache root in production Compose retain model downloads across container replacement/restart. See [deployment.md](deployment.md).

## Testing strategy

Automated tests force mock backends before importing the application, so tests never download weights. Adapter tests use synthetic model outputs, transform tests verify inverse geometry, orchestration tests inject a failing module, API tests exercise multipart contracts and multi-page provenance, and UI tests verify the stable color mapping plus JSON/ZIP generation. Real-model quality and latency require a separate representative-document evaluation run.

## Current implementation versus contractual intent

The current implementation satisfies the V1 document/page/provenance contract and preserves successful results after module failures. Its deliberate limitations are:

- upload validation is all-or-nothing rather than returning partial results for corrupt pages;
- `GET /api/v1/health` reports process/configuration health, not model readiness and does not warm weights;
- layout polygons are currently rectangular polygons derived from returned XYXY coordinates;
- no persistent result store is implemented; Streamlit exports are generated in memory;
- page ID/page number uniqueness is caller responsibility;
- API MIME strings are recorded but not trusted as format validation—Pillow decode is authoritative.
