# ExamCraft AI - Development Makefile
# Praktische Shortcuts für häufige Entwicklungsaufgaben

.PHONY: help lint lint-fix test test-backend test-frontend pre-commit install-hooks ci-check
.PHONY: e2e e2e-ui e2e-headed e2e-debug e2e-setup
.PHONY: deploy deploy-backend deploy-frontend deploy-all deploy-status deploy-logs

# Default target
help:
	@echo "ExamCraft AI - Development Commands"
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
	@echo "  make e2e-setup     - Setup test data for E2E tests"
	@echo ""
	@echo "Quality Checks:"
	@echo "  make ci-check      - Run all CI checks locally (before push)"
	@echo "  make pre-commit    - Run all pre-commit hooks"
	@echo "  make install-hooks - Install pre-commit & pre-push hooks"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start development environment"
	@echo "  make dev-core      - Start Core deployment"
	@echo "  make dev-full      - Start Full deployment"
	@echo ""
	@echo "Fly.io Deployment:"
	@echo "  make deploy        - Deploy Backend + Frontend to Fly.io"
	@echo "  make deploy-all    - Deploy ALL services (Backend, Frontend, Qdrant, RabbitMQ, Celery)"
	@echo "  make deploy-backend  - Deploy Backend only"
	@echo "  make deploy-frontend - Deploy Frontend only"
	@echo "  make deploy-qdrant   - Deploy Qdrant vector database"
	@echo "  make deploy-rabbitmq - Deploy RabbitMQ message broker"
	@echo "  make deploy-celery   - Deploy Celery worker"
	@echo "  make deploy-flower   - Deploy Flower monitoring dashboard"
	@echo "  make deploy-status   - Show status of all Fly.io apps"
	@echo "  make deploy-logs     - Show logs from Backend app"
	@echo ""

# Lint Commands
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting Backend..."
	cd packages/core/backend && ruff check .
	cd packages/core/backend && ruff format --check .

lint-frontend:
	@echo "🔍 Linting Frontend..."
	cd packages/core/frontend && bun run lint || echo "⚠️  ESLint warnings found (non-blocking)"

lint-fix: lint-fix-backend lint-fix-frontend

lint-fix-backend:
	@echo "🔧 Auto-fixing Backend..."
	cd packages/core/backend && ruff check . --fix
	cd packages/core/backend && ruff format .

lint-fix-frontend:
	@echo "🔧 Auto-fixing Frontend..."
	cd packages/core/frontend && bun run lint:fix

# Test Commands
test: test-backend test-frontend

test-backend:
	@echo "🧪 Running Backend Tests..."
	uv run pytest packages/core/backend/tests/ -v

test-frontend:
	@echo "🧪 Running Frontend Tests..."
	cd packages/core/frontend && bun test -- --watchAll=false

# E2E Test Commands (Playwright)
e2e:
	@echo "🎭 Running E2E Tests..."
	cd packages/core/frontend && bun run test:e2e

e2e-ui:
	@echo "🎭 Running E2E Tests with UI..."
	cd packages/core/frontend && bun run test:e2e:ui

e2e-headed:
	@echo "🎭 Running E2E Tests (Headed)..."
	cd packages/core/frontend && bun run test:e2e:headed

e2e-debug:
	@echo "🎭 Running E2E Tests (Debug)..."
	cd packages/core/frontend && bun run test:e2e:debug

e2e-setup:
	@echo "📦 Setting up E2E Test Data..."
	@echo "💡 Requires: docker compose up -d postgres (or local PostgreSQL)"
	DATABASE_URL=postgresql://examcraft:examcraft_dev@localhost:5432/examcraft uv run python packages/core/backend/scripts/setup_e2e_test_data.py  # pragma: allowlist secret

# Pre-Commit Hooks
pre-commit:
	@echo "🔧 Running Pre-Commit Hooks..."
	pre-commit run --all-files

install-hooks:
	@echo "📦 Installing Pre-Commit & Pre-Push Hooks..."
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "✅ Hooks installed!"
	@echo "💡 Pre-commit: Runs on every commit"
	@echo "💡 Pre-push: Runs comprehensive checks before push"

