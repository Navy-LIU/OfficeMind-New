"""
OfficeMind 4-Layer RAG Pipeline
Layer 1: Semantic Chunking (sentence-transformers)
Layer 2: HyDE (Hypothetical Document Embeddings)
Layer 3: Hybrid Search (Dense Vector + BM25)
Layer 4: MMR Reranking (Maximal Marginal Relevance)

Embedding: Qwen3-Embedding (local, /home/xsuper/models)
Vector DB: ChromaDB (persistent)
"""
from __future__ import annotations
import os, logging, hashlib
from pathlib import Path
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# ── Embedding Client (Qwen3-Embedding via vLLM) ───────────────────────────────
class LocalEmbedding:
    """Calls local Qwen3-Embedding via OpenAI-compatible API."""
    
    def __init__(self, base_url: str = None, model: str = "Qwen3-Embedding"):
        self.base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.model = model
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=os.getenv("VLLM_API_KEY", "EMPTY")
            )
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

# ── Layer 1: Semantic Chunker ─────────────────────────────────────────────────
class SemanticChunker:
    """Splits text into semantically coherent chunks using embedding similarity."""
    
    def __init__(self, embedder: LocalEmbedding, 
                 breakpoint_threshold: float = 0.7,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 1000):
        self.embedder = embedder
        self.threshold = breakpoint_threshold
        self.min_size = min_chunk_size
        self.max_size = max_chunk_size
    
    def chunk(self, text: str) -> List[str]:
        """Split text into semantic chunks."""
        import re
        # Split into sentences
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 2:
            return [text]
        
        try:
            # Embed all sentences
            embeddings = self.embedder.embed_documents(sentences)
            
            # Find breakpoints where similarity drops
            chunks, current_chunk = [], [sentences[0]]
            for i in range(1, len(sentences)):
                sim = self._cosine_sim(embeddings[i-1], embeddings[i])
                current_text = " ".join(current_chunk)
                
                if (sim < self.threshold and len(current_text) >= self.min_size) or \
                   len(current_text) >= self.max_size:
                    chunks.append(current_text)
                    current_chunk = [sentences[i]]
                else:
                    current_chunk.append(sentences[i])
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            return chunks
        except Exception as e:
            logger.warning(f"Semantic chunking failed, falling back to fixed: {e}")
            return self._fixed_chunk(text)
    
    def _fixed_chunk(self, text: str, size: int = 500, overlap: int = 50) -> List[str]:
        chunks = []
        for i in range(0, len(text), size - overlap):
            chunks.append(text[i:i+size])
        return chunks
    
    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

# ── Layer 2: HyDE (Hypothetical Document Embeddings) ─────────────────────────
class HyDEExpander:
    """Generates hypothetical answers to improve retrieval recall."""
    
    def __init__(self, llm_base_url: str = None):
        self.base_url = llm_base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.base_url, api_key="EMPTY")
        return self._client
    
    def expand(self, query: str, n: int = 3) -> List[str]:
        """Generate n hypothetical document passages for the query."""
        prompt = (
            f"请为以下问题生成{n}个可能的文档段落（每个段落100字左右），"
            f"这些段落应该是能回答该问题的理想文档内容。\n"
            f"问题：{query}\n"
            f"只输出段落内容，用---分隔，不要编号。"
        )
        try:
            resp = self.client.chat.completions.create(
                model="Qwen3-Thinking",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600,
            )
            passages = resp.choices[0].message.content.split("---")
            return [p.strip() for p in passages if p.strip()][:n]
        except Exception as e:
            logger.warning(f"HyDE expansion failed: {e}")
            return [query]

