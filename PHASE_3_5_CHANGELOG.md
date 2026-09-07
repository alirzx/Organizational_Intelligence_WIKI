# Phase 3–5 implementation changelog

## Added

- PaddleOCR backend, paragraph grouping, and canonical OCR adapter.
- PP-DocLayoutV3 backend and figure/table adapter.
- RF-DETR Hugging Face checkpoint downloader/backend and stamp/signature adapter.
- Current RF-DETR/Supervision output compatibility plus legacy iterable fallback.
- Polygon source-coordinate restoration.
- Per-model inference locks and thread offloading for concurrent module execution.
- Per-module timeout in the document orchestrator.
- `.env` and `.env.example`.
- `requirements.txt`, `requirements-dev.txt`, `requirements-models.txt`.
- CPU-model Dockerfile and local `compose.yaml`.
- Production-style `deployment/compose.prod.yaml` and deployment notes.
- Makefile and smoke test.
- Model cache/storage policy.
- Model adapter unit tests.

## Extraction V1 documentation/UI audit

- Added authoritative architecture, workflow, API/schema, model/cache, and deployment documentation.
- Reworked Streamlit into a multi-page inspector with canonical source-coordinate overlays, fixed class colors, status/latency/OCR inspection, and JSON/ZIP downloads.
- Added reusable visualization and artifact helpers with unit coverage.
- Shared one process-local service/model instance between module endpoints and `/extract`.
- Corrected container persistence for PaddleX's actual `PADDLE_PDX_CACHE_HOME`.
- Added EXIF/polygon, partial-success, corrupt-page, service-lifecycle, cache-config, annotation, JSON, and ZIP tests.

## Validation

- Python compileall: pass.
- Pytest: 18 passed.
- Compose YAML parse: pass.
- Actual heavyweight model inference and Docker image build were not executed in this audit; previously downloaded local caches were inspected.
