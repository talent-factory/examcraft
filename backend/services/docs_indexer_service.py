import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DOCS_SITE_PATH = os.environ.get("DOCS_SITE_PATH", "core/docs-site/docs")

# Redis SETNX key + TTL for the indexing lock. 15 min is well above the
# realistic worst case (sentence-transformers cold-load plus full re-index
# of the corpus); if exceeded, the key expires and the next attempt proceeds.
_LOCK_KEY = "docs_help:indexing_lock"
_LOCK_TTL_SECONDS = 15 * 60


class IndexingInProgressError(RuntimeError):
    """Raised when another indexing run (startup task or admin call) holds the lock."""


class DocsIndexerService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _acquire_lock() -> bool:
        """SETNX on Redis. Returns True if lock was acquired.

        Falls back to True (skip locking) when Redis is unavailable — better
        to allow a potentially-concurrent run than to refuse indexing entirely.
        """
        try:
            from services.redis_service import RedisService

            client = RedisService.get_ratelimit_client()
            return bool(client.set(_LOCK_KEY, "1", nx=True, ex=_LOCK_TTL_SECONDS))
        except Exception as e:
            logger.warning(f"Redis unreachable, proceeding without lock: {e}")
            return True

    @staticmethod
    def _release_lock() -> None:
        try:
            from services.redis_service import RedisService

            RedisService.get_ratelimit_client().delete(_LOCK_KEY)
        except Exception as e:
            logger.warning(f"Redis lock release failed: {e}")

    async def run_index(self, full_scan: bool = False) -> Dict[str, int]:
        """Serialize indexing via Redis SETNX lock; raises IndexingInProgressError on conflict."""
        if not self._acquire_lock():
            raise IndexingInProgressError(
                "Docs indexing is already in progress "
                "(startup task or another admin call holds the Redis lock)."
            )

        try:
            return await self._run_index_locked(full_scan=full_scan)
        finally:
            self._release_lock()

    async def _run_index_locked(self, full_scan: bool) -> Dict[str, int]:
        from models.help import HelpIndexState

        state = self.db.query(HelpIndexState).first()
        if not state:
            state = HelpIndexState()
            self.db.add(state)
            self.db.commit()
            full_scan = True

        # Ensure the docs_help collection exists before any indexing.
        # Let failures propagate — returning {indexed: 0} looked like success
        # in the caller (print "✅ Docs indexed: 0 files") and hid real errors.
        self._ensure_collection()

        if full_scan:
            # Full Replace: clear entire collection before re-indexing.
            # Clear-failure must abort (not return 0) so caller sees the error.
            self._clear_collection()
            changed = self._get_all_md_files()
            deleted = []
        elif not full_scan and state.last_indexed_sha:
            changed, deleted = self._get_changed_files(state.last_indexed_sha)
        else:
            changed = self._get_all_md_files()
            deleted = []

        indexed = 0
        for filepath in changed:
            if await self._index_file(filepath):
                indexed += 1

        deleted_count = 0
        for filepath in deleted:
            await self._remove_file_from_index(filepath)
            deleted_count += 1

        current_sha = self._get_current_sha()
        state.last_indexed_sha = current_sha
        state.last_indexed_at = datetime.now(timezone.utc)
        state.files_indexed = indexed
        state.files_deleted = deleted_count
        self.db.commit()

        self._invalidate_stale_faq_cache(changed + deleted)

        logger.info(f"Indexing complete: {indexed} indexed, {deleted_count} deleted")
        return {"indexed": indexed, "deleted": deleted_count}

    def _ensure_collection(self) -> None:
        """Create the docs_help collection if it doesn't exist."""
        from services.vector_service_factory import vector_service

        if not hasattr(vector_service, "client") or vector_service.client is None:
            return

        if hasattr(vector_service, "get_or_create_collection"):
            vector_service.get_or_create_collection("docs_help")
            logger.info("Ensured docs_help collection exists")
        else:
            # Fallback: create manually if vector_service lacks the method
            from qdrant_client.http.models import VectorParams, Distance

            collections = vector_service.client.get_collections()
            if not any(c.name == "docs_help" for c in collections.collections):
                embedding_dim = 384  # Default for sentence-transformers
                vector_service.client.create_collection(
                    collection_name="docs_help",
                    vectors_config=VectorParams(
                        size=embedding_dim, distance=Distance.COSINE
                    ),
                )
                logger.info("Created docs_help collection (384 dim, cosine)")

    def _clear_collection(self) -> None:
        """Delete all points from the docs_help collection (Full Replace strategy)."""
        from services.vector_service_factory import vector_service
        from qdrant_client.http import models

        if not hasattr(vector_service, "client") or vector_service.client is None:
            logger.warning("Qdrant not available, skipping collection clear")
            return

        vector_service.client.delete(
            collection_name="docs_help",
            points_selector=models.FilterSelector(filter=models.Filter(must=[])),
        )
        logger.info("Cleared docs_help collection for full re-index")

    def _get_all_md_files(self) -> List[str]:
        md_files = []
        for root, _, files in os.walk(DOCS_SITE_PATH):
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))
        return md_files

    def _get_changed_files(self, last_sha: str) -> Tuple[List[str], List[str]]:
        # Defensive: guards against None and any other non-string sentinel.
        # The regex below would raise TypeError on None rather than returning
        # no match, masking the real issue behind a generic exception.
        if not last_sha or not isinstance(last_sha, str):
            logger.warning("No valid last_sha provided, falling back to full scan")
            return self._get_all_md_files(), []
        if not re.match(r"^[0-9a-f]{40}$", last_sha):
            logger.warning(f"Invalid SHA format: {last_sha}, falling back to full scan")
            return self._get_all_md_files(), []
        try:
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-status",
                    f"{last_sha}..HEAD",
                    "--",
                    DOCS_SITE_PATH,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            changed, deleted = [], []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                status, filepath = parts[0], parts[-1]
                if status.startswith("D"):
                    deleted.append(filepath)
                else:
                    changed.append(filepath)
            return changed, deleted
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            # FileNotFoundError: git binary not on PATH (possible in minimal
            # container images); OSError: broader subprocess spawn failures.
            logger.warning(
                f"Git diff failed ({type(e).__name__}), falling back to full scan"
            )
            return self._get_all_md_files(), []

    def _get_current_sha(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            logger.warning(f"Could not determine current git SHA ({type(e).__name__})")
            return None

    def _parse_markdown(
        self, content: str, filepath: str, language: str
    ) -> List[Dict[str, Any]]:
        chunks = []
        current_section = (
            os.path.basename(filepath).replace(".md", "").replace(".en", "")
        )
        current_content: List[str] = []

        for line in content.split("\n"):
            heading_match = re.match(r"^(#{1,3})\s+(.+)", line)
            if heading_match:
                if current_content:
                    text = "\n".join(current_content).strip()
                    if len(text) > 20:
                        chunks.append(
                            {
                                "source_file": filepath,
                                "section_title": current_section,
                                "content": text[:2000],
                                "language": language,
                            }
                        )
                current_section = heading_match.group(2)
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            text = "\n".join(current_content).strip()
            if len(text) > 20:
                chunks.append(
                    {
                        "source_file": filepath,
                        "section_title": current_section,
                        "content": text[:2000],
                        "language": language,
                    }
                )

        return chunks

    def _detect_language(self, filepath: str) -> str:
        if ".en." in os.path.basename(filepath):
            return "en"
        return "de"

    async def _index_file(self, filepath: str) -> bool:
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return False

        language = self._detect_language(filepath)
        chunks = self._parse_markdown(content, filepath, language)
        await self._remove_file_from_index(filepath)

        try:
            from services.vector_service_factory import vector_service
            from qdrant_client.http.models import PointStruct
            import uuid

            if not hasattr(vector_service, "client") or vector_service.client is None:
                logger.warning("Qdrant not available, skipping indexing")
                return False

            texts = [chunk["content"] for chunk in chunks]
            embeddings = await vector_service.create_embeddings(texts)

            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embeddings[i].tolist(),
                    payload={
                        "source_file": chunk["source_file"],
                        "section_title": chunk["section_title"],
                        "language": chunk["language"],
                        "content_preview": chunk["content"][:500],
                    },
                )
                for i, chunk in enumerate(chunks)
            ]
            vector_service.client.upsert(collection_name="docs_help", points=points)
            return True
        except Exception as e:
            logger.error(f"Failed to index {filepath}: {e}")
            return False

    async def _remove_file_from_index(self, filepath: str) -> None:
        try:
            from services.vector_service_factory import vector_service
            from qdrant_client.http import models

            if not hasattr(vector_service, "client") or vector_service.client is None:
                return

            vector_service.client.delete(
                collection_name="docs_help",
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="source_file",
                                match=models.MatchValue(value=filepath),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Failed to remove {filepath} from index: {e}")

    def _invalidate_stale_faq_cache(self, changed_files: List[str]) -> None:
        if not changed_files:
            return
        from models.help import HelpFaqCache

        entries = (
            self.db.query(HelpFaqCache).filter(HelpFaqCache.stale.is_(False)).all()
        )
        for entry in entries:
            if any(f in (entry.source_files or []) for f in changed_files):
                entry.stale = True
        self.db.commit()
