#!/usr/bin/env python3
"""
Performance Test Script: Qdrant vs ChromaDB
Vergleicht die Performance zwischen Qdrant und ChromaDB Vector Services
"""

import asyncio
import os
import sys
import time
import statistics
from typing import List, Dict, Any, Tuple
import logging
import json

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


class VectorServicePerformanceTester:
    """Performance Tester für Vector Services"""
    
    def __init__(self):
        """Initialize Performance Tester"""
        self.chromadb_service = ChromaDBService(
            persist_directory="./test_chroma_db",
            collection_name="performance_test"
        )
        self.qdrant_service = QdrantVectorService(
            qdrant_url="http://localhost:6333",
            collection_name="performance_test"
        )
        
        self.results = {
            "chromadb": {},
            "qdrant": {},
            "comparison": {}
        }
    
    def generate_test_documents(self, num_docs: int = 10, chunks_per_doc: int = 20) -> List[ProcessedDocument]:
        """
        Generate test documents for performance testing
        
        Args:
            num_docs: Number of documents to generate
            chunks_per_doc: Number of chunks per document
            
        Returns:
            List of ProcessedDocument objects
        """
        logger.info(f"Generating {num_docs} test documents with {chunks_per_doc} chunks each...")
        
        documents = []
        
        for doc_id in range(1, num_docs + 1):
            chunks = []
            
            for chunk_idx in range(chunks_per_doc):
                content = f"""
                This is test document {doc_id}, chunk {chunk_idx + 1}.
                This chunk contains sample text for performance testing of vector databases.
                The content includes various topics like machine learning, artificial intelligence,
                natural language processing, vector embeddings, similarity search, and database performance.
                Document ID: {doc_id}, Chunk Index: {chunk_idx}, Total Length: approximately 500 characters.
                Additional content to make the chunk longer and more realistic for testing purposes.
                Performance testing is crucial for evaluating the efficiency of vector database operations.
                """
                
                chunk = DocumentChunk(
                    content=content.strip(),
                    chunk_index=chunk_idx,
                    page_number=(chunk_idx // 5) + 1,  # 5 chunks per page
                    metadata={
                        "test_doc": True,
                        "doc_category": f"category_{doc_id % 3}",
                        "chunk_type": "performance_test"
                    }
                )
                chunks.append(chunk)
            
            document = ProcessedDocument(
                document_id=doc_id,
                filename=f"test_document_{doc_id}.txt",
                mime_type="text/plain",
                total_pages=(chunks_per_doc // 5) + 1,
                total_chunks=chunks_per_doc,
                chunks=chunks,
                metadata={
                    "test_document": True,
                    "performance_test": True,
                    "doc_size": "medium"
                },
                processing_time=0.1
            )
            documents.append(document)
        
        logger.info(f"Generated {len(documents)} test documents")
        return documents
    
    async def measure_add_performance(self, service, service_name: str, documents: List[ProcessedDocument]) -> Dict[str, Any]:
        """
        Measure document addition performance
        
        Args:
            service: Vector service instance
            service_name: Name of the service
            documents: Documents to add
            
        Returns:
            Performance metrics
        """
        logger.info(f"Testing {service_name} document addition performance...")
        
        times = []
        total_chunks = 0
        
        for doc in documents:
            start_time = time.time()
            
            try:
                stats = await service.add_document_chunks(doc)
                end_time = time.time()
                
                duration = end_time - start_time
                times.append(duration)
                total_chunks += len(doc.chunks)
                
                logger.debug(f"{service_name}: Added document {doc.document_id} in {duration:.3f}s")
                
            except Exception as e:
                logger.error(f"{service_name}: Failed to add document {doc.document_id}: {e}")
                continue
        
        if not times:
            return {"error": "No documents were successfully added"}
        
        metrics = {
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "total_time": sum(times),
            "avg_time_per_doc": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "median_time": statistics.median(times),
            "chunks_per_second": total_chunks / sum(times) if sum(times) > 0 else 0,
            "docs_per_second": len(documents) / sum(times) if sum(times) > 0 else 0
        }
        
        logger.info(f"{service_name} Addition Performance:")
        logger.info(f"  - Total Time: {metrics['total_time']:.3f}s")
        logger.info(f"  - Avg Time per Doc: {metrics['avg_time_per_doc']:.3f}s")
        logger.info(f"  - Chunks per Second: {metrics['chunks_per_second']:.1f}")
        
        return metrics
    
    async def measure_search_performance(self, service, service_name: str, queries: List[str], n_results: int = 5) -> Dict[str, Any]:
        """
        Measure search performance
        
        Args:
            service: Vector service instance
            service_name: Name of the service
            queries: Search queries to test
            n_results: Number of results per query
            
        Returns:
            Performance metrics
        """
        logger.info(f"Testing {service_name} search performance...")
        
        times = []
        total_results = 0
        
        for query in queries:
            start_time = time.time()
            
            try:
                results = await service.similarity_search(query, n_results=n_results)
                end_time = time.time()
                
                duration = end_time - start_time
                times.append(duration)
                total_results += len(results)
                
                logger.debug(f"{service_name}: Search '{query[:30]}...' took {duration:.3f}s, found {len(results)} results")
                
            except Exception as e:
                logger.error(f"{service_name}: Search failed for query '{query[:30]}...': {e}")
                continue
        
        if not times:
            return {"error": "No searches were successful"}
        
        metrics = {
            "total_queries": len(queries),
            "total_results": total_results,
            "total_time": sum(times),
            "avg_time_per_query": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "median_time": statistics.median(times),
            "queries_per_second": len(queries) / sum(times) if sum(times) > 0 else 0,
            "avg_results_per_query": total_results / len(queries) if len(queries) > 0 else 0
        }
        
        logger.info(f"{service_name} Search Performance:")
        logger.info(f"  - Total Time: {metrics['total_time']:.3f}s")
        logger.info(f"  - Avg Time per Query: {metrics['avg_time_per_query']:.3f}s")
        logger.info(f"  - Queries per Second: {metrics['queries_per_second']:.1f}")
        
        return metrics
    
    def measure_memory_usage(self, service, service_name: str) -> Dict[str, Any]:
        """
        Measure memory usage (basic implementation)
        
        Args:
            service: Vector service instance
            service_name: Name of the service
            
        Returns:
            Memory metrics
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            metrics = {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "percent": process.memory_percent()
            }
            
            logger.info(f"{service_name} Memory Usage:")
            logger.info(f"  - RSS: {metrics['rss_mb']:.1f} MB")
            logger.info(f"  - VMS: {metrics['vms_mb']:.1f} MB")
            logger.info(f"  - Percent: {metrics['percent']:.1f}%")
            
            return metrics
            
        except ImportError:
            logger.warning("psutil not available, skipping memory measurement")
            return {"error": "psutil not available"}
        except Exception as e:
            logger.error(f"Memory measurement failed: {e}")
            return {"error": str(e)}
    
    def generate_test_queries(self) -> List[str]:
        """Generate test queries for search performance testing"""
        queries = [
            "machine learning algorithms",
            "artificial intelligence applications",
            "natural language processing techniques",
            "vector embeddings similarity",
            "database performance optimization",
            "document processing methods",
            "text analysis and mining",
            "information retrieval systems",
            "semantic search capabilities",
            "data science methodologies",
            "performance testing strategies",
            "vector database comparison",
            "embedding model evaluation",
            "similarity search algorithms",
            "document classification techniques"
        ]
        return queries
    
    async def run_performance_test(self, num_docs: int = 10, chunks_per_doc: int = 20) -> Dict[str, Any]:
        """
        Run complete performance test
        
        Args:
            num_docs: Number of test documents
            chunks_per_doc: Chunks per document
            
        Returns:
            Complete performance results
        """
        logger.info("🚀 Starting Vector Service Performance Test...")
        
        # Generate test data
        documents = self.generate_test_documents(num_docs, chunks_per_doc)
        queries = self.generate_test_queries()
        
        # Reset collections
        logger.info("Resetting collections...")
        self.chromadb_service.reset_collection()
        self.qdrant_service.reset_collection()
        
        # Test ChromaDB
        logger.info("Testing ChromaDB Performance...")
        chromadb_add = await self.measure_add_performance(self.chromadb_service, "ChromaDB", documents)
        chromadb_search = await self.measure_search_performance(self.chromadb_service, "ChromaDB", queries)
        chromadb_memory = self.measure_memory_usage(self.chromadb_service, "ChromaDB")
        
        self.results["chromadb"] = {
            "addition": chromadb_add,
            "search": chromadb_search,
            "memory": chromadb_memory
        }
        
        # Test Qdrant
        logger.info("Testing Qdrant Performance...")
        qdrant_add = await self.measure_add_performance(self.qdrant_service, "Qdrant", documents)
        qdrant_search = await self.measure_search_performance(self.qdrant_service, "Qdrant", queries)
        qdrant_memory = self.measure_memory_usage(self.qdrant_service, "Qdrant")
        
        self.results["qdrant"] = {
            "addition": qdrant_add,
            "search": qdrant_search,
            "memory": qdrant_memory
        }
        
        # Calculate comparisons
        self.results["comparison"] = self.calculate_comparisons()
        
        # Print summary
        self.print_performance_summary()
        
        return self.results
    
    def calculate_comparisons(self) -> Dict[str, Any]:
        """Calculate performance comparisons between services"""
        comparison = {}
        
        try:
            # Addition performance comparison
            chromadb_add_time = self.results["chromadb"]["addition"].get("avg_time_per_doc", 0)
            qdrant_add_time = self.results["qdrant"]["addition"].get("avg_time_per_doc", 0)
            
            if chromadb_add_time > 0 and qdrant_add_time > 0:
                comparison["addition_speedup"] = chromadb_add_time / qdrant_add_time
                comparison["addition_winner"] = "Qdrant" if qdrant_add_time < chromadb_add_time else "ChromaDB"
            
            # Search performance comparison
            chromadb_search_time = self.results["chromadb"]["search"].get("avg_time_per_query", 0)
            qdrant_search_time = self.results["qdrant"]["search"].get("avg_time_per_query", 0)
            
            if chromadb_search_time > 0 and qdrant_search_time > 0:
                comparison["search_speedup"] = chromadb_search_time / qdrant_search_time
                comparison["search_winner"] = "Qdrant" if qdrant_search_time < chromadb_search_time else "ChromaDB"
            
            # Memory usage comparison
            chromadb_memory = self.results["chromadb"]["memory"].get("rss_mb", 0)
            qdrant_memory = self.results["qdrant"]["memory"].get("rss_mb", 0)
            
            if chromadb_memory > 0 and qdrant_memory > 0:
                comparison["memory_efficiency"] = chromadb_memory / qdrant_memory
                comparison["memory_winner"] = "Qdrant" if qdrant_memory < chromadb_memory else "ChromaDB"
            
        except Exception as e:
            logger.error(f"Failed to calculate comparisons: {e}")
        
        return comparison
    
    def print_performance_summary(self):
        """Print performance test summary"""
        logger.info("\n" + "="*80)
        logger.info("📊 PERFORMANCE TEST SUMMARY")
        logger.info("="*80)
        
        # Addition Performance
        logger.info("\n🔄 DOCUMENT ADDITION PERFORMANCE:")
        chromadb_add = self.results["chromadb"]["addition"]
        qdrant_add = self.results["qdrant"]["addition"]
        
        logger.info(f"ChromaDB: {chromadb_add.get('avg_time_per_doc', 0):.3f}s per doc, {chromadb_add.get('chunks_per_second', 0):.1f} chunks/s")
        logger.info(f"Qdrant:   {qdrant_add.get('avg_time_per_doc', 0):.3f}s per doc, {qdrant_add.get('chunks_per_second', 0):.1f} chunks/s")
        
        # Search Performance
        logger.info("\n🔍 SEARCH PERFORMANCE:")
        chromadb_search = self.results["chromadb"]["search"]
        qdrant_search = self.results["qdrant"]["search"]
        
        logger.info(f"ChromaDB: {chromadb_search.get('avg_time_per_query', 0):.3f}s per query, {chromadb_search.get('queries_per_second', 0):.1f} queries/s")
        logger.info(f"Qdrant:   {qdrant_search.get('avg_time_per_query', 0):.3f}s per query, {qdrant_search.get('queries_per_second', 0):.1f} queries/s")
        
        # Winner Summary
        logger.info("\n🏆 PERFORMANCE WINNERS:")
        comparison = self.results["comparison"]
        
        if "addition_winner" in comparison:
            speedup = comparison.get("addition_speedup", 1)
            logger.info(f"Addition: {comparison['addition_winner']} ({speedup:.2f}x faster)")
        
        if "search_winner" in comparison:
            speedup = comparison.get("search_speedup", 1)
            logger.info(f"Search:   {comparison['search_winner']} ({speedup:.2f}x faster)")
        
        if "memory_winner" in comparison:
            efficiency = comparison.get("memory_efficiency", 1)
            logger.info(f"Memory:   {comparison['memory_winner']} ({efficiency:.2f}x more efficient)")
        
        logger.info("="*80)
    
    def save_results(self, filename: str = "performance_results.json"):
        """Save performance results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Performance results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


async def main():
    """Main performance test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance test for Vector Services")
    parser.add_argument("--docs", type=int, default=10, help="Number of test documents")
    parser.add_argument("--chunks", type=int, default=20, help="Chunks per document")
    parser.add_argument("--output", default="performance_results.json", help="Output file for results")
    
    args = parser.parse_args()
    
    # Create tester
    tester = VectorServicePerformanceTester()
    
    # Run performance test
    results = await tester.run_performance_test(
        num_docs=args.docs,
        chunks_per_doc=args.chunks
    )
    
    # Save results
    tester.save_results(args.output)
    
    logger.info("✅ Performance test completed!")


if __name__ == "__main__":
    asyncio.run(main())
