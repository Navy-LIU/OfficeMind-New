"""
OfficeMind RAG Pipeline
4-Layer Retrieval:
  1. Semantic Chunking
  2. HyDE Query Optimization (Hypothetical Document Embeddings)
  3. Hybrid Search (Vector 0.7 + BM25 0.3)
  4. MMR Reranking + Context Compression
"""

from .pipeline import RAGPipeline
from .indexer import DocumentIndexer

__all__ = ["RAGPipeline", "DocumentIndexer"]
