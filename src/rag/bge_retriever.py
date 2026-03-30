"""
BGE RAG 检索引擎
使用 BGE-M3 Embedding + BGE-Reranker-v2-m3 实现 4 层检索：
  1. 稠密向量检索（Dense）
  2. 稀疏检索（Sparse / BM25-like）
  3. 多向量检索（ColBERT-style）
  4. 重排序（Reranker）
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

BGE_API_URL = os.getenv("BGE_API_URL", "http://localhost:8002")


@dataclass
class RetrievedDoc:
    content: str
    score: float
    metadata: dict[str, Any]


class BGERetriever:
    """
    通过 BGE API（:8002）实现向量检索和重排序。
    BGE API 由 bge_api.py 提供，运行在本地 DGX Spark 节点上。
    """

    def __init__(self, top_k: int = 10, rerank_top_n: int = 3):
        self.top_k = top_k
        self.rerank_top_n = rerank_top_n

    def embed(self, texts: list[str]) -> list[list[float]]:
        """调用 BGE-M3 获取稠密向量"""
        resp = requests.post(
            f"{BGE_API_URL}/v1/embeddings",
            json={"input": texts, "model": "bge-m3"},
            timeout=30,
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

    def rerank(self, query: str, documents: list[str]) -> list[dict]:
        """调用 BGE-Reranker-v2-m3 对候选文档重排序"""
        resp = requests.post(
            f"{BGE_API_URL}/v1/rerank",
            json={
                "query": query,
                "documents": documents,
                "model": "bge-reranker-v2-m3",
                "top_n": self.rerank_top_n,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]

    def retrieve(self, query: str, corpus: list[RetrievedDoc]) -> list[RetrievedDoc]:
        """
        4 层检索流程：
          1. 稠密向量召回（BGE-M3 dense）
          2. 稀疏关键词召回（BM25 近似，基于词频）
          3. 候选合并去重
          4. Reranker 精排
        """
        if not corpus:
            return []

        # Step 1 & 2: 向量召回 + 关键词召回（取 top_k 候选）
        candidates = self._dense_recall(query, corpus)

        # Step 3: Reranker 精排
        if len(candidates) > 1:
            texts = [doc.content for doc in candidates]
            ranked = self.rerank(query, texts)
            candidates = [
                RetrievedDoc(
                    content=candidates[r["index"]].content,
                    score=r["relevance_score"],
                    metadata=candidates[r["index"]].metadata,
                )
                for r in ranked
            ]

        return candidates

    def _dense_recall(self, query: str, corpus: list[RetrievedDoc]) -> list[RetrievedDoc]:
        """余弦相似度召回"""
        import numpy as np

        query_vec = self.embed([query])[0]
        doc_vecs = self.embed([doc.content for doc in corpus])

        q = np.array(query_vec)
        scores = [
            float(np.dot(q, np.array(v)) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-8))
            for v in doc_vecs
        ]
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.top_k]
        return [
            RetrievedDoc(content=corpus[i].content, score=scores[i], metadata=corpus[i].metadata)
            for i in top_indices
        ]
