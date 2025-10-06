#!/bin/bash
set -e

echo "🚀 Starting ExamCraft AI All-in-One Container..."

# PostgreSQL vorbereiten
echo "📊 Initializing PostgreSQL..."
mkdir -p /var/run/postgresql
chown -R postgres:postgres /var/run/postgresql
chmod 2777 /var/run/postgresql

# PostgreSQL Cluster initialisieren falls nötig
if [ ! -d "/var/lib/postgresql/15/main" ]; then
    echo "Creating PostgreSQL cluster..."
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/15/main"
fi

# Qdrant Storage vorbereiten
echo "🔍 Preparing Qdrant storage..."
mkdir -p /var/lib/qdrant/storage
chmod -R 755 /var/lib/qdrant

# Qdrant Config erstellen
cat > /app/docker/qdrant-config.yaml <<EOF
service:
  http_port: 6333
  grpc_port: 6334

storage:
  storage_path: /var/lib/qdrant/storage

log_level: INFO
EOF

# Environment Variables ausgeben (ohne Secrets)
echo "🔧 Environment Configuration:"
echo "  DATABASE_URL: ${DATABASE_URL:-postgresql://examcraft:examcraft_prod@localhost:5432/examcraft}"
echo "  REDIS_URL: ${REDIS_URL:-redis://localhost:6379}"
echo "  QDRANT_URL: ${QDRANT_URL:-http://localhost:6333}"
echo "  VECTOR_SERVICE_TYPE: ${VECTOR_SERVICE_TYPE:-qdrant}"
echo "  ENVIRONMENT: ${ENVIRONMENT:-production}"
echo "  CLAUDE_API_KEY: ${CLAUDE_API_KEY:+***configured***}"

# Warte kurz
sleep 2

# Supervisor starten (startet alle Services)
echo "🎯 Starting all services via Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

