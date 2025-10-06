#!/usr/bin/env python3
"""
Migration Script: ChromaDB zu Qdrant
Migriert alle Dokumente und Embeddings von ChromaDB zu Qdrant
"""

import asyncio
import os
import sys
import time
from typing import List, Dict, Any
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vector_service import VectorService as ChromaDBService
from services.qdrant_vector_service import QdrantVectorService
from services.docling_service import ProcessedDocument, DocumentChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChromaDBToQdrantMigrator:
    """Migrator für ChromaDB zu Qdrant Migration"""
    
    def __init__(self, 
                 chromadb_persist_dir: str = "./chroma_db",
                 qdrant_url: str = "http://localhost:6333",
                 collection_name: str = "examcraft_documents",
                 batch_size: int = 100):
        """
        Initialize Migrator
        
        Args:
            chromadb_persist_dir: ChromaDB persistence directory
            qdrant_url: Qdrant server URL
            collection_name: Collection name for both services
            batch_size: Batch size for migration
        """
        self.chromadb_persist_dir = chromadb_persist_dir
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.batch_size = batch_size
        
        # Initialize services
        self.chromadb_service = ChromaDBService(
            persist_directory=chromadb_persist_dir,
            collection_name=collection_name
        )
        self.qdrant_service = QdrantVectorService(
            qdrant_url=qdrant_url,
            collection_name=collection_name
        )
        
        # Migration statistics
        self.stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "migrated_chunks": 0,
            "failed_chunks": 0,
            "start_time": None,
            "end_time": None,
            "duration": 0
        }
    
    def get_chromadb_stats(self) -> Dict[str, Any]:
        """Get ChromaDB collection statistics"""
        try:
            stats = self.chromadb_service.get_collection_stats()
            logger.info(f"ChromaDB Stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get ChromaDB stats: {e}")
            return {}
    
    def get_qdrant_stats(self) -> Dict[str, Any]:
        """Get Qdrant collection statistics"""
        try:
            stats = self.qdrant_service.get_collection_stats()
            logger.info(f"Qdrant Stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {}
    
    def extract_chromadb_data(self) -> List[Dict[str, Any]]:
        """
        Extract all data from ChromaDB
        
        Returns:
            List of document chunks with metadata
        """
        logger.info("Extracting data from ChromaDB...")
        
        try:
            # Get all documents from ChromaDB
            # Note: ChromaDB doesn't have a direct "get all" method
            # We'll use a broad search to get all documents
            all_chunks = []
            
            # Try to get collection info first
            stats = self.get_chromadb_stats()
            total_chunks = stats.get("total_chunks", 0)
            
            if total_chunks == 0:
                logger.warning("No chunks found in ChromaDB collection")
                return []
            
            # Use similarity search with a generic query to get all documents
            # This is a workaround since ChromaDB doesn't have a direct "get all" method
            search_results = self.chromadb_service.similarity_search(
                query="document content text",  # Generic query
                n_results=total_chunks  # Get all chunks
            )
            
            logger.info(f"Extracted {len(search_results)} chunks from ChromaDB")
            
            # Convert search results to migration format
            for result in search_results:
                chunk_data = {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "content": result.content,
                    "chunk_index": getattr(result, 'chunk_index', 0),
                    "filename": getattr(result, 'filename', 'unknown'),
                    "metadata": getattr(result, 'metadata', {})
                }
                all_chunks.append(chunk_data)
            
            self.stats["total_chunks"] = len(all_chunks)
            
            # Group by document_id to count documents
            document_ids = set(chunk["document_id"] for chunk in all_chunks)
            self.stats["total_documents"] = len(document_ids)
            
            logger.info(f"Found {self.stats['total_documents']} documents with {self.stats['total_chunks']} chunks")
            
            return all_chunks
            
        except Exception as e:
            logger.error(f"Failed to extract ChromaDB data: {e}")
            return []
    
    async def migrate_chunks_to_qdrant(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Migrate chunks to Qdrant
        
        Args:
            chunks: List of chunk data to migrate
            
        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Migrating {len(chunks)} chunks to Qdrant...")
        
        try:
            # Group chunks by document_id
            documents_by_id = {}
            for chunk in chunks:
                doc_id = chunk["document_id"]
                if doc_id not in documents_by_id:
                    documents_by_id[doc_id] = []
                documents_by_id[doc_id].append(chunk)
            
            # Migrate each document
            for doc_id, doc_chunks in documents_by_id.items():
                try:
                    logger.info(f"Migrating document {doc_id} with {len(doc_chunks)} chunks...")
                    
                    # Create ProcessedDocument from chunks
                    document_chunks = []
                    filename = doc_chunks[0].get("filename", f"document_{doc_id}")
                    
                    for chunk_data in doc_chunks:
                        document_chunk = DocumentChunk(
                            content=chunk_data["content"],
                            chunk_index=chunk_data.get("chunk_index", 0),
                            page_number=chunk_data.get("page_number", 1),
                            metadata=chunk_data.get("metadata", {})
                        )
                        document_chunks.append(document_chunk)
                    
                    # Create ProcessedDocument
                    processed_doc = ProcessedDocument(
                        document_id=doc_id,
                        filename=filename,
                        mime_type="application/pdf",  # Default
                        total_pages=1,
                        total_chunks=len(document_chunks),
                        chunks=document_chunks,
                        metadata={"migrated_from": "chromadb"},
                        processing_time=0.0
                    )
                    
                    # Add to Qdrant
                    stats = await self.qdrant_service.add_document_chunks(processed_doc)
                    
                    self.stats["migrated_chunks"] += len(document_chunks)
                    logger.info(f"Successfully migrated document {doc_id}: {stats}")
                    
                except Exception as e:
                    logger.error(f"Failed to migrate document {doc_id}: {e}")
                    self.stats["failed_chunks"] += len(doc_chunks)
                    continue
            
            logger.info(f"Migration completed: {self.stats['migrated_chunks']} chunks migrated, {self.stats['failed_chunks']} failed")
            return self.stats["failed_chunks"] == 0
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    async def validate_migration(self) -> bool:
        """
        Validate migration by comparing data
        
        Returns:
            True if validation successful, False otherwise
        """
        logger.info("Validating migration...")
        
        try:
            # Get stats from both services
            chromadb_stats = self.get_chromadb_stats()
            qdrant_stats = self.get_qdrant_stats()
            
            chromadb_chunks = chromadb_stats.get("total_chunks", 0)
            qdrant_chunks = qdrant_stats.get("total_chunks", 0)
            
            logger.info(f"ChromaDB chunks: {chromadb_chunks}, Qdrant chunks: {qdrant_chunks}")
            
            if chromadb_chunks == qdrant_chunks and qdrant_chunks > 0:
                logger.info("✅ Migration validation successful!")
                return True
            else:
                logger.warning(f"❌ Migration validation failed: chunk count mismatch")
                return False
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    async def run_migration(self, validate: bool = True, backup: bool = True) -> bool:
        """
        Run complete migration process
        
        Args:
            validate: Whether to validate migration
            backup: Whether to backup ChromaDB data (placeholder)
            
        Returns:
            True if migration successful, False otherwise
        """
        logger.info("🚀 Starting ChromaDB to Qdrant migration...")
        self.stats["start_time"] = time.time()
        
        try:
            # Step 1: Check source and target
            logger.info("Step 1: Checking source and target services...")
            chromadb_stats = self.get_chromadb_stats()
            qdrant_stats = self.get_qdrant_stats()
            
            if chromadb_stats.get("total_chunks", 0) == 0:
                logger.warning("No data found in ChromaDB. Nothing to migrate.")
                return True
            
            # Step 2: Extract data from ChromaDB
            logger.info("Step 2: Extracting data from ChromaDB...")
            chunks = self.extract_chromadb_data()
            
            if not chunks:
                logger.error("No data extracted from ChromaDB")
                return False
            
            # Step 3: Migrate to Qdrant
            logger.info("Step 3: Migrating data to Qdrant...")
            migration_success = await self.migrate_chunks_to_qdrant(chunks)
            
            if not migration_success:
                logger.error("Migration failed")
                return False
            
            # Step 4: Validate migration
            if validate:
                logger.info("Step 4: Validating migration...")
                validation_success = await self.validate_migration()
                
                if not validation_success:
                    logger.error("Migration validation failed")
                    return False
            
            # Calculate duration
            self.stats["end_time"] = time.time()
            self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
            
            logger.info("🎉 Migration completed successfully!")
            logger.info(f"Migration Statistics:")
            logger.info(f"  - Total Documents: {self.stats['total_documents']}")
            logger.info(f"  - Total Chunks: {self.stats['total_chunks']}")
            logger.info(f"  - Migrated Chunks: {self.stats['migrated_chunks']}")
            logger.info(f"  - Failed Chunks: {self.stats['failed_chunks']}")
            logger.info(f"  - Duration: {self.stats['duration']:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            return False


async def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ChromaDB to Qdrant")
    parser.add_argument("--chromadb-dir", default="./chroma_db", help="ChromaDB persist directory")
    parser.add_argument("--qdrant-url", default="http://localhost:6333", help="Qdrant server URL")
    parser.add_argument("--collection", default="examcraft_documents", help="Collection name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for migration")
    parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    parser.add_argument("--dry-run", action="store_true", help="Dry run - don't actually migrate")
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = ChromaDBToQdrantMigrator(
        chromadb_persist_dir=args.chromadb_dir,
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        batch_size=args.batch_size
    )
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No data will be migrated")
        chromadb_stats = migrator.get_chromadb_stats()
        qdrant_stats = migrator.get_qdrant_stats()
        logger.info(f"Would migrate {chromadb_stats.get('total_chunks', 0)} chunks from ChromaDB to Qdrant")
        return
    
    # Run migration
    success = await migrator.run_migration(validate=not args.no_validate)
    
    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
