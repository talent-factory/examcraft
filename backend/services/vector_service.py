"""
Vector Database Service für ExamCraft AI
Implementiert ChromaDB Integration für Similarity Search und RAG
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Temporäre Imports für Demo - ChromaDB wird später konfiguriert
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

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


class VectorService:
    """Service für Vector Database Operations mit ChromaDB"""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "examcraft_documents"
    ):
        """
        Initialisiere Vector Service
        
        Args:
            persist_directory: Verzeichnis für ChromaDB Persistierung
            embedding_model: Sentence Transformer Modell
            collection_name: Name der ChromaDB Collection
        """
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Erstelle Persist Directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialisiere ChromaDB Client (falls verfügbar)
        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB initialized successfully")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("ChromaDB not available - using mock implementation")
        
        # Initialisiere Embedding Model (lazy loading)
        self._embedding_model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Mock Storage für Demo (wenn ChromaDB nicht verfügbar)
        self._mock_storage = {}
        
        logger.info(f"VectorService initialized with model: {embedding_model}")
    
    @property
    def embedding_model(self):
        """Lazy loading des Embedding Models"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
            
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            try:
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self._embedding_model = None
        return self._embedding_model
    
    def get_or_create_collection(self, collection_name: Optional[str] = None) -> chromadb.Collection:
        """Hole oder erstelle ChromaDB Collection"""
        name = collection_name or self.collection_name
        
        try:
            collection = self.client.get_collection(name=name)
            logger.info(f"Using existing collection: {name}")
        except ValueError:
            # Collection existiert nicht, erstelle neue
            collection = self.client.create_collection(
                name=name,
                metadata={"description": "ExamCraft AI Document Embeddings"}
            )
            logger.info(f"Created new collection: {name}")
        
        return collection
    
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
        Füge Document Chunks zur Vector Database hinzu
        
        Args:
            processed_doc: Verarbeitetes Dokument mit Chunks
            collection_name: Optional spezifische Collection
            
        Returns:
            Statistiken über die Embedding-Erstellung
        """
        start_time = asyncio.get_event_loop().time()
        
        collection = self.get_or_create_collection(collection_name)
        
        # Extrahiere Texte und Metadaten
        texts = [chunk.content for chunk in processed_doc.chunks]
        chunk_ids = [
            f"doc_{processed_doc.document_id}_chunk_{chunk.chunk_index}"
            for chunk in processed_doc.chunks
        ]
        
        # Erstelle Metadaten für jeden Chunk
        metadatas = []
        for chunk in processed_doc.chunks:
            metadata = {
                "document_id": processed_doc.document_id,
                "filename": processed_doc.filename,
                "mime_type": processed_doc.mime_type,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "word_count": len(chunk.content.split()),
                **chunk.metadata,  # Zusätzliche Chunk-Metadaten
                **processed_doc.metadata  # Document-Metadaten
            }
            metadatas.append(metadata)
        
        # Erstelle Embeddings
        logger.info(f"Creating embeddings for {len(texts)} chunks")
        embeddings = await self.create_embeddings(texts)
        
        # Füge zur Collection hinzu
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        logger.info(f"Added {len(texts)} chunks to vector database in {processing_time:.2f}s")
        
        return EmbeddingStats(
            total_chunks=len(texts),
            embedding_dimension=embeddings.shape[1] if len(embeddings) > 0 else 0,
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
        collection = self.get_or_create_collection(collection_name)
        
        # Erstelle Query Embedding
        query_embedding = await self.create_embeddings([query])
        
        # Erstelle Where-Filter für document_ids
        where_filter = None
        if document_ids:
            where_filter = {"document_id": {"$in": document_ids}}
        
        # Führe Similarity Search durch
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Konvertiere zu SearchResult Objekten
        search_results = []
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            document = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            
            # Konvertiere Distance zu Similarity Score (1 - distance)
            similarity_score = 1.0 - distance
            
            search_result = SearchResult(
                chunk_id=chunk_id,
                document_id=metadata["document_id"],
                content=document,
                similarity_score=similarity_score,
                metadata=metadata,
                chunk_index=metadata["chunk_index"]
            )
            search_results.append(search_result)
        
        logger.info(f"Similarity search returned {len(search_results)} results")
        return search_results
    
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
        collection = self.get_or_create_collection(collection_name)
        
        # Query für spezifisches Dokument
        results = collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        
        # Konvertiere zu SearchResult Objekten
        search_results = []
        for i in range(len(results["ids"])):
            chunk_id = results["ids"][i]
            document = results["documents"][i]
            metadata = results["metadatas"][i]
            
            search_result = SearchResult(
                chunk_id=chunk_id,
                document_id=metadata["document_id"],
                content=document,
                similarity_score=1.0,  # Kein Similarity Score bei direkter Abfrage
                metadata=metadata,
                chunk_index=metadata["chunk_index"]
            )
            search_results.append(search_result)
        
        # Sortiere nach chunk_index
        search_results.sort(key=lambda x: x.chunk_index)
        
        logger.info(f"Retrieved {len(search_results)} chunks for document {document_id}")
        return search_results
    
    async def delete_document_chunks(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> int:
        """
        Lösche alle Chunks eines Dokuments aus der Vector Database
        
        Args:
            document_id: ID des Dokuments
            collection_name: Optional spezifische Collection
            
        Returns:
            Anzahl gelöschter Chunks
        """
        collection = self.get_or_create_collection(collection_name)
        
        # Finde alle Chunk-IDs für das Dokument
        results = collection.get(
            where={"document_id": document_id},
            include=["documents"]
        )
        
        chunk_ids = results["ids"]
        
        if chunk_ids:
            # Lösche Chunks
            collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks for document {document_id}")
        
        return len(chunk_ids)
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Hole Statistiken über die Collection
        
        Args:
            collection_name: Optional spezifische Collection
            
        Returns:
            Dictionary mit Collection-Statistiken
        """
        collection = self.get_or_create_collection(collection_name)
        
        # Hole Collection Info
        count = collection.count()
        
        stats = {
            "collection_name": collection.name,
            "total_chunks": count,
            "embedding_model": self.embedding_model_name,
            "persist_directory": self.persist_directory
        }
        
        if count > 0:
            # Hole Sample für zusätzliche Stats
            sample = collection.peek(limit=1)
            if sample["metadatas"]:
                sample_metadata = sample["metadatas"][0]
                stats["sample_document_id"] = sample_metadata.get("document_id")
                stats["sample_filename"] = sample_metadata.get("filename")
        
        return stats
    
    def reset_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Lösche alle Daten aus der Collection (für Tests/Development)
        
        Args:
            collection_name: Optional spezifische Collection
            
        Returns:
            True wenn erfolgreich
        """
        name = collection_name or self.collection_name
        
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
            return True
        except ValueError:
            logger.info(f"Collection {name} did not exist")
            return True
    
    def __del__(self):
        """Cleanup beim Zerstören des Services"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


# Globale Service Instanz
vector_service = VectorService()
