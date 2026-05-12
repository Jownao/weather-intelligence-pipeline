.PHONY: help setup docker-build docker-up docker-down docker-logs test lint format clean

help:
	@echo "=== Weather Intelligence Pipeline ==="
	@echo ""
	@echo "Available commands:"
	@echo "  make setup              - Install dependencies locally"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start Airflow + PostgreSQL"
	@echo "  make docker-down        - Stop containers"
	@echo "  make docker-logs        - Show container logs"
	@echo "  make test               - Run unit tests"
	@echo "  make test-integration   - Run integration tests"
	@echo "  make lint               - Run linters (flake8, isort)"
	@echo "  make format             - Format code (black, isort)"
	@echo "  make clean              - Remove __pycache__, .pytest_cache"
	@echo ""

setup:
	pip install -r requirements.txt

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo ""
	@echo "✅ Airflow is running!"
	@echo "🌐 Access at: http://localhost:8080"
	@echo "👤 Default user: admin / admin"
	@echo ""

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

test:
	pytest tests/unit -v --cov=pipeline --cov-report=html

test-integration:
	pytest tests/integration -v

lint:
	flake8 pipeline dags tests --max-line-length=120
	isort --check-only pipeline dags tests

format:
	black pipeline dags tests
	isort pipeline dags tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
