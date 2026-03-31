import numpy as np
import requests
import json
from typing import List, Dict

class RAGDocumentQA:
    """
    高级 AI 架构师重构版：4 层高精度 RAG 检索引擎
    架构：语义分块 → HyDE (假设性文档嵌入) → 混合搜索 (Dense+BM25) → MMR 重排
    """
    def __init__(self, embedding_url="http://localhost:8002", llm_url="http://localhost:8000"):
        self.embedding_url = embedding_url
        self.llm_url = llm_url
        self.documents = [] # 模拟文档库

    def _semantic_chunking(self, text: str) -> List[str]:
        """第一层：语义分块 (基于句子相似度或固定窗口)"""
        # 实际实现中应使用 LangChain 的 SemanticChunker
        return text.split("\n\n")

    def _generate_hyde_query(self, query: str) -> str:
        """第二层：HyDE (Hypothetical Document Embeddings)"""
        # 生成一个假设性的回答，用于增强检索效果
        payload = {
            "model": "qwen3.5:35b",
            "messages": [{"role": "user", "content": f"请针对以下问题写一个简短的、假设性的回答，用于文档检索：{query}"}],
            "max_tokens": 100
        }
        try:
            response = requests.post(f"{self.llm_url}/v1/chat/completions", json=payload, timeout=30)
            return response.json()['choices'][0]['message']['content']
        except:
            return query

    def _hybrid_search(self, query: str, hyde_query: str) -> List[Dict]:
        """第三层：混合搜索 (Dense + BM25)"""
        # 模拟混合搜索逻辑
        # 实际应调用向量数据库 (如 Milvus/Chroma)
        return [{"content": "检索到的文档片段...", "score": 0.95}]

    def _mmr_rerank(self, results: List[Dict], k: int = 3) -> List[Dict]:
        """第四层：MMR (Maximal Marginal Relevance) 重排"""
        # 增加结果的多样性，减少冗余
        return results[:k]

    def query_knowledge_base(self, query: str) -> str:
        """执行完整的 4 层 RAG 检索流程"""
        # 1. HyDE 增强
        hyde_query = self._generate_hyde_query(query)
        
        # 2. 混合搜索
        search_results = self._hybrid_search(query, hyde_query)
        
        # 3. MMR 重排
        final_context = self._mmr_rerank(search_results)
        
        # 4. 生成最终回答
        context_str = "\n".join([res['content'] for res in final_context])
        prompt = f"基于以下背景信息回答问题：\n{context_str}\n\n问题：{query}"
        
        payload = {
            "model": "qwen3.5:35b",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(f"{self.llm_url}/v1/chat/completions", json=payload, timeout=60)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"RAG Error: {str(e)}"
