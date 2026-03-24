# ExamCraft AI - Development Makefile (Open Source)

.PHONY: help dev stop lint lint-fix test test-backend test-frontend
.PHONY: e2e e2e-ui e2e-headed e2e-debug
.PHONY: pre-commit install-hooks ci-check clean install setup seed

help:
	@echo "ExamCraft AI - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start development environment"
	@echo "  make stop          - Stop all services"
	@echo "  make stop-volumes  - Stop and remove volumes"
	@echo "  make seed          - Seed development data"
	@echo ""
	@echo "Lint & Format:"
	@echo "  make lint          - Run all linters (Backend + Frontend)"
	@echo "  make lint-fix      - Auto-fix all lint errors"
	@echo "  make lint-backend  - Lint Backend only"
	@echo "  make lint-frontend - Lint Frontend only"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run Backend tests"
	@echo "  make test-frontend - Run Frontend tests"
	@echo ""
	@echo "E2E Testing (Playwright):"
	@echo "  make e2e           - Run all E2E tests"
	@echo "  make e2e-ui        - Run E2E tests with interactive UI"
	@echo "  make e2e-headed    - Run E2E tests with visible browser"
	@echo "  make e2e-debug     - Run E2E tests in debug mode"
	@echo ""
	@echo "Quality Checks:"
	@echo "  make ci-check      - Run all CI checks locally"
	@echo "  make pre-commit    - Run all pre-commit hooks"
	@echo "  make install-hooks - Install pre-commit & pre-push hooks"
	@echo ""

# Development
dev:
	docker compose up -d --build
	@echo ""
	@echo "ExamCraft AI Core is running!"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

stop:
	docker compose down

stop-volumes:
	docker compose down -v

seed:
	docker compose exec api python scripts/seed_dev_data.py

# Lint
lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check .
	cd backend && ruff format --check .

lint-frontend:
	cd frontend && bun run lint || echo "ESLint warnings found (non-blocking)"

lint-fix: lint-fix-backend lint-fix-frontend

lint-fix-backend:
	cd backend && ruff check . --fix
	cd backend && ruff format .

lint-fix-frontend:
	cd frontend && bun run lint:fix

# Tests
test: test-backend test-frontend

test-backend:
	uv run pytest backend/tests/ -v

test-frontend:
	cd frontend && bun test -- --watchAll=false

# E2E
e2e:
	cd frontend && bun run test:e2e

e2e-ui:
	cd frontend && bun run test:e2e:ui

e2e-headed:
	cd frontend && bun run test:e2e:headed

e2e-debug:
	cd frontend && bun run test:e2e:debug

# Quality
pre-commit:
	pre-commit run --all-files

install-hooks:
	pre-commit install
	pre-commit install --hook-type pre-push

ci-check:
	@bash scripts/pre-push-lint-check.sh

# Clean & Install
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

install:
	cd backend && uv pip install -r requirements.txt
	cd frontend && bun install

setup: install install-hooks
	@echo ""
	@echo "Setup complete. Next steps:"
	@echo "  1. cp .env.example .env"
	@echo "  2. Configure environment variables"
	@echo "  3. make dev"
