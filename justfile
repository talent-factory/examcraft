# ExamCraft AI Core — OSS Task Runner
#
# Prereqs:
#   just ≥ 1.18 (Homebrew: `brew install just`)
#   bash (Windows contributors: Git Bash or WSL — recipes are POSIX-shell)
#
# List all recipes grouped by category:  `just`

set dotenv-load
set shell := ["bash", "-uc"]
set positional-arguments

default:
    @just --list --unsorted

# ──────────────────────── Development ────────────────────────

# Start Core dev stack with Alembic migrations.
[group('Development')]
dev:
    #!/usr/bin/env bash
    set -euo pipefail

    # Pre-flight: docker daemon reachable?
    if ! docker info >/dev/null 2>&1; then
        echo "✖ Docker daemon is not running or not accessible." >&2
        echo "  Start Docker Desktop or 'sudo systemctl start docker'." >&2
        exit 1
    fi

    echo "▸ Starting ExamCraft AI Core"

    if [ ! -f .env ] && [ -f .env.example ]; then
        cp .env.example .env
        echo "▸ Created .env from .env.example — configure before production."
    fi

    docker compose down 2>/dev/null || true
    docker compose up -d --build

    # Health gate: api container actually running?
    echo "▸ Waiting for services…"
    sleep 5
    if ! docker compose ps --services --filter status=running | grep -q '^api$'; then
        echo "✖ api container is not running after startup." >&2
        echo "  Dumping last 60 log lines:" >&2
        docker compose logs api --tail=60 >&2 || true
        exit 1
    fi

    # Migration retry with per-attempt preamble
    for i in 1 2 3; do
        echo "▸ Running migrations (attempt $i/3)…"
        if docker compose exec -T api alembic upgrade head; then
            echo "▸ Migrations completed"
            break
        fi
        if [ "$i" -eq 3 ]; then
            echo "✖ Migrations failed after 3 attempts" >&2
            echo "  Tail of api logs:" >&2
            docker compose logs api --tail=40 >&2 || true
            exit 1
        fi
        sleep 3
    done

    echo ""
    echo "✓ ExamCraft AI Core is running:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"

[group('Development')]
stop:
    docker compose down

[group('Development')]
stop-volumes:
    docker compose down -v

# Seed dev data. Requires the stack to be running (just dev first).
[group('Development')]
seed:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! docker compose exec -T api echo ok >/dev/null 2>&1; then
        echo "✖ Core stack is not running." >&2
        echo "  Start it first:  just dev" >&2
        exit 1
    fi
    docker compose exec -T api python scripts/seed_dev_data.py
    echo ""
    echo "✓ Development data seeded."
    echo "  Admin login: admin@talent-factory.ch / admin123"

# ──────────────────────── Lint & Format ────────────────────────

[group('Lint & Format')]
lint: lint-backend lint-frontend

[group('Lint & Format')]
lint-backend:
    cd backend && ruff check .
    cd backend && ruff format --check .

[group('Lint & Format')]
lint-frontend:
    cd frontend && bun run lint || echo "ESLint warnings (non-blocking)"

[group('Lint & Format')]
lint-fix: lint-fix-backend lint-fix-frontend

[group('Lint & Format')]
lint-fix-backend:
    cd backend && ruff check . --fix
    cd backend && ruff format .

[group('Lint & Format')]
lint-fix-frontend:
    cd frontend && bun run lint:fix

# ──────────────────────── Testing ────────────────────────

[group('Testing')]
test: test-backend test-frontend

# Backend tests run locally via uv (no running container required).
[group('Testing')]
test-backend:
    uv run pytest backend/tests/ -v

[group('Testing')]
test-frontend:
    cd frontend && bun test -- --watchAll=false

# Run a single pytest file via uv.
# Example: just test-file backend/tests/test_auth_service.py
[group('Testing')]
test-file path:
    uv run pytest {{path}} -v

# Run a single pytest test function via uv.
# Example: just test-one backend/tests/test_auth_service.py::test_login
[group('Testing')]
test-one target:
    uv run pytest {{target}} -v

# ──────────────────────── E2E (Playwright) ────────────────────────

[group('E2E')]
e2e:
    cd frontend && bun run test:e2e

[group('E2E')]
e2e-ui:
    cd frontend && bun run test:e2e:ui

[group('E2E')]
e2e-headed:
    cd frontend && bun run test:e2e:headed

[group('E2E')]
e2e-debug:
    cd frontend && bun run test:e2e:debug

# ──────────────────────── Quality ────────────────────────

# Full CI check chain. Called by the pre-push git hook.
[group('Quality')]
ci-check:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "▸ Ruff lint (backend)…"
    (cd backend && ruff check .)

    echo "▸ Ruff format check (backend)…"
    (cd backend && ruff format --check .)

    # Strict ESLint: warnings still pass, but errors fail the recipe.
    # (The standalone `just lint-frontend` keeps the non-blocking behavior.)
    echo "▸ ESLint (frontend)…"
    (cd frontend && bun run lint)

    echo "▸ Backend tests…"
    uv run pytest backend/tests/ -v

    echo ""
    echo "✓ CI checks passed."

[group('Quality')]
pre-commit:
    pre-commit run --all-files

# ──────────────────────── Setup ────────────────────────

# Remove Python cache dirs/files. Permission errors are printed (not swallowed).
[group('Setup')]
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + || true
    find . -type f -name "*.pyc" -delete || true

[group('Setup')]
install:
    cd backend && uv pip install -r requirements.txt
    cd frontend && bun install

# Install pre-commit + pre-push hooks.
# --allow-missing-config: safe when the hook runs from a directory without a
# .pre-commit-config.yaml (e.g. a monorepo root that doesn't carry the config).
[group('Setup')]
install-hooks:
    pre-commit install --allow-missing-config
    pre-commit install --hook-type pre-push --allow-missing-config

[group('Setup')]
setup: install install-hooks
    @echo ""
    @echo "Setup complete. Next:"
    @echo "  1. cp .env.example .env   (if not done)"
    @echo "  2. Configure environment variables"
    @echo "  3. just dev"
