VENV ?= .venv
PYTHON := $(VENV)/bin/python

.PHONY: install test lint format run eval ui tunnel up down

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e "./backend[dev]"

test:
	cd backend && ../$(PYTHON) -m pytest

lint:
	cd backend && ../$(PYTHON) -m ruff check . && ../$(PYTHON) -m ruff format --check .

format:
	cd backend && ../$(PYTHON) -m ruff format .

run:
	cd backend && ../$(PYTHON) -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

eval:
	cd backend && ../$(PYTHON) -m app.evals.runner --label v1 --out evals/baselines/v1.json --publish evals/baselines/current.json

ui:
	cd frontend && npm run dev

tunnel:
	npx --yes cloudflared tunnel --url http://127.0.0.1:8080

up:
	docker compose up --build

down:
	docker compose down
