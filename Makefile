
# Variables
UV := uv
PYTHON := $(UV) run python
ALEMBIC := $(UV) run alembic
UVICORN := $(UV) run uvicorn
CELERY := $(UV) run celery

.PHONY: help install dev run test lint format clean migration migrate worker up down seed flower

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  dev        Run development server (hot reload)"
	@echo "  run        Run application"
	@echo "  test       Run tests"
	@echo "  lint       Run linting"
	@echo "  format     Format code"
	@echo "  clean      Remove temporary files"
	@echo "  migration  Generate a new migration (usage: make migration MSG='message')"
	@echo "  migrate    Apply migrations"
	@echo "  worker     Run Celery worker"
	@echo "  up         Start docker services"
	@echo "  down       Stop docker services"
	@echo "  seed       Seed database with sample data"
	@echo "  flower     Start Flower monitoring (localhost:5555)"

install:
	$(UV) venv
	$(UV) pip install -e .[dev]

dev:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

run: dev

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

migration:
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate:
	$(ALEMBIC) upgrade head

worker:
	$(CELERY) -A app.core.celery_app worker --loglevel=info

up:
	docker-compose up -d

down:
	docker-compose down

seed:
	$(PYTHON) scripts/seed_db.py

emails:	
	$(PYTHON) scripts/trigger_emails.py

flower:
	docker compose up -d flower
