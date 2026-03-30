#!/usr/bin/env python3
"""
OfficeMind VLM Service — Port 8001
Model  : llava:7b via Ollama (GPU accelerated)
Backend: Ollama v0.18.3 + CUDA 13 symlinks → GB10 Blackwell

Endpoints:
  POST /v1/chat/completions   — OpenAI-compatible multimodal chat
  POST /v1/vision/describe    — OfficeMind screen analysis (4 task types)
  GET  /health                — Service health check
"""
from __future__ import annotations
import base64, time, logging
import requests
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vlm_service")

app = FastAPI(title="OfficeMind VLM Service", version="1.0.0")

OLLAMA_URL = "http://localhost:11434"
VLM_MODEL  = "llava:7b"

# ── 工具函数 ──────────────────────────────────────────────────────────────────
def ollama_ready() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).status_code == 200
    except Exception:
        return False

def infer(prompt: str, img_b64: str, num_gpu: int = 99, temperature: float = 0.1) -> dict:
    t0 = time.time()
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model":  VLM_MODEL,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "options": {
                "num_gpu":     num_gpu,
                "num_ctx":     4096,
                "temperature": temperature,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    d = resp.json()
    elapsed = time.time() - t0
    return {
        "response":       d["response"],
        "eval_count":     d.get("eval_count", 0),
        "latency_s":      round(elapsed, 2),
        "eval_duration_ms": round(d.get("eval_duration", 0) / 1e6, 0),
    }

# ── 接口 ──────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    ok = ollama_ready()
    return {
        "status":         "ok" if ok else "degraded",
        "model":          VLM_MODEL,
        "ollama_running": ok,
        "gpu":            True,
        "backend":        "ollama-0.18.3",
        "endpoints":      ["/v1/chat/completions", "/v1/vision/describe"],
    }

@app.post("/v1/chat/completions")
async def vlm_chat(
    image:  UploadFile = File(...),
    prompt: str = Form(default="请详细描述这张图片的内容，包括文字、界面元素、数据等所有可见信息。"),
):
    if not ollama_ready():
        return JSONResponse({"error": "Ollama 服务未运行，请先执行 scripts/start_ollama_gpu.sh"}, status_code=503)

    img_b64 = base64.b64encode(await image.read()).decode("utf-8")
    result  = infer(prompt, img_b64)

    return {
        "choices": [{"message": {"content": result["response"]}}],
        "model":   VLM_MODEL,
        "backend": "ollama-gpu",
        "latency_s":        result["latency_s"],
        "eval_count":       result["eval_count"],
        "eval_duration_ms": result["eval_duration_ms"],
    }

@app.post("/v1/vision/describe")
async def describe_screen(
    image: UploadFile = File(...),
    task:  str = Form(default="screen_analysis"),
):
    """
    OfficeMind 专用屏幕理解接口，支持四种任务类型：
      - screen_analysis : 全面分析屏幕内容
      - form_fill       : 识别表单字段（JSON 格式返回）
      - data_extract    : 提取数字/表格/关键数据
      - error_detect    : 检测错误/警告/异常状态
    """
    PROMPTS = {
        "screen_analysis": (
            "分析这个屏幕截图：\n"
            "1) 界面类型（网页/桌面应用/终端等）\n"
            "2) 主要内容摘要\n"
            "3) 可操作的 UI 元素（按钮/输入框/链接）\n"
            "4) 需要关注的数据或文字\n"
            "请用中文结构化回答。"
        ),
        "form_fill": (
            "识别图中所有表单字段的名称和当前值，"
            "以 JSON 格式返回，格式：{\"字段名\": \"当前值\", ...}"
        ),
        "data_extract": (
            "提取图中所有数字、表格、关键数据，"
            "以结构化 Markdown 格式返回，包含表头和数据行。"
        ),
        "error_detect": (
            "检查图中是否有错误提示、警告信息或异常状态，"
            "详细描述每一个问题及其位置。若无异常，回答「正常」。"
        ),
    }
    prompt = PROMPTS.get(task, PROMPTS["screen_analysis"])

    if not ollama_ready():
        return JSONResponse({"error": "Ollama 服务未运行"}, status_code=503)

    img_b64 = base64.b64encode(await image.read()).decode("utf-8")
    result  = infer(prompt, img_b64, temperature=0.0)

    return {
        "task":     task,
        "analysis": result["response"],
        "model":    VLM_MODEL,
        "gpu":      True,
        "latency_s": result["latency_s"],
    }

if __name__ == "__main__":
    logger.info("🚀 OfficeMind VLM Service starting on :8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