# CI-Check (simulate what CI does)
ci-check:
	@echo "🔍 Running CI Checks locally..."
	@bash scripts/pre-push-lint-check.sh

# Development Environment
dev:
	@echo "🚀 Starting Development Environment (Auto-detect)..."
	./start-dev.sh

dev-core:
	@echo "🚀 Starting Core Deployment..."
	./start-dev.sh --core

dev-full:
	@echo "🚀 Starting Full Deployment..."
	./start-dev.sh --full

# Pre-Push Check (manual)
pre-push:
	@echo "🔍 Running Pre-Push Lint Checks..."
	bash scripts/pre-push-lint-check.sh

# Clean
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Install Dependencies
install:
	@echo "📦 Installing Dependencies..."
	cd packages/core/backend && uv pip install -r requirements.txt
	cd packages/core/frontend && bun install
	@echo "✅ Dependencies installed!"

# Full Setup (for new developers)
setup: install install-hooks
	@echo ""
	@echo "✅ Setup Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make dev' to start development environment"
	@echo "  3. Run 'make lint' before committing"
	@echo ""

# =============================================================================
# Fly.io Deployment Commands
# =============================================================================

# Deploy Backend + Frontend (most common)
deploy: deploy-backend deploy-frontend
	@echo "✅ Core services deployed!"

# Deploy all services
deploy-all: deploy-backend deploy-frontend deploy-qdrant deploy-rabbitmq deploy-celery deploy-flower
	@echo "✅ All services deployed!"

# GitHub token for private dependency access (subscribeflow SDK)
GITHUB_TOKEN ?= $(shell gh auth token 2>/dev/null)

# Individual service deployments
deploy-backend:
	@echo "🚀 Deploying Backend to Fly.io..."
	fly deploy --config fly.toml --build-secret "GITHUB_TOKEN=$(GITHUB_TOKEN)"

deploy-frontend:
	@echo "🚀 Deploying Frontend to Fly.io..."
	fly deploy --config fly.frontend.toml

deploy-qdrant:
	@echo "🚀 Deploying Qdrant to Fly.io..."
	fly deploy --config fly.qdrant.toml

deploy-rabbitmq:
	@echo "🚀 Deploying RabbitMQ to Fly.io..."
	fly deploy --config fly.rabbitmq.toml

deploy-celery:
	@echo "🚀 Deploying Celery Worker to Fly.io..."
	fly deploy --config fly.celery.toml --build-secret "GITHUB_TOKEN=$(GITHUB_TOKEN)"

deploy-flower:
	@echo "🚀 Deploying Flower Dashboard to Fly.io..."
	fly deploy --config fly.flower.toml

# Status and monitoring
deploy-status:
	@echo "📊 Fly.io App Status"
	@echo ""
	@echo "=== Backend (examcraft-api) ==="
	@fly status -a examcraft-api 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Frontend (examcraft-web) ==="
	@fly status -a examcraft-web 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Database (examcraft-db) ==="
	@fly status -a examcraft-db 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Qdrant (examcraft-qdrant) ==="
	@fly status -a examcraft-qdrant 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== RabbitMQ (examcraft-rabbitmq) ==="
	@fly status -a examcraft-rabbitmq 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Celery (examcraft-celery) ==="
	@fly status -a examcraft-celery 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Flower (examcraft-flower) ==="
	@fly status -a examcraft-flower 2>/dev/null || echo "  Not deployed"

deploy-logs:
	@echo "📜 Backend Logs (examcraft-api)"
	fly logs -a examcraft-api

deploy-logs-frontend:
	@echo "📜 Frontend Logs (examcraft-web)"
	fly logs -a examcraft-web

# Database access helper
db-proxy:
	@echo "🔌 Starting database proxy on localhost:5432..."
	@echo "   Connect with: psql -h localhost -p 5432 -U flypgadmin -d examcraft_api"
	fly proxy 5432 -a examcraft-db

db-connect:
	@echo "🔌 Connecting to database..."
	fly postgres connect -a examcraft-db
