.PHONY: install install-dev install-models test api ui up down logs smoke

install:
	python -m pip install -r requirements.txt

install-dev:
	python -m pip install -r requirements-dev.txt

install-models:
	python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
	python -m pip install -r requirements-models.txt

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run ui/streamlit_app.py --server.port 8501

test:
	pytest -q

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api ui

smoke:
	python scripts/smoke_test.py
