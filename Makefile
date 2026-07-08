.PHONY: help install dev lint fmt type test cov run export-reqs deploy clean

help:
	@echo "install     Install runtime deps"
	@echo "dev         Install dev deps + pre-commit hooks"
	@echo "lint        Ruff lint"
	@echo "fmt         Ruff format"
	@echo "type        Mypy type-check"
	@echo "test        Run pytest"
	@echo "run         Run the Streamlit app locally"
	@echo "export-reqs Export requirements.txt from the lock for Databricks Apps"
	@echo "deploy      Deploy the Databricks Asset Bundle"

install:
	uv sync

dev:
	uv sync --extra dev
	uv run pre-commit install

lint:
	uv run ruff check src tests

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

type:
	uv run mypy

test:
	uv run pytest

run:
	uv run streamlit run app.py

export-reqs:
	uv export --no-dev --format requirements-txt > requirements.txt

deploy:
	databricks bundle deploy

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov build dist
