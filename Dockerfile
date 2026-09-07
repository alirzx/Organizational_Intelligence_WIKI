FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    PADDLE_HOME=/app/.cache/paddle \
    PADDLE_PDX_CACHE_HOME=/app/.cache/paddlex \
    PADDLE_PDX_MODEL_SOURCE=HUGGINGFACE

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-models.txt requirements-paddle-cpu.txt ./

ARG INSTALL_MODELS=true
RUN python -m pip install --upgrade pip && \
    if [ "$INSTALL_MODELS" = "true" ]; then \
      python -m pip install -r requirements-paddle-cpu.txt -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ && \
      python -m pip install -r requirements-models.txt; \
    else \
      python -m pip install -r requirements.txt; \
    fi

COPY . .

RUN mkdir -p /app/.cache/huggingface /app/.cache/paddlex /app/data/outputs

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
