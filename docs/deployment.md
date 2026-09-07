# Extraction V1 deployment

## Local Python 3.11

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501
```

The UI expects `WIKI_HAMI_API_BASE=http://localhost:8000/api/v1` unless overridden. It has no embedded model logic, so FastAPI must be available.

## Real CPU model dependencies

Base `requirements.txt` includes API/UI dependencies only. `requirements-dev.txt` adds tests. For all real models on CPU:

```bash
source .venv/bin/activate
python -m pip install -r requirements-paddle-cpu.txt \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements-models.txt
```

Then set:

```text
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
```

CPU remains valid even if Torch is CUDA-capable. To select another device, change the module-specific `*_DEVICE` setting only after validating that the installed framework/runtime supports it.

## Cache paths

| Framework | Environment | Local default | Container value |
|---|---|---|---|
| Hugging Face Hub / RF-DETR | `HF_HOME` | `~/.cache/huggingface` | `/app/.cache/huggingface` |
| Paddle engine | `PADDLE_HOME` | `~/.cache/paddle` | `/app/.cache/paddle` |
| PaddleX/PaddleOCR official models | `PADDLE_PDX_CACHE_HOME` | `~/.paddlex` | `/app/.cache/paddlex` |

`PADDLE_PDX_MODEL_SOURCE=HUGGINGFACE` selects the preferred PaddleX source. `WIKI_HAMI_STAMP_SIGNATURE_CACHE_DIR`, when set, overrides `HF_HOME` only for the RF-DETR checkpoint download.

Do not bake downloaded weights into Git. For offline deployment, populate the mounted caches ahead of time and keep their directory structure intact. There is no built-in warmup command; one successful real inference per module downloads and initializes its model. A subsequent process reuses disk weights but must reconstruct models in RAM.

## Docker image

The default build installs CPU PaddlePaddle and all model extras:

```bash
docker build -t wiki-hami-extraction:0.2.0 .
```

For a lightweight mock-only image:

```bash
docker build --build-arg INSTALL_MODELS=false -t wiki-hami-extraction:mock .
```

The image exposes ports 8000 and 8501, runs the API by default, and checks `/api/v1/health`. Health is a liveness/config endpoint, not a model-readiness check.

## Local Compose

```bash
docker compose up -d --build
docker compose logs -f api ui
```

Services:

- API: `http://localhost:8000`, OpenAPI UI at `/docs`;
- Streamlit: `http://localhost:8501`;
- named cache volume: `wiki_hami_model_cache` mounted at `/app/.cache`;
- output bind mount: `./data/outputs:/app/data/outputs` (reserved; current API/UI do not persist runs there).

Use `docker compose down` without `-v` to preserve the named model cache. Removing the volume deletes cached weights and forces downloads on the next real inference.

## Production-style Compose

```bash
mkdir -p /var/lib/wiki-hami/cache /var/lib/wiki-hami/outputs
WIKI_HAMI_DATA_ROOT=/var/lib/wiki-hami \
  docker compose -f deployment/compose.prod.yaml up -d
```

The production file uses one Uvicorn worker and bind-mounts cache/output roots. Keep a single worker while models live in-process: every additional process loads another PaddleOCR, PP-DocLayout, and RF-DETR model set. Scale only after measuring RAM/VRAM and deciding whether model services should be separated.

Ensure the container user can write the mounted cache. Persist and back up only project-owned artifacts as required; framework caches are reproducible and can normally be repopulated.

## First-run and restart behavior

1. Container starts without loading models.
2. `/health` can become healthy before weights are present.
3. First request to a real backend acquires its initialization lock, downloads missing weights, and initializes the model.
4. Concurrent calls to the same still-loading backend wait on that lock.
5. Later requests reuse the in-memory model.
6. After container restart, disk weights remain on the volume and the model is reconstructed without downloading them again.

For controlled rollout, send a small representative request to `/ocr`, `/figure-table`, and `/stamp-signature` before routing user traffic. A network-free readiness guarantee would require a future explicit warmup/readiness mechanism.

## Operational limits and timeouts

Default per-image maximum is 25 MiB and 50 million pixels; `/extract` accepts at most 100 pages. Up to four page jobs are admitted, but each model instance serializes its own predictions. The 180-second module timeout bounds how long orchestration waits; it cannot forcibly terminate synchronous inference already running in a worker thread.

Reverse proxies should set multipart/body/time limits appropriate to the maximum document size. The application does not currently authenticate, rate-limit, persist results, or impose a whole-request byte ceiling.

## Outputs

The API returns JSON only and writes no extraction files. Streamlit retains the current run in session memory and offers:

- complete canonical `extraction.json`;
- a ZIP with canonical JSON, `manifest.json`, and one annotated PNG per page.

These are evaluation/debug exports, not a persistent storage subsystem.
