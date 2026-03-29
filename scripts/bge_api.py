"""
BGE Embedding + Reranker API
提供 OpenAI 兼容接口，监听 :8002
  POST /v1/embeddings  — BGE-M3 稠密向量
  POST /v1/rerank      — BGE-Reranker-v2-m3 重排序
"""
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from FlagEmbedding import BGEM3FlagModel, FlagReranker

MODELS_DIR = os.getenv("MODELS_DIR", "/home/xsuper/models")
BGE_M3_PATH = os.path.join(MODELS_DIR, "bge/bge-m3")
RERANKER_PATH = os.path.join(MODELS_DIR, "bge/bge-reranker-v2-m3")

# 全局模型实例，启动时加载一次
_embedder: BGEM3FlagModel | None = None
_reranker: FlagReranker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _reranker
    print("[bge_api] 加载 BGE-M3 Embedding 模型...")
    _embedder = BGEM3FlagModel(BGE_M3_PATH, use_fp16=True)
    print("[bge_api] 加载 BGE-Reranker-v2-m3 模型...")
    _reranker = FlagReranker(RERANKER_PATH, use_fp16=True)
    print("[bge_api] 模型加载完成，服务就绪")
    yield


app = FastAPI(title="BGE API", version="1.0", lifespan=lifespan)


# ── 请求/响应模型 ─────────────────────────────────────────────

class EmbeddingRequest(BaseModel):
    input: list[str]
    model: str = "bge-m3"


class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    model: str = "bge-reranker-v2-m3"
    top_n: int = 3


# ── 接口实现 ──────────────────────────────────────────────────

@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    vecs = _embedder.encode(req.input, batch_size=12)["dense_vecs"].tolist()
    return {
        "object": "list",
        "model": req.model,
        "data": [
            {"object": "embedding", "index": i, "embedding": vec}
            for i, vec in enumerate(vecs)
        ],
    }


@app.post("/v1/rerank")
def rerank(req: RerankRequest):
    pairs = [[req.query, doc] for doc in req.documents]
    scores = _reranker.compute_score(pairs, normalize=True)
    if isinstance(scores, float):
        scores = [scores]

    ranked = sorted(
        [{"index": i, "relevance_score": float(s), "document": req.documents[i]}
         for i, s in enumerate(scores)],
        key=lambda x: x["relevance_score"],
        reverse=True,
    )[: req.top_n]

    return {"model": req.model, "results": ranked}


@app.get("/health")
def health():
    return {"status": "ok", "embedder": _embedder is not None, "reranker": _reranker is not None}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
