"""
Reprocess documents that completed processing but never received vectors.

This typically affects DOCX uploads that hit the bug where python-docx's
`doc.paragraphs` extraction missed table/header/footer content (fixed in
this PR). Affected documents have `status=PROCESSED` and `has_vectors=False`.

Usage (inside the backend container):

    python scripts/reprocess_documents_without_vectors.py [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("reprocess")


async def reprocess(limit: int | None, dry_run: bool) -> int:
    from database import SessionLocal
    from models.document import Document, DocumentStatus
    from services.document_service import document_service

    db = SessionLocal()
    try:
        query = (
            db.query(Document)
            .filter(Document.status == DocumentStatus.PROCESSED)
            .filter((Document.has_vectors.is_(None)) | (Document.has_vectors == False))  # noqa: E712
            .order_by(Document.id)
        )
        if limit:
            query = query.limit(limit)

        targets = query.all()
        if not targets:
            logger.info(
                "No documents need reprocessing — all PROCESSED docs have vectors."
            )
            return 0

        logger.info("Found %d document(s) to reprocess", len(targets))
        for doc in targets:
            logger.info(
                "  - id=%s mime=%s name=%r",
                doc.id,
                doc.mime_type,
                doc.original_filename,
            )

        if dry_run:
            logger.info("Dry-run: not reprocessing.")
            return 0

        success, failure = 0, 0
        for doc in targets:
            try:
                logger.info("Reprocessing document id=%s ...", doc.id)
                result = await document_service.process_document_with_vectors(
                    doc.id, db
                )
                if result and not result.get("vector_embeddings", {}).get("error"):
                    success += 1
                    logger.info("  ✓ id=%s vectorized", doc.id)
                else:
                    failure += 1
                    logger.warning(
                        "  ✗ id=%s reprocess returned error: %s", doc.id, result
                    )
            except Exception:
                failure += 1
                logger.exception("  ✗ id=%s raised", doc.id)

        logger.info("Reprocess summary: %d ok, %d failed", success, failure)
        return 0 if failure == 0 else 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Cap number of docs")
    parser.add_argument("--dry-run", action="store_true", help="List but don't act")
    args = parser.parse_args()
    return asyncio.run(reprocess(args.limit, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
