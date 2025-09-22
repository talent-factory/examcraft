"""
Mock Vector Service für ExamCraft AI Demo
Simuliert ChromaDB Funktionalität ohne externe Dependencies
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import json
import random
import time

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
    """Mock Vector Service für Demo-Zwecke"""
    
    def __init__(
        self,
        persist_directory: str = "./mock_vector_db",
        embedding_model: str = "mock-model",
        collection_name: str = "examcraft_documents"
    ):
        """Initialisiere Mock Vector Service"""
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Erstelle Persist Directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Mock Storage
        self.storage_file = os.path.join(persist_directory, "mock_vectors.json")
        self._load_storage()
        
        # Mock embedding model status
        self._embedding_model = None
        
        logger.info(f"Mock VectorService initialized")
    
    def _load_storage(self):
        """Lade Mock Storage aus Datei"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self._storage = json.load(f)
            else:
                self._storage = {"chunks": {}, "documents": {}}
        except Exception as e:
            logger.warning(f"Failed to load storage: {e}")
            self._storage = {"chunks": {}, "documents": {}}
    
    def _save_storage(self):
        """Speichere Mock Storage in Datei"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._storage, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save storage: {e}")
    
    def get_or_create_collection(self, collection_name: Optional[str] = None):
        """Mock Collection Management"""
        return {"name": collection_name or self.collection_name}
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Mock Embedding-Erstellung
        Generiert zufällige Embeddings für Demo
        """
        if not texts:
            return []
        
        # Simuliere Verarbeitungszeit
        await asyncio.sleep(0.1)
        
        # Generiere Mock Embeddings (384 Dimensionen)
        embeddings = []
        for text in texts:
            # Verwende Text-Hash für konsistente "Embeddings"
            random.seed(hash(text) % 2**32)
            embedding = [random.uniform(-1, 1) for _ in range(384)]
            embeddings.append(embedding)
        
        return embeddings
    
    async def add_document_chunks(
        self,
        processed_doc: ProcessedDocument,
        collection_name: Optional[str] = None
    ) -> EmbeddingStats:
        """Füge Document Chunks zur Mock Vector Database hinzu"""
        start_time = time.time()
        
        # Extrahiere Texte
        texts = [chunk.content for chunk in processed_doc.chunks]
        
        # Erstelle Mock Embeddings
        embeddings = await self.create_embeddings(texts)
        
        # Speichere in Mock Storage
        doc_key = str(processed_doc.document_id)
        self._storage["documents"][doc_key] = {
            "document_id": processed_doc.document_id,
            "filename": processed_doc.filename,
            "mime_type": processed_doc.mime_type,
            "total_chunks": processed_doc.total_chunks,
            "metadata": processed_doc.metadata
        }
        
        # Speichere Chunks
        for i, chunk in enumerate(processed_doc.chunks):
            chunk_id = f"doc_{processed_doc.document_id}_chunk_{chunk.chunk_index}"
            
            self._storage["chunks"][chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": processed_doc.document_id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "embedding": embeddings[i],
                "metadata": {
                    "document_id": processed_doc.document_id,
                    "filename": processed_doc.filename,
                    "mime_type": processed_doc.mime_type,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "word_count": len(chunk.content.split()),
                    **chunk.metadata,
                    **processed_doc.metadata
                }
            }
        
        # Speichere Storage
        self._save_storage()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Added {len(texts)} chunks to mock vector database")
        
        return EmbeddingStats(
            total_chunks=len(texts),
            embedding_dimension=384,
            model_name=self.embedding_model_name,
            processing_time=processing_time
        )
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Berechne Cosine Similarity zwischen zwei Embeddings"""
        try:
            # Einfache Dot Product Similarity
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            norm1 = sum(a * a for a in embedding1) ** 0.5
            norm2 = sum(b * b for b in embedding2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, similarity)  # Normalisiere auf [0, 1]
        except:
            return 0.0
    
    async def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        document_ids: Optional[List[int]] = None,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Führe Mock Similarity Search durch"""
        
        # Erstelle Query Embedding
        query_embeddings = await self.create_embeddings([query])
        query_embedding = query_embeddings[0]
        
        # Sammle alle relevanten Chunks
        candidates = []
        for chunk_id, chunk_data in self._storage["chunks"].items():
            # Filter nach document_ids falls angegeben
            if document_ids and chunk_data["document_id"] not in document_ids:
                continue
            
            # Berechne Similarity
            similarity = self._calculate_similarity(query_embedding, chunk_data["embedding"])
            
            candidates.append({
                "chunk_id": chunk_id,
                "similarity": similarity,
                "data": chunk_data
            })
        
        # Sortiere nach Similarity (absteigend)
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Nimm Top N Ergebnisse
        results = []
        for candidate in candidates[:n_results]:
            data = candidate["data"]
            
            result = SearchResult(
                chunk_id=data["chunk_id"],
                document_id=data["document_id"],
                content=data["content"],
                similarity_score=candidate["similarity"],
                metadata=data["metadata"],
                chunk_index=data["chunk_index"]
            )
            results.append(result)
        
        logger.info(f"Mock similarity search returned {len(results)} results")
        return results
    
    async def get_document_chunks(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Hole alle Chunks eines spezifischen Dokuments"""
        
        results = []
        for chunk_id, chunk_data in self._storage["chunks"].items():
            if chunk_data["document_id"] == document_id:
                result = SearchResult(
                    chunk_id=chunk_data["chunk_id"],
                    document_id=chunk_data["document_id"],
                    content=chunk_data["content"],
                    similarity_score=1.0,
                    metadata=chunk_data["metadata"],
                    chunk_index=chunk_data["chunk_index"]
                )
                results.append(result)
        
        # Sortiere nach chunk_index
        results.sort(key=lambda x: x.chunk_index)
        
        logger.info(f"Retrieved {len(results)} chunks for document {document_id}")
        return results
    
    async def delete_document_chunks(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> int:
        """Lösche alle Chunks eines Dokuments"""
        
        deleted_count = 0
        chunk_ids_to_delete = []
        
        # Finde alle Chunk-IDs für das Dokument
        for chunk_id, chunk_data in self._storage["chunks"].items():
            if chunk_data["document_id"] == document_id:
                chunk_ids_to_delete.append(chunk_id)
        
        # Lösche Chunks
        for chunk_id in chunk_ids_to_delete:
            del self._storage["chunks"][chunk_id]
            deleted_count += 1
        
        # Lösche Dokument-Eintrag
        doc_key = str(document_id)
        if doc_key in self._storage["documents"]:
            del self._storage["documents"][doc_key]
        
        # Speichere Storage
        self._save_storage()
        
        logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
        return deleted_count
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Hole Mock Collection Statistiken"""
        
        total_chunks = len(self._storage["chunks"])
        total_documents = len(self._storage["documents"])
        
        stats = {
            "collection_name": collection_name or self.collection_name,
            "total_chunks": total_chunks,
            "total_documents": total_documents,
            "embedding_model": self.embedding_model_name,
            "persist_directory": self.persist_directory
        }
        
        # Füge Sample-Info hinzu
        if self._storage["documents"]:
            sample_doc = next(iter(self._storage["documents"].values()))
            stats["sample_document_id"] = sample_doc["document_id"]
            stats["sample_filename"] = sample_doc["filename"]
        
        return stats
    
    def reset_collection(self, collection_name: Optional[str] = None) -> bool:
        """Lösche alle Mock-Daten"""
        self._storage = {"chunks": {}, "documents": {}}
        self._save_storage()
        logger.info("Mock collection reset")
        return True


# Globale Service Instanz
vector_service = VectorService()
