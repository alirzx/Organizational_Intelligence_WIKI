#!/usr/bin/env bash
set -euo pipefail
streamlit run ui/streamlit_app.py --server.port "${UI_PORT:-8501}"
