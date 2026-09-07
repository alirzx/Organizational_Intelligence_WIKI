# Deployment baseline

The V1 baseline is one FastAPI worker with one process-local instance of each model backend. Additional workers duplicate model RAM/VRAM. Full setup, cache, warmup, limits, and restart behavior are documented in [docs/deployment.md](../docs/deployment.md).

```bash
docker build -t wiki-hami-extraction:0.2.0 .
docker compose up -d --build
```

For the production-style bind-mounted cache:

```bash
mkdir -p /var/lib/wiki-hami/cache /var/lib/wiki-hami/outputs
docker compose -f deployment/compose.prod.yaml up -d
```

Production backends can call the independent `/ocr`, `/figure-table`, and `/stamp-signature` endpoints. `/extract` is the complete local E2E/demo/evaluation workflow used by Streamlit.

Set real backends in `.env` when the model dependencies are installed:

```text
WIKI_HAMI_OCR_BACKEND=paddle
WIKI_HAMI_FIGURE_TABLE_BACKEND=pp_doclayout
WIKI_HAMI_STAMP_SIGNATURE_BACKEND=rfdetr
```

The first real inference downloads missing weights. Persist `HF_HOME`, `PADDLE_HOME`, and especially PaddleX's `PADDLE_PDX_CACHE_HOME`; both Compose files do so.
