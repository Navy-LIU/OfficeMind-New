#!/usr/bin/env python3
"""
OfficeMind Embedding Service — Port 8002
Model  : Qwen3-Embedding (FlagEmbedding / sentence-transformers)
Backend: CPU / GPU（自动检测）

Endpoints:
  POST /v1/embeddings        — OpenAI-compatible embedding API
  POST /v1/rerank            — BGE Reranker 重排序
  GET  /health               — 服务健康检查
"""
from __future__ import annotations
import os, time, logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Union
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("embedding_service")

app = FastAPI(title="OfficeMind Embedding Service", version="1.0.0")

# ── 模型配置 ──────────────────────────────────────────────────────────────────
MODEL_DIR    = Path(os.getenv("MODEL_DIR", "/home/xsuper/models"))
EMBED_MODEL  = str(MODEL_DIR / "Qwen" / "Qwen3-Embedding")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

_embed_model  = None
_rerank_model = None

def get_embed():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBED_MODEL}")
        _embed_model = SentenceTransformer(EMBED_MODEL, trust_remote_code=True)
        logger.info("✅ Embedding model loaded")
    return _embed_model

def get_reranker():
    global _rerank_model
    if _rerank_model is None:
        from FlagEmbedding import FlagReranker
        logger.info(f"Loading reranker: {RERANK_MODEL}")
        _rerank_model = FlagReranker(RERANK_MODEL, use_fp16=True)
        logger.info("✅ Reranker loaded")
    return _rerank_model

# ── 请求模型 ──────────────────────────────────────────────────────────────────
class EmbedRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "qwen3-embedding"

class RerankRequest(BaseModel):
    query: str
    documents: List[str]
    top_n: int = 5

# ── 接口 ──────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model":  "qwen3-embedding",
        "port":   8002,
    }

@app.post("/v1/embeddings")
async def embeddings(req: EmbedRequest):
    t0 = time.time()
    model = get_embed()
    texts = [req.input] if isinstance(req.input, str) else req.input
    try:
        vecs = model.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": i, "embedding": v}
            for i, v in enumerate(vecs)
        ],
        "model":   req.model,
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "usage": {"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": 0},
    }

@app.post("/v1/rerank")
async def rerank(req: RerankRequest):
    t0 = time.time()
    reranker = get_reranker()
    pairs = [[req.query, doc] for doc in req.documents]
    try:
        scores = reranker.compute_score(pairs, normalize=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ranked = sorted(
        [{"index": i, "document": doc, "score": float(scores[i])}
         for i, doc in enumerate(req.documents)],
        key=lambda x: x["score"], reverse=True
    )[:req.top_n]

    return {
        "results":    ranked,
        "latency_ms": round((time.time() - t0) * 1000, 1),
    }

if __name__ == "__main__":
    logger.info("🚀 OfficeMind Embedding Service starting on :8002")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
