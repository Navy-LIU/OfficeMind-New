#!/usr/bin/env python3
"""
OfficeMind LLM Service — Port 8000
Model  : Qwen2.5-72B-Instruct (GGUF, llama_cpp, full GPU offload)
Backend: llama-cpp-python with CUDA 13 / GB10 Blackwell
"""
from __future__ import annotations
import os, time, logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("llm_service")

# ── 模型配置 ──────────────────────────────────────────────────────────────────
MODEL_DIR   = Path(os.getenv("MODEL_DIR", "/home/xsuper/models"))
MODEL_PATH  = MODEL_DIR / "qwen2.5-72b-instruct-q4_k_m.gguf"
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "-1"))   # -1 = 全部层卸载到 GPU
N_CTX        = int(os.getenv("N_CTX", "4096"))
N_THREADS    = int(os.getenv("N_THREADS", "8"))

app = FastAPI(title="OfficeMind LLM Service", version="1.0.0")

# ── 懒加载模型 ────────────────────────────────────────────────────────────────
_llm = None

def get_llm():
    global _llm
    if _llm is None:
        from llama_cpp import Llama
        logger.info(f"Loading model: {MODEL_PATH}")
        logger.info(f"GPU layers: {N_GPU_LAYERS}, ctx: {N_CTX}")
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_gpu_layers=N_GPU_LAYERS,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            verbose=False,
        )
        logger.info("✅ Model loaded successfully")
    return _llm

# ── 请求/响应模型 ─────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

# ── 接口 ──────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "gpu": True,
        "model": "qwen2.5:72b-gb10",
        "backend": "llama_cpp",
        "cuda": "13.0",
        "arch": "Blackwell GB10",
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    llm = get_llm()
    t0 = time.time()
    try:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        resp = llm.create_chat_completion(
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            stream=False,
        )
        elapsed = time.time() - t0
        tokens  = resp["usage"]["completion_tokens"]
        speed   = round(tokens / elapsed, 2) if elapsed > 0 else 0

        return {
            "choices": resp["choices"],
            "usage":   resp["usage"],
            "model":   "qwen2.5:72b-gb10",
            "speed":   f"{speed} tokens/s",
        }
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/completions")
async def completions(body: dict):
    """兼容 OpenAI completions 格式"""
    llm = get_llm()
    prompt = body.get("prompt", "")
    resp = llm(
        prompt,
        max_tokens=body.get("max_tokens", 512),
        temperature=body.get("temperature", 0.7),
    )
    return resp

if __name__ == "__main__":
    logger.info("🚀 OfficeMind LLM Service starting on :8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
