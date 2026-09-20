# Deployment baseline

Wiki Hami production uses one FastAPI worker with one process-local instance of each CPU model backend. Additional Uvicorn workers duplicate the complete model set in RAM.

The Dockerfile requires no special MinIO stage: `minio` is a base runtime dependency in `requirements.txt`, which the existing model installation chain already installs. Both Compose files already load `.env`, so MinIO configuration is supplied exactly like model configuration and secrets are not baked into the image.

## Production configuration

Set real CPU model backends plus MinIO connection settings in the deployment `.env` / GitLab `ENV_FILE`:

```env
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_OCR_DEVICE=cpu
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_FIGURE_TABLE_DEVICE=cpu
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
WIKI_HAMI_STAMP_SIGNATURE_DEVICE=cpu

WIKI_HAMI_MINIO_ENABLED=true
WIKI_HAMI_MINIO_ENDPOINT=minio:9000
WIKI_HAMI_MINIO_PUBLIC_BASE_URL=http://<external-host>:<exposed-port>
WIKI_HAMI_MINIO_ACCESS_KEY=<secret>
WIKI_HAMI_MINIO_SECRET_KEY=<secret>
WIKI_HAMI_MINIO_BUCKET=wiki-documents
WIKI_HAMI_MINIO_SECURE=false
```

`MINIO_ENDPOINT` is where the API container reaches S3. `MINIO_PUBLIC_BASE_URL` is the host/port in URLs supplied by the backend; it may be a different exposed port such as `9002` while the MinIO container listens on `9000`.

Production backend calls `/ocr`, `/figure-table`, and `/stamp-signature` with JSON MinIO URLs. `/extract` is the local upload workflow and `/extract/minio` is the local/E2E full MinIO workflow.

Disable `WIKI_HAMI_MINIO_BROWSER_ENABLED` when the Streamlit object-browser/proxy endpoints are not required in production.

Model cache/warmup behavior is unchanged. First real inference downloads missing model weights to the persistent model cache; later containers reuse those files.

See `docs/deployment.md` and `docs/minio.md` for details.
