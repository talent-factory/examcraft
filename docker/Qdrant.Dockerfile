# Qdrant Vector Database für Render.com Deployment
# Basiert auf offiziellem Qdrant Image

FROM qdrant/qdrant:latest

# Expose HTTP API Port (Render.com verwendet $PORT)
EXPOSE 6333

# Expose gRPC Port (optional)
EXPOSE 6334

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:6333/ || exit 1

# Qdrant startet automatisch mit dem Entrypoint des Base Images
# Keine CMD nötig, da das Base Image bereits konfiguriert ist
