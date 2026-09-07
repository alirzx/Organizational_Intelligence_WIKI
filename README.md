# Wiki Hami — Extraction V1

Wiki Hami Extraction V1 turns one or more page images from a logical document into canonical OCR paragraph, figure, table, stamp, and signature detections.

This repository is strictly Step 1: Detection & Extraction. Make Template, Doc Linking, RAG/semantic/LLM mapping, table-cell extraction, signature identity, stamp interpretation, and wiki generation are not implemented here.

## Architecture

```text
Document (1..N images)
  -> validate + EXIF orientation + RGB + bounded resize once per page
  -> OCR + Figure/Table + Stamp/Signature
  -> model-output adapters + restoration to source-image coordinates
  -> page aggregation
  -> pages[] + flattened document objects[] + counts/status/provenance
```

Every canonical object repeats `document_id`, `page_id`, and `page_number`. Public geometry is always in `exif_corrected_source_pixels`, not model-resized coordinates. See [architecture](docs/architecture.md) and [workflows](docs/workflows.md).

## APIs

Production/backend integrations use the independent module APIs:

- `POST /api/v1/ocr`
- `POST /api/v1/figure-table`
- `POST /api/v1/stamp-signature`

The local Streamlit inspector, E2E tests, demos, and evaluation use `POST /api/v1/extract` for the complete multi-page workflow. It calls shared Python services inside the FastAPI process; it does not make loopback HTTP calls and does not replace the independent production APIs.

Process/config health is `GET /api/v1/health`. Full multipart fields, responses, schemas, status behavior, and curl examples are in the [API reference](docs/api.md).

## Baseline models

| Module | Baseline | Default device | Canonical output |
|---|---|---|---|
| OCR | PaddleOCR: `PP-OCRv5_server_det` + `arabic_PP-OCRv5_mobile_rec` | CPU | `paragraph` |
| Figure/Table | `PaddlePaddle/PP-DocLayoutV3` | CPU | `figure`, `table` |
| Stamp/Signature | `bluecopa/rf-detr-stamp-signature-detector` | CPU | `stamp`, `signature` |

The RF-DETR checkpoint also predicts checked/unchecked checkboxes; V1 filters them. A CUDA-capable Torch installation does not force RF-DETR onto GPU—the `WIKI_HAMI_STAMP_SIGNATURE_DEVICE` setting controls it. See [models and cache audit](docs/models.md).

## Repository structure

```text
app/api/             FastAPI routes and multipart parsing
app/core/            settings and process-local service registry
app/preprocessing/   validation, image normalization, geometry transforms
app/modules/         OCR, layout, and RF-DETR backends/services/adapters
app/orchestration/   multi-module/page execution and aggregation
app/schemas/         canonical Pydantic contracts
ui/                  Streamlit inspector, visualizer, JSON/ZIP artifacts
tests/               unit and API contract tests
deployment/          production-style Compose baseline
docs/                engineering and integration documentation
models/              policy/placeholder; downloaded weights are not committed
```

`configs/` and `data/` are currently placeholders. The API does not persist results; the UI creates downloadable artifacts in memory.

## Python 3.11 setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Requirements are split by purpose:

- `requirements.txt`: FastAPI, image processing, Streamlit/client runtime;
- `requirements-dev.txt`: base dependencies plus tests;
- `requirements-models.txt`: PaddleOCR, RF-DETR, and Hugging Face adapters; PaddlePaddle itself is platform-specific;
- `requirements-paddle-cpu.txt`: tested CPU PaddlePaddle version.

Install real CPU model runtimes with:

```bash
python -m pip install -r requirements-paddle-cpu.txt \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements-models.txt
```

## Environment and mock/real backends

Settings load from `.env` and environment variables. `.env.example` documents request limits, concurrency, thresholds, devices, model IDs, and caches. It defaults to mock backends so API/UI development and tests start without heavyweight downloads.

For real inference set:

```text
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
```

Mocks exercise the canonical pipeline but do not represent model quality.

## Run FastAPI

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API root: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- health: `http://localhost:8000/api/v1/health`

## Run Streamlit

Keep FastAPI running, then in another terminal:

```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501
```

The inspector uploads one or many pages to `/extract`, shows document/page status and latency, original and annotated pages, a fixed class legend, OCR paragraphs, page/transform metadata, and canonical JSON. It can download complete JSON or a ZIP containing JSON, a manifest, and all annotated PNGs. Annotations use canonical source coordinates and EXIF-corrected images.

## Model caching

First real inference downloads missing weights; later starts reuse disk caches, and later requests reuse in-memory model instances. Local defaults are:

- PaddleX official models: `~/.paddlex/official_models` (`PADDLE_PDX_CACHE_HOME`);
- Paddle runtime: `~/.cache/paddle` (`PADDLE_HOME`);
- Hugging Face/RF-DETR: `~/.cache/huggingface` (`HF_HOME`).

`models/` stays empty because frameworks own these caches. Docker/Compose maps all three to persistent storage; weights are not committed. See [deployment](docs/deployment.md).

## Docker Compose

```bash
docker compose up -d --build
```

- FastAPI: `http://localhost:8000`
- Streamlit: `http://localhost:8501`

The default Docker build installs real CPU model dependencies. The configured `.env` still selects mock or real backends. Local Compose uses one named persistent cache volume and one API worker to avoid duplicating model memory.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Tests force mock backends and never download weights. They cover module/API contracts, multi-page aggregation and provenance, corrupt-page rejection, partial module success, service reuse, bbox/polygon coordinate round trips, model adapters, OCR grouping, stable visualization colors, multi-module annotation, canonical JSON, and multi-page ZIP export.

## Documentation

- [Contract notes](docs/contracts.md)
- [Architecture](docs/architecture.md)
- [Workflows and preprocessing](docs/workflows.md)
- [API integration reference and canonical schemas](docs/api.md)
- [Models and cache audit](docs/models.md)
- [Deployment](docs/deployment.md)
