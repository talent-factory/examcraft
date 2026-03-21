#!/bin/bash
set -e

# ============================================================================
# ExamCraft AI Backend - Docker Entrypoint
# Handles database migrations before application startup
# ============================================================================

# Fix postgres:// to postgresql:// (required by SQLAlchemy)
if [[ "$DATABASE_URL" == postgres://* ]]; then
    export DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql:\/\/}"
    echo "Converted DATABASE_URL scheme to postgresql://"
fi

echo "============================================"
echo "ExamCraft AI Backend - Starting..."
echo "Environment: ${ENVIRONMENT:-production}"
echo "Deployment Mode: ${DEPLOYMENT_MODE:-core}"
echo "============================================"

echo "Waiting for database to be ready..."
MAX_RETRIES=15
RETRY_INTERVAL=3

for i in $(seq 1 $MAX_RETRIES); do
    echo "Migration attempt $i/$MAX_RETRIES..."
    if alembic upgrade head; then
        echo "✓ Migrations completed successfully!"
        break
    fi

    if [ $i -eq $MAX_RETRIES ]; then
        echo "✗ Failed to run migrations after $MAX_RETRIES attempts"
        exit 1
    fi

    echo "Migration failed, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

# One-time data enrichment: add bloom_level + estimated_time to existing questions
if [ -n "$ANTHROPIC_API_KEY" ] && [ -f "scripts/enrich_question_metadata.py" ]; then
    echo "Running question metadata enrichment..."
    python scripts/enrich_question_metadata.py || echo "⚠ Enrichment failed (non-fatal), continuing startup..."
fi

echo "Starting application..."
exec "$@"
