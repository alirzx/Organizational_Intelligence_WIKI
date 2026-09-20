# Extraction V1 deployment

## Runtime topology

The normal deployment remains one FastAPI process plus optional Streamlit. MinIO is an external S3 dependency; Wiki Hami does not require MinIO to run in the same Compose project.

```text
Product backend -> Wiki Hami API -> MinIO/S3
                           |
                    three CPU models
```

Keep one Uvicorn worker while all models are process-local. Every additional process loads another OCR, layout and RF-DETR model set.

## Local Python

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python run.py --api
```

Second terminal:

```bash
source .venv/bin/activate
python run.py --web
```

The base requirements now include the official `minio` Python SDK.

## Real CPU model dependencies

Install in this order:

```bash
python -m pip install -r requirements-paddle-cpu.txt \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements-torch-cpu.txt \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-models.txt
```

Select:

```env
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_OCR_DEVICE=cpu
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_FIGURE_TABLE_DEVICE=cpu
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
WIKI_HAMI_STAMP_SIGNATURE_DEVICE=cpu
```

## MinIO configuration

Example when MinIO listens on `9000` inside its Docker network but is published to clients as host port `9002`:

```env
WIKI_HAMI_MINIO_ENABLED=true
WIKI_HAMI_MINIO_ENDPOINT=minio:9000
WIKI_HAMI_MINIO_PUBLIC_BASE_URL=http://192.168.x.x:9002
WIKI_HAMI_MINIO_ACCESS_KEY=<secret>
WIKI_HAMI_MINIO_SECRET_KEY=<secret>
WIKI_HAMI_MINIO_SECURE=false
WIKI_HAMI_MINIO_BUCKET=wiki-documents
```

If Wiki Hami is not on the MinIO Docker network, set `MINIO_ENDPOINT` to whatever host/port is reachable from the Wiki Hami container. Do not assume that the backend-facing published port and the API-to-MinIO port are identical.

The public base URL is a validation policy for URLs sent by the backend. The API never treats those URLs as arbitrary HTTP download targets; object bytes are read via the configured MinIO client.

Credentials belong in deployment secrets/GitLab `ENV_FILE`, never in source control.

## Docker image

No special Dockerfile change is required for storage. The existing Dockerfile installs `requirements.txt` (directly or through `requirements-models.txt`), so the MinIO SDK is included automatically.

```bash
docker build -t wiki-hami-extraction:0.2.0 .
```

The image continues to expose 8000/8501 and uses `/api/v1/health` for liveness. Liveness does not load models or contact MinIO. Use `/api/v1/storage/minio/health` when storage connectivity must be checked explicitly.

## Compose

Both `compose.yaml` and `deployment/compose.prod.yaml` already use `env_file: .env`/`../.env`; therefore the new `WIKI_HAMI_MINIO_*` settings are injected without structural Compose changes.

Production-style startup remains:

```bash
mkdir -p /var/lib/wiki-hami/cache /var/lib/wiki-hami/outputs
docker compose -f deployment/compose.prod.yaml up -d
```

Model cache paths remain persistent:

- Hugging Face/RF-DETR: `HF_HOME`;
- Paddle runtime: `PADDLE_HOME`;
- PaddleX official models: `PADDLE_PDX_CACHE_HOME`.

MinIO document images remain in object storage and are read per request; they are not copied into those framework caches.

## Production versus local storage browser

The product backend needs only the three module endpoints. The Streamlit inspector additionally uses MinIO health/list/object-proxy routes for browsing and preview.

Set:

```env
WIKI_HAMI_MINIO_BROWSER_ENABLED=false
```

when those internal inspection endpoints should not be available in a production environment. If Streamlit is intentionally deployed as an internal engineering console, the flag may remain enabled behind the appropriate network/access controls.

## First run

1. API starts without loading model weights.
2. `/api/v1/health` can become healthy immediately.
3. MinIO-backed requests first acquire the image object, validate/decode it, then initialize the selected model if needed.
4. First real model inference downloads missing weights into the persistent framework cache.
5. Later requests reuse both on-disk weights and the in-memory model instance.
6. Container restart reconstructs models from the persistent cache; MinIO source objects remain external.

## Operational notes

Per-image storage objects are bounded by the same `max_upload_bytes` limit before full object read. Pillow still enforces decode/pixel validation after acquisition. The public URL host/port and bucket are restricted by configuration, preventing arbitrary URL fetching.

The API currently does not provide end-user authentication/rate limiting itself. Keep product and dev-storage endpoints behind the deployment network/API gateway appropriate to your environment.