# ── Layer 3: Hybrid Search (Dense + BM25) ────────────────────────────────────
class HybridSearcher:
    """Combines dense vector search with BM25 sparse retrieval."""
    
    def __init__(self, embedder: LocalEmbedding, persist_dir: str = "./chroma_db"):
        self.embedder = embedder
        self.persist_dir = persist_dir
        self._collection = None
        self._bm25 = None
        self._docs_cache: List[dict] = []
    
    def _get_collection(self):
        if self._collection is None:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = client.get_or_create_collection(
                name="officemind_docs",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def add_documents(self, docs: List[dict]) -> int:
        """Add documents to vector store. docs: [{"text": ..., "metadata": {...}}]"""
        collection = self._get_collection()
        texts = [d["text"] for d in docs]
        embeddings = self.embedder.embed_documents(texts)
        ids = [hashlib.md5(t.encode()).hexdigest()[:16] for t in texts]
        metadatas = [d.get("metadata", {}) for d in docs]
        
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        self._docs_cache.extend(docs)
        self._bm25 = None  # Reset BM25 index
        logger.info(f"Added {len(docs)} documents to vector store")
        return len(docs)
    
    def search(self, query: str, k: int = 10, alpha: float = 0.6) -> List[dict]:
        """Hybrid search: alpha * dense + (1-alpha) * sparse."""
        # Dense search
        q_emb = self.embedder.embed_query(query)
        collection = self._get_collection()
        dense_results = collection.query(
            query_embeddings=[q_emb],
            n_results=min(k * 2, collection.count() or 1),
            include=["documents", "metadatas", "distances"]
        )
        
        dense_docs = []
        if dense_results["documents"] and dense_results["documents"][0]:
            for doc, meta, dist in zip(
                dense_results["documents"][0],
                dense_results["metadatas"][0],
                dense_results["distances"][0]
            ):
                dense_docs.append({
                    "text": doc,
                    "metadata": meta,
                    "dense_score": 1.0 - float(dist),
                    "sparse_score": 0.0,
                })
        
        # BM25 sparse search
        if self._docs_cache:
            bm25_results = self._bm25_search(query, k * 2)
            # Merge scores
            bm25_map = {r["text"]: r["sparse_score"] for r in bm25_results}
            for doc in dense_docs:
                doc["sparse_score"] = bm25_map.get(doc["text"], 0.0)
        
        # Combine scores
        for doc in dense_docs:
            doc["score"] = alpha * doc["dense_score"] + (1 - alpha) * doc["sparse_score"]
        
        return sorted(dense_docs, key=lambda x: x["score"], reverse=True)[:k]
    
    def _bm25_search(self, query: str, k: int) -> List[dict]:
        try:
            from rank_bm25 import BM25Okapi
            if self._bm25 is None:
                corpus = [d["text"].split() for d in self._docs_cache]
                self._bm25 = BM25Okapi(corpus)
            
            scores = self._bm25.get_scores(query.split())
            top_k = np.argsort(scores)[::-1][:k]
            max_score = scores[top_k[0]] if scores[top_k[0]] > 0 else 1.0
            
            return [
                {
                    "text": self._docs_cache[i]["text"],
                    "metadata": self._docs_cache[i].get("metadata", {}),
                    "sparse_score": float(scores[i]) / max_score,
                }
                for i in top_k if scores[i] > 0
            ]
        except Exception as e:
            logger.warning(f"BM25 search failed: {e}")
            return []

# ── Layer 4: MMR Reranker ─────────────────────────────────────────────────────
class MMRReranker:
    """Maximal Marginal Relevance: balance relevance and diversity."""
    
    def __init__(self, embedder: LocalEmbedding, lambda_param: float = 0.7):
        self.embedder = embedder
        self.lambda_param = lambda_param  # 1.0 = pure relevance, 0.0 = pure diversity
    
    def rerank(self, query: str, docs: List[dict], k: int = 5) -> List[dict]:
        """Select k docs maximizing relevance while minimizing redundancy."""
        if len(docs) <= k:
            return docs
        
        try:
            q_emb = np.array(self.embedder.embed_query(query))
            doc_embs = np.array(self.embedder.embed_documents([d["text"] for d in docs]))
            
            selected, remaining = [], list(range(len(docs)))
            
            for _ in range(k):
                if not remaining:
                    break
                
                best_idx, best_score = -1, -float("inf")
                for i in remaining:
                    # Relevance to query
                    rel = float(np.dot(q_emb, doc_embs[i]) / 
                               (np.linalg.norm(q_emb) * np.linalg.norm(doc_embs[i]) + 1e-8))
                    
                    # Redundancy with already selected
                    if selected:
                        sims = [
                            float(np.dot(doc_embs[i], doc_embs[j]) /
                                  (np.linalg.norm(doc_embs[i]) * np.linalg.norm(doc_embs[j]) + 1e-8))
                            for j in selected
                        ]
                        red = max(sims)
                    else:
                        red = 0.0
                    
                    score = self.lambda_param * rel - (1 - self.lambda_param) * red
                    if score > best_score:
                        best_score, best_idx = score, i
                
                selected.append(best_idx)
                remaining.remove(best_idx)
            
            return [docs[i] for i in selected]
        except Exception as e:
            logger.warning(f"MMR reranking failed: {e}")
            return docs[:k]

# ── Main RAG Pipeline ─────────────────────────────────────────────────────────
class RAGPipeline:
    """
    4-Layer RAG Pipeline:
    Query → HyDE Expansion → Hybrid Search → MMR Rerank → LLM Answer
    """
    
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.embedder = LocalEmbedding()
        self.chunker = SemanticChunker(self.embedder)
        self.hyde = HyDEExpander()
        self.searcher = HybridSearcher(self.embedder, persist_dir)
        self.reranker = MMRReranker(self.embedder)
        self._llm_client = None
    
    @property
    def llm(self):
        if self._llm_client is None:
            from openai import OpenAI
            self._llm_client = OpenAI(
                base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
                api_key="EMPTY"
            )
        return self._llm_client
    
    def ingest(self, text: str, metadata: dict = None) -> int:
        """Ingest a document into the knowledge base."""
        chunks = self.chunker.chunk(text)
        docs = [{"text": c, "metadata": metadata or {}} for c in chunks]
        return self.searcher.add_documents(docs)
    
    def ingest_file(self, file_path: str) -> int:
        """Ingest a file (PDF, DOCX, TXT) into the knowledge base."""
        path = Path(file_path)
        text = self._extract_text(path)
        metadata = {"source": str(path), "filename": path.name, "type": path.suffix}
        return self.ingest(text, metadata)
    
    def query(self, question: str, k: int = 5, use_hyde: bool = True) -> dict:
        """
        Full 4-layer RAG query.
        Returns: {answer, sources, confidence}
        """
        # Layer 2: HyDE expansion
        search_queries = [question]
        if use_hyde:
            hypothetical = self.hyde.expand(question, n=2)
            search_queries.extend(hypothetical)
        
        # Layer 3: Hybrid search across all queries
        all_results = []
        for q in search_queries:
            results = self.searcher.search(q, k=k * 2)
            all_results.extend(results)
        
        # Deduplicate
        seen, unique = set(), []
        for r in all_results:
            key = r["text"][:100]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        # Layer 4: MMR reranking
        final_docs = self.reranker.rerank(question, unique, k=k)
        
        if not final_docs:
            return {
                "answer": "知识库中未找到相关信息，请上传相关文档后重试。",
                "sources": [],
                "confidence": 0.0,
            }
        
        # Build context
        context = "\n\n---\n\n".join([
            f"[来源 {i+1}: {d['metadata'].get('filename', '未知')}]\n{d['text']}"
            for i, d in enumerate(final_docs)
        ])
        
        # LLM answer generation
        prompt = (
            f"基于以下文档内容回答问题。如果文档中没有相关信息，请明确说明。\n\n"
            f"文档内容：\n{context}\n\n"
            f"问题：{question}\n\n"
            f"请提供详细、准确的回答，并引用具体来源。"
        )
        
        try:
            resp = self.llm.chat.completions.create(
                model="Qwen3-Thinking",
                messages=[
                    {"role": "system", "content": "你是企业文档智能助手，运行在NVIDIA DGX Spark GB10。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            answer = resp.choices[0].message.content
            confidence = min(1.0, sum(d.get("score", 0.5) for d in final_docs) / len(final_docs))
        except Exception as e:
            answer = f"生成回答时出错：{e}"
            confidence = 0.0
        
        return {
            "answer": answer,
            "sources": [
                {
                    "text": d["text"][:200] + "...",
                    "filename": d["metadata"].get("filename", "未知"),
                    "score": round(d.get("score", 0), 3),
                }
                for d in final_docs
            ],
            "confidence": round(confidence, 3),
        }
    
    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                return "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                raise ImportError("pip install pypdf")
        elif suffix in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                raise ImportError("pip install python-docx")
        elif suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
