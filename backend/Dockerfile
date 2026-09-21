# TF-865: specula-client-python requires Python >=3.12 (its pyproject.toml);
# python:3.11-slim built without error (the optional install step is a no-op
# without a GITHUB_TOKEN secret, see below) but failed at install time once a
# real token was used -- "Package 'specula-client' requires a different
# Python: 3.11.16 not in '>=3.12'", verified empirically. Matches
# Dockerfile.fly, which was already on python:3.12-slim.
FROM python:3.12-slim

WORKDIR /app

# Build arguments
ARG BUILD_TIMESTAMP
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Install system dependencies
# Note: PyMuPDF (fitz) requires mupdf libraries for PDF processing.
# Tesseract (+ deu/eng) enables PyMuPDF OCR for scanned PDFs (TF-360).
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    libpq-dev \
    python3-dev \
    libmagic1 \
    libmupdf-dev \
    mupdf \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Tesseract tessdata für PyMuPDF-OCR (TF-360). PyMuPDFs get_textpage_ocr
# verlangt eine gesetzte TESSDATA_PREFIX. Pfad ist nach Tesseract-Major-
# Version versioniert (aktuell 5.x), nicht nach Debian-Codename -- blieb
# beim TF-865-Wechsel von python:3.11-slim (Debian Bookworm) auf
# python:3.12-slim (inzwischen Debian Trixie) unverändert korrekt, empirisch
# im gebauten Image verifiziert. Bei abweichender Tesseract-Major-Version
# anpassen.
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Copy requirements and pyproject.toml first for better caching
COPY backend/requirements.txt .
COPY pyproject.toml /app/pyproject.toml

# Install Python dependencies. requirements.txt itself needs no credentials
# at all (see its own comment on why specula-client isn't listed there) --
# this succeeds unconditionally for a public/OSS build.
RUN pip install --no-cache-dir -r requirements.txt

# Optional: TF-865 observability (specula-client, private repo, not on PyPI
# yet, see requirements.txt). Only attempted when a GITHUB_TOKEN build secret
# is supplied (private/full builds, see core/docker-compose.yml /
# docker-compose.full.yml's `secrets: - GITHUB_TOKEN`); silently skipped
# otherwise -- config/observability.py and middleware/observability_context.py
# degrade to a fully functional, tracing-less no-op when the package isn't
# importable, so a build without this secret is a working image, not a
# broken one.
#
# `-s` (not `-f`): BuildKit still mounts an EMPTY file at
# /run/secrets/GITHUB_TOKEN when the `GITHUB_TOKEN` env var is unset --
# `-f` alone would be true for that empty file too, attempting an anonymous
# `https://@github.com/...` clone of a private repo (guaranteed to fail).
# `-s` requires the file to be non-empty.
#
# The token is embedded directly in the pip install URL argument, not
# written to disk via `git config --global` -- nothing to clean up
# afterwards, and no risk of it persisting in a shipped image layer.
RUN --mount=type=secret,id=GITHUB_TOKEN \
    if [ -s /run/secrets/GITHUB_TOKEN ]; then \
        GITHUB_TOKEN=$(cat /run/secrets/GITHUB_TOKEN) && \
        pip install --no-cache-dir "specula-client[fastapi,celery] @ git+https://${GITHUB_TOKEN}@github.com/talent-factory/specula-client-python.git@v0.1.0"; \
    fi

# Install additional dependencies from pyproject.toml (qdrant-client, sentence-transformers, etc.)
RUN pip install --no-cache-dir -e .

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
