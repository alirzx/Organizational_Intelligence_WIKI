# Wiki Hami — Extraction V1

Wiki Hami Extraction V1 converts document page images into canonical OCR paragraph, figure, table, stamp and signature detections. This repository is Step 1 only; template generation, document linking and later semantic/wiki stages are outside its scope.

## Current architecture

Production images live in MinIO. The product backend sends an object URL to one of the three independent model APIs; Wiki Hami validates the configured MinIO host/bucket, obtains the object through its own authenticated MinIO client, performs shared preprocessing, then runs the selected CPU model.

```text
Product backend -> MinIO URL -> authenticated object acquisition -> prepare page
                                                            |
                              +-----------------------------+-----------------------------+
                              |                             |                             |
                           OCR API                    Figure/Table API             Stamp/Signature API
                              |                             |                             |
                           PaddleOCR                   PP-DocLayoutV3                   RF-DETR
```

Local development supports both uploaded images and MinIO objects. `/extract` is the existing upload-based full workflow; `/extract/minio` runs all three pipelines over MinIO pages. Both reuse the same preprocessing, model services and canonical output contract.

See [architecture](docs/architecture.md), [workflows](docs/workflows.md) and [MinIO integration](docs/minio.md).

## APIs

Product/backend:

- `POST /api/v1/ocr` — JSON + one MinIO `image_url`
- `POST /api/v1/figure-table` — JSON + one MinIO `image_url`
- `POST /api/v1/stamp-signature` — JSON + one MinIO `image_url`

Local/E2E:

- `POST /api/v1/extract` — multipart uploaded pages
- `POST /api/v1/extract/minio` — JSON with one or more MinIO page URLs

Storage inspection for the local UI:

- `GET /api/v1/storage/minio/health`
- `GET /api/v1/storage/minio/objects`
- `GET /api/v1/storage/minio/object`

Swagger/OpenAPI is at `/docs`. Exact contracts and examples are in [docs/api.md](docs/api.md).

## Baseline models

| Module | Model | Device | Canonical output |
|---|---|---|---|
| OCR | `PP-OCRv5_server_det` + `arabic_PP-OCRv5_mobile_rec` | CPU | `paragraph` |
| Figure/Table | `PaddlePaddle/PP-DocLayoutV3` | CPU | `figure`, `table` |
| Stamp/Signature | `bluecopa/rf-detr-stamp-signature-detector` | CPU | `stamp`, `signature` |

MinIO integration does not change model/device configuration.

## Repository structure

```text
run.py               unified local launcher
app/api/             FastAPI routes and request contracts
app/storage/         MinIO URL validation and authenticated object acquisition
app/core/            environment settings and process-local service registry
app/preprocessing/   validation, decode, EXIF/RGB/resize and geometry transforms
app/modules/         OCR, layout and RF-DETR backends/services/adapters
app/orchestration/   multi-page/all-model execution and aggregation
app/schemas/         public Pydantic contracts
ui/                  Streamlit engineering inspector and exports
tests/               unit/integration contracts
deployment/          production-style Compose baseline
docs/                architecture, API, storage and deployment documentation
```

## Python 3.11 setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

For real CPU models install in this order:

```bash
python -m pip install -r requirements-paddle-cpu.txt \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements-torch-cpu.txt \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-models.txt
```

## Environment

Real model selection:

```env
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_OCR_DEVICE=cpu
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_FIGURE_TABLE_DEVICE=cpu
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
WIKI_HAMI_STAMP_SIGNATURE_DEVICE=cpu
```

MinIO settings:

```env
WIKI_HAMI_MINIO_ENABLED=true
WIKI_HAMI_MINIO_ENDPOINT=minio:9000
WIKI_HAMI_MINIO_PUBLIC_BASE_URL=http://<external-minio-host>:<exposed-port>
WIKI_HAMI_MINIO_ACCESS_KEY=<secret>
WIKI_HAMI_MINIO_SECRET_KEY=<secret>
WIKI_HAMI_MINIO_SECURE=false
WIKI_HAMI_MINIO_BUCKET=wiki-documents
```

`MINIO_ENDPOINT` is Wiki Hami's connection address. `MINIO_PUBLIC_BASE_URL` is the host/port appearing in URLs sent by the backend. They can differ, for example Docker `minio:9000` internally versus host port `9002` externally. Never commit real credentials. See [docs/minio.md](docs/minio.md).

## Run locally

```bash
source .venv/bin/activate
python run.py --api
```

Second terminal:

```bash
source .venv/bin/activate
python run.py --web
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- UI: `http://localhost:8501`

The Streamlit inspector provides Local Upload and MinIO input modes, MinIO health/object browsing and preview, full extraction, source/annotated overlays, pipeline status, ordered detections, OCR/layout/mark views, page/document JSON and downloadable JSON/ZIP artifacts.

## Model caching

First real inference downloads missing model weights. Framework caches are persisted by Compose and later requests reuse in-memory model instances. MinIO objects are read from object storage per request; they are not copied into the model-cache directories.

## Docker / deployment

The existing Dockerfile automatically installs the MinIO SDK through `requirements.txt`; no model image/device changes are required. Both Compose files already load `.env`, so MinIO configuration is injected the same way as the existing model settings.

```bash
docker compose up -d --build
```

Production should keep one Uvicorn worker while models are process-local. Disable `WIKI_HAMI_MINIO_BROWSER_ENABLED` when the Streamlit storage browser/proxy is not required. See [deployment](docs/deployment.md).

## Tests

```bash
pytest -q
```

Tests keep real models/network disabled through mocks and cover product URL contracts, MinIO URL validation, uploaded and MinIO full extraction, canonical provenance, orchestration, transforms, adapters and UI helpers.

## Documentation

- [API reference](docs/api.md)
- [MinIO integration](docs/minio.md)
- [Architecture](docs/architecture.md)
- [Workflows](docs/workflows.md)
- [Models](docs/models.md)
- [Deployment](docs/deployment.md)
- [Contract notes](docs/contracts.md)
