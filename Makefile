.PHONY: dev stop build test lint migrate keygen clean

# Start full stack (backend + frontend + postgres + redis)
dev:
	docker compose up --build

# Start in background
dev-bg:
	docker compose up --build -d

# Stop all services
stop:
	docker compose down

# Build images only
build:
	docker compose build

# Run all tests
test:
	$(MAKE) test-backend
	$(MAKE) test-python-sdk
	$(MAKE) test-ts-sdk

test-backend:
	cd backend && python -m pytest tests/ -v --tb=short

test-python-sdk:
	cd sdks/python && python -m pytest tests/ -v --tb=short

test-ts-sdk:
	cd sdks/typescript && npm test

# Lint everything
lint:
	cd backend && ruff check . && ruff format --check .
	cd sdks/python && ruff check . && ruff format --check .
	cd sdks/typescript && npm run lint
	cd frontend && npm run lint

# Format everything
fmt:
	cd backend && ruff format . && ruff check --fix .
	cd sdks/python && ruff format . && ruff check --fix .
	cd sdks/typescript && npm run format
	cd frontend && npm run format

# Run DB migrations
migrate:
	cd backend && alembic upgrade head

# Generate a new migration
migration:
	cd backend && alembic revision --autogenerate -m "$(name)"

# Generate RS256 key pair (run once on fresh setup)
keygen:
	cd backend && python -c "from app.services.jwt_service import generate_key_pair; generate_key_pair()"

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	cd sdks/typescript && rm -rf dist node_modules 2>/dev/null || true
	cd frontend && rm -rf .next node_modules 2>/dev/null || true

# Install all deps locally (no Docker)
install:
	cd backend && pip install -e ".[dev]"
	cd sdks/python && pip install -e ".[dev]"
	cd sdks/typescript && npm install
	cd frontend && npm install

# Quick local dev without Docker (sqlite mode)
local:
	cd backend && DATABASE_URL=sqlite:///./agentid.db uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

# Health check
health:
	curl -s http://localhost:8000/health | python3 -m json.tool
