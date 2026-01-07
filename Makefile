# ExamCraft AI - Development Makefile
# Praktische Shortcuts für häufige Entwicklungsaufgaben

.PHONY: help lint lint-fix test test-backend test-frontend pre-commit install-hooks

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
	@echo "Pre-Commit:"
	@echo "  make pre-commit    - Run all pre-commit hooks"
	@echo "  make install-hooks - Install pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start development environment"
	@echo "  make dev-core      - Start Core deployment"
	@echo "  make dev-full      - Start Full deployment"
	@echo ""

# Lint Commands
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting Backend..."
	cd packages/core/backend && ruff check .
	cd packages/core/backend && ruff format --check .

lint-frontend:
	@echo "🔍 Linting Frontend..."
	cd packages/core/frontend && npm run lint

lint-fix: lint-fix-backend lint-fix-frontend

lint-fix-backend:
	@echo "🔧 Auto-fixing Backend..."
	cd packages/core/backend && ruff check . --fix
	cd packages/core/backend && ruff format .

lint-fix-frontend:
	@echo "🔧 Auto-fixing Frontend..."
	cd packages/core/frontend && npm run lint:fix

# Test Commands
test: test-backend test-frontend

test-backend:
	@echo "🧪 Running Backend Tests..."
	cd packages/core/backend && pytest tests/ -v

test-frontend:
	@echo "🧪 Running Frontend Tests..."
	cd packages/core/frontend && npm test -- --watchAll=false

# Pre-Commit Hooks
pre-commit:
	@echo "🔧 Running Pre-Commit Hooks..."
	pre-commit run --all-files

install-hooks:
	@echo "📦 Installing Pre-Commit Hooks..."
	pre-commit install
	@echo "✅ Pre-Commit Hooks installed!"
	@echo "💡 Hooks will run automatically on every commit"

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
	cd packages/core/backend && pip install -r requirements.txt
	cd packages/core/frontend && npm install
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
