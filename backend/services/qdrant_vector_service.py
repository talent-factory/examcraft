"""
Qdrant Vector Database Service für ExamCraft AI
Implementiert Qdrant Integration für Similarity Search und RAG
"""

import os
import logging
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

# Qdrant Client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# NumPy für Embeddings (immer benötigt)
import numpy as np

# Sentence Transformers für Embeddings (optional)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    import random

from services.docling_service import DocumentChunk, ProcessedDocument

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Ergebnis einer Similarity Search"""
    chunk_id: str
    document_id: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_index: int


@dataclass
class EmbeddingStats:
    """Statistiken über Embeddings"""
    total_chunks: int
    embedding_dimension: int
    model_name: str
    processing_time: float


def generate_point_id(document_id: int, chunk_index: int) -> str:
    """
    Generiere eine UUID für einen Qdrant Point basierend auf document_id und chunk_index

    Args:
        document_id: Document ID
        chunk_index: Chunk Index

    Returns:
        UUID String für Qdrant Point
    """
    # Erstelle deterministische UUID basierend auf document_id und chunk_index
    content = f"doc_{document_id}_chunk_{chunk_index}"
    hash_object = hashlib.md5(content.encode())
    # Konvertiere zu UUID Format
    hex_string = hash_object.hexdigest()
    uuid_string = f"{hex_string[:8]}-{hex_string[8:12]}-{hex_string[12:16]}-{hex_string[16:20]}-{hex_string[20:32]}"
    return uuid_string


class QdrantVectorService:
    """Service für Vector Database Operations mit Qdrant"""
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "examcraft_documents"
    ):
        """
        Initialisiere Qdrant Vector Service
        
        Args:
            qdrant_url: URL des Qdrant Servers
            embedding_model: Sentence Transformer Modell
            collection_name: Name der Qdrant Collection
        """
        self.qdrant_url = qdrant_url
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Initialisiere Qdrant Client (falls verfügbar)
        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(url=qdrant_url)
                logger.info(f"Qdrant client initialized successfully at {qdrant_url}")
            except Exception as e:
                logger.warning(f"Qdrant client initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Qdrant client not available - using fallback implementation")
        
        # Initialisiere Embedding Model (lazy loading)
        self._embedding_model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"QdrantVectorService initialized with model: {embedding_model}")
    
    @property
    def embedding_model(self):
        """Lazy loading des Embedding Models"""
        if self._embedding_model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading embedding model: {self.embedding_model_name}")
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._embedding_model = None
        
        return self._embedding_model
    
    def get_or_create_collection(self, collection_name: Optional[str] = None) -> str:
        """Hole oder erstelle Qdrant Collection"""
        name = collection_name or self.collection_name
        
        if not self.client:
            logger.warning("Qdrant client not available")
            return name
        
        try:
            # Prüfe ob Collection existiert
            collections = self.client.get_collections()
            collection_exists = any(col.name == name for col in collections.collections)
            
            if not collection_exists:
                # Erstelle neue Collection
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=384,  # Dimension für all-MiniLM-L6-v2
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created new collection: {name}")
            else:
                logger.info(f"Using existing collection: {name}")
            
            return name
        except Exception as e:
            logger.error(f"Failed to get/create collection {name}: {e}")
            return name
    
    async def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Erstelle Embeddings für Text-Liste (async)
        
        Args:
            texts: Liste von Texten
            
        Returns:
            NumPy Array mit Embeddings
        """
        if not texts:
            return np.array([])
        
        if not self.embedding_model:
            # Fallback: Mock Embeddings
            logger.warning("Using mock embeddings - embedding model not available")
            return np.array([[random.random() for _ in range(384)] for _ in texts])
        
        # Führe Embedding-Erstellung in Thread Pool aus (CPU-intensiv)
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self._executor,
            self.embedding_model.encode,
            texts
        )
        
        return embeddings
    
    async def add_document_chunks(
        self,
        processed_doc: ProcessedDocument,
        collection_name: Optional[str] = None
    ) -> EmbeddingStats:
        """
        Füge Document Chunks zur Qdrant Vector Database hinzu
        
        Args:
            processed_doc: Verarbeitetes Dokument mit Chunks
            collection_name: Optional spezifische Collection
            
        Returns:
            Statistiken über die Embedding-Erstellung
        """
        start_time = time.time()
        
        collection_name = self.get_or_create_collection(collection_name)
        
        if not self.client:
            logger.warning("Qdrant client not available - skipping vector storage")
            return EmbeddingStats(
                total_chunks=len(processed_doc.chunks),
                embedding_dimension=384,
                model_name=self.embedding_model_name,
                processing_time=0.1
            )
        
        # Extrahiere Texte und Metadaten
        texts = [chunk.content for chunk in processed_doc.chunks]
        
        # Erstelle Embeddings
        logger.info(f"Creating embeddings for {len(texts)} chunks")
        embeddings = await self.create_embeddings(texts)
        
        # Erstelle Points für Qdrant
        points = []
        for i, chunk in enumerate(processed_doc.chunks):
            chunk_id = generate_point_id(processed_doc.document_id, chunk.chunk_index)
            
            # Erstelle Metadaten
            metadata = {
                "document_id": processed_doc.document_id,
                "filename": processed_doc.filename,
                "mime_type": processed_doc.mime_type,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "word_count": len(chunk.content.split()),
                "content": chunk.content,  # Speichere Content in Payload
                **chunk.metadata,  # Zusätzliche Chunk-Metadaten
                **processed_doc.metadata  # Document-Metadaten
            }
            
            point = PointStruct(
                id=chunk_id,
                vector=embeddings[i].tolist(),
                payload=metadata
            )
            points.append(point)
        
        # Füge Points zur Collection hinzu
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Added {len(points)} points to Qdrant collection {collection_name}")
        except Exception as e:
            logger.error(f"Failed to add points to Qdrant: {e}")
            raise
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Added {len(texts)} chunks to Qdrant in {processing_time:.2f}s")
        
        return EmbeddingStats(
            total_chunks=len(texts),
            embedding_dimension=embeddings.shape[1] if len(embeddings) > 0 else 384,
            model_name=self.embedding_model_name,
            processing_time=processing_time
        )

    async def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        document_ids: Optional[List[int]] = None,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Führe Similarity Search durch

        Args:
            query: Suchquery
            n_results: Anzahl Ergebnisse
            document_ids: Optional Filter für spezifische Dokumente
            collection_name: Optional spezifische Collection

        Returns:
            Liste von SearchResult Objekten
        """
        collection_name = self.get_or_create_collection(collection_name)

        if not self.client:
            logger.warning("Qdrant client not available - returning empty results")
            return []

        # Erstelle Query Embedding
        query_embedding = await self.create_embeddings([query])
        if len(query_embedding) == 0:
            return []

        # Erstelle Filter für document_ids
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids)
                    )
                ]
            )

        try:
            # Führe Similarity Search durch
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding[0].tolist(),
                query_filter=query_filter,
                limit=n_results,
                with_payload=True
            )

            # Konvertiere zu SearchResult Objekten
            results = []
            for result in search_results:
                payload = result.payload

                search_result = SearchResult(
                    chunk_id=str(result.id),
                    document_id=payload["document_id"],
                    content=payload["content"],
                    similarity_score=result.score,
                    metadata=payload,
                    chunk_index=payload["chunk_index"]
                )
                results.append(search_result)

            logger.info(f"Similarity search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    async def get_document_chunks(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Hole alle Chunks eines spezifischen Dokuments

        Args:
            document_id: ID des Dokuments
            collection_name: Optional spezifische Collection

        Returns:
            Liste von SearchResult Objekten (sortiert nach chunk_index)
        """
        collection_name = self.get_or_create_collection(collection_name)

        if not self.client:
            logger.warning("Qdrant client not available - returning empty results")
            return []

        try:
            # Scroll durch alle Points mit dem spezifischen document_id
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )

            scroll_result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                with_payload=True,
                limit=1000  # Annahme: max 1000 chunks pro Dokument
            )

            # Konvertiere zu SearchResult Objekten
            search_results = []
            for point in scroll_result[0]:  # scroll_result ist (points, next_page_offset)
                payload = point.payload

                search_result = SearchResult(
                    chunk_id=str(point.id),
                    document_id=payload["document_id"],
                    content=payload["content"],
                    similarity_score=1.0,  # Kein Similarity Score bei direkter Abfrage
                    metadata=payload,
                    chunk_index=payload["chunk_index"]
                )
                search_results.append(search_result)

            # Sortiere nach chunk_index
            search_results.sort(key=lambda x: x.chunk_index)

            logger.info(f"Retrieved {len(search_results)} chunks for document {document_id}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to get document chunks: {e}")
            return []

    async def delete_document_chunks(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> int:
        """
        Lösche alle Chunks eines spezifischen Dokuments

        Args:
            document_id: ID des Dokuments
            collection_name: Optional spezifische Collection

        Returns:
            Anzahl gelöschter Chunks
        """
        collection_name = self.get_or_create_collection(collection_name)

        if not self.client:
            logger.warning("Qdrant client not available - cannot delete chunks")
            return 0

        try:
            # Erstelle Filter für document_id
            delete_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )

            # Hole zuerst die Anzahl der zu löschenden Points
            count_result = self.client.count(
                collection_name=collection_name,
                count_filter=delete_filter
            )
            deleted_count = count_result.count

            # Lösche Points
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=delete_filter)
            )

            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}")
            return 0

    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Hole Statistiken über die Collection

        Args:
            collection_name: Optional spezifische Collection

        Returns:
            Dictionary mit Collection-Statistiken
        """
        collection_name = self.get_or_create_collection(collection_name)

        if not self.client:
            return {
                "collection_name": collection_name,
                "total_chunks": 0,
                "embedding_model": self.embedding_model_name,
                "qdrant_url": self.qdrant_url
            }

        try:
            # Hole Collection Info - mit robuster Fehlerbehandlung
            try:
                collection_info = self.client.get_collection(collection_name)
                total_chunks = collection_info.points_count or 0
            except Exception as collection_error:
                # Fallback: Verwende count API direkt
                logger.warning(f"get_collection failed, using count API: {collection_error}")
                try:
                    count_result = self.client.count(collection_name=collection_name)
                    total_chunks = count_result.count if hasattr(count_result, 'count') else 0
                except Exception as count_error:
                    logger.warning(f"count API also failed: {count_error}")
                    total_chunks = 0

            stats = {
                "collection_name": collection_name,
                "total_chunks": total_chunks,
                "embedding_model": self.embedding_model_name,
                "qdrant_url": self.qdrant_url
            }

            if total_chunks > 0:
                # Hole Sample für zusätzliche Stats
                try:
                    scroll_result = self.client.scroll(
                        collection_name=collection_name,
                        limit=1,
                        with_payload=True
                    )

                    if scroll_result[0]:  # Wenn Points vorhanden
                        sample_payload = scroll_result[0][0].payload
                        stats["sample_document_id"] = sample_payload.get("document_id")
                        stats["sample_filename"] = sample_payload.get("filename")
                except Exception as e:
                    logger.warning(f"Failed to get sample data: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": collection_name,
                "total_chunks": 0,
                "embedding_model": self.embedding_model_name,
                "qdrant_url": self.qdrant_url,
                "error": str(e)
            }

    def reset_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Lösche alle Daten aus der Collection (für Tests/Development)

        Args:
            collection_name: Optional spezifische Collection

        Returns:
            True wenn erfolgreich
        """
        name = collection_name or self.collection_name

        if not self.client:
            logger.warning("Qdrant client not available - cannot reset collection")
            return False

        try:
            # Lösche Collection komplett und erstelle neu
            try:
                self.client.delete_collection(collection_name=name)
                logger.info(f"Deleted collection: {name}")
            except Exception:
                logger.info(f"Collection {name} did not exist")

            # Erstelle Collection neu
            self.get_or_create_collection(name)
            return True

        except Exception as e:
            logger.error(f"Failed to reset collection {name}: {e}")
            return False

    def __del__(self):
        """Cleanup beim Zerstören des Services"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


# Globale Service Instanz - wird durch Environment Variable konfiguriert
def create_vector_service() -> QdrantVectorService:
    """Factory function für Vector Service"""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantVectorService(qdrant_url=qdrant_url)


# Globale Service Instanz
vector_service = create_vector_service()
