"""
OfficeMind — Enterprise AI Office Automation
=========================================================
Built on NVIDIA DGX Spark GB10 (128GB Unified Memory)
Model: Qwen3-80B-A3B-Thinking (local, $HOME/models)
Stack:
  ① LangGraph Agent + HITL          ← langgraph_engine.py
  ② VLM Screen Reader (Qwen-VL)     ← vision_engine.py
  ③ Playwright Browser Operator     ← automation_engine.py + browser/
  ④ 4-Layer RAG Pipeline            ← rag_engine_enhanced.py
  ⑤ NemoClaw OpenShell Sandbox      ← secure execution environment
  ⑥ FastAPI REST + WebSocket        ← this file
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel

# ── Local skill modules (from manus-skills + openclaw-my-browser-operator) ──
sys.path.insert(0, str(Path(__file__).parent))
from core_integration import IntelligentAutomationSystem
from langgraph_engine import LangGraphAgent
from rag_engine_enhanced import EnhancedRAGEngine
from vision_engine import VisionEngine
from automation_engine import AutomationEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("OfficeMind")

# ── Config ────────────────────────────────────────────────────────────────────
MODELS_DIR   = "$HOME/models"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_MODEL    = os.getenv("LLM_MODEL", "Qwen3-Thinking")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "EMPTY")
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:8001/v1")
APP_PORT     = int(os.getenv("APP_PORT", "8080"))

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="OfficeMind API",
    description="NVIDIA DGX Spark GB10 · Enterprise AI Office Automation",
    version="1.0.0",
    docs_url="/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global instances (lazy init) ──────────────────────────────────────────────
_llm_client: Optional[AsyncOpenAI] = None
_agent: Optional[LangGraphAgent] = None
_rag: Optional[EnhancedRAGEngine] = None
_vision: Optional[VisionEngine] = None
_automation: Optional[AutomationEngine] = None
_system: Optional[IntelligentAutomationSystem] = None


def get_llm_client() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _llm_client


def get_agent() -> LangGraphAgent:
    global _agent
    if _agent is None:
        _agent = LangGraphAgent(
            llm_model=LLM_MODEL,
            llm_api_key=LLM_API_KEY,
            llm_base_url=LLM_BASE_URL,
            hitl_timeout_s=120.0,
            audit_log_path="./logs/agent_audit.jsonl",
        )
    return _agent


def get_rag() -> Optional[EnhancedRAGEngine]:
    global _rag
    if _rag is None:
        try:
            from sentence_transformers import SentenceTransformer
            embed_model = SentenceTransformer(
                f"{MODELS_DIR}/BAAI/bge-m3",
                device="cuda",
            )
            def embed_fn(texts: List[str]) -> List[List[float]]:
                return embed_model.encode(texts, normalize_embeddings=True).tolist()
            _rag = EnhancedRAGEngine(
                embed_fn=embed_fn,
                persist_dir=f"{MODELS_DIR}/officemind/chroma_db",
            )
            logger.info("RAG engine initialized with BGE-M3")
        except Exception as e:
            logger.warning("RAG init failed (BGE-M3 not ready?): %s", e)
    return _rag


# ── Request / Response Models ─────────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str
    context: Optional[str] = ""
    session_id: Optional[str] = "default"
    use_hitl: Optional[bool] = False
    use_rag: Optional[bool] = False

class TaskResponse(BaseModel):
    result: str
    thinking: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: float
    model: str
    session_id: str

class EmailRequest(BaseModel):
    email_text: str
    language: Optional[str] = "zh"

class ReportRequest(BaseModel):
    data: str
    report_type: Optional[str] = "daily"
    format: Optional[str] = "markdown"

class DocQARequest(BaseModel):
    question: str
    document: str
    use_rag: Optional[bool] = False

class BrowserTaskRequest(BaseModel):
    task: str
    url: Optional[str] = None
    cdp_port: Optional[int] = 9222

class HITLDecision(BaseModel):
    session_id: str
    decision: str        # "approve" | "reject" | "modify"
    feedback: Optional[str] = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "OfficeMind",
        "version": "1.0.0",
        "model": LLM_MODEL,
        "llm_url": LLM_BASE_URL,
        "platform": "NVIDIA DGX Spark GB10",
    }


@app.get("/models")
async def list_models():
    """List available local models."""
    models = []
    for d in Path(MODELS_DIR).iterdir():
        if d.is_dir():
            config = d / "config.json"
            models.append({
                "name": d.name,
                "path": str(d),
                "has_config": config.exists(),
                "size_gb": round(sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1e9, 1),
            })
    return {"models": models, "count": len(models)}


@app.post("/api/task", response_model=TaskResponse)
async def process_task(req: TaskRequest):
    """
    Core task endpoint. Routes through LangGraph Agent with optional HITL + RAG.
    Uses local Qwen3-80B-A3B-Thinking on DGX Spark GB10.
    """
    t0 = time.perf_counter()
    agent = get_agent()

    # Optionally enrich context with RAG
    context = req.context or ""
    if req.use_rag:
        rag = get_rag()
        if rag:
            rag_result = rag.query(req.task)
            context += f"\n\n[知识库检索结果]\n{rag_result.get('context', '')[:1000]}"

    full_query = f"{req.task}\n\n{context}".strip() if context else req.task

    try:
        result = await agent.run(full_query, req.session_id or "default")
    except Exception as e:
        logger.error("Agent error: %s", e)
        # Fallback: direct LLM call
        client = get_llm_client()
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是 OfficeMind，企业级 AI 办公自动化助手。"},
                {"role": "user", "content": full_query},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        result = {"final_answer": resp.choices[0].message.content, "confidence": 0.9}

    latency = (time.perf_counter() - t0) * 1000
    return TaskResponse(
        result=result.get("final_answer", str(result)),
        thinking=result.get("draft_answer"),
        confidence=result.get("confidence"),
        latency_ms=latency,
        model=LLM_MODEL,
        session_id=req.session_id or "default",
    )


@app.post("/api/email/summarize")
async def summarize_email(req: EmailRequest):
    """
    Summarize email: extract action items, deadlines, required responses.
    """
    t0 = time.perf_counter()
    client = get_llm_client()
    prompt = f"""请对以下邮件进行专业分析，输出 JSON 格式：
{{
  "summary": "一句话摘要",
  "action_items": ["行动项1", "行动项2"],
  "deadlines": ["截止日期1"],
  "required_response": "是否需要回复及建议回复要点",
  "priority": "high/medium/low",
  "sentiment": "positive/neutral/negative"
}}

邮件内容：
{req.email_text}"""

    resp = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是企业邮件处理专家，擅长快速提取关键信息。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.05,
        max_tokens=1024,
    )
    raw = resp.choices[0].message.content
    latency = (time.perf_counter() - t0) * 1000

    # Try parse JSON
    import re
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(m.group()) if m else {"raw": raw}
    except Exception:
        parsed = {"raw": raw}

    return {"result": parsed, "latency_ms": latency, "model": LLM_MODEL}


@app.post("/api/report/generate")
async def generate_report(req: ReportRequest):
    """
    Generate professional report from raw data.
    Supports: daily | weekly | meeting | sales | project
    """
    t0 = time.perf_counter()
    client = get_llm_client()

    report_templates = {
        "daily": "日报（今日工作总结、完成情况、明日计划、风险提示）",
        "weekly": "周报（本周成果、关键指标、下周计划、资源需求）",
        "meeting": "会议纪要（议题、讨论要点、决议事项、责任人、截止日期）",
        "sales": "销售报告（销售额、转化率、客户分析、竞品对比、建议）",
        "project": "项目进度报告（里程碑、完成度、风险、预算、下步行动）",
    }
    template_desc = report_templates.get(req.report_type, "专业报告")

    prompt = f"""请根据以下数据生成一份专业的{template_desc}。
要求：
- 结构清晰，层次分明
- 使用 Markdown 格式
- 包含执行摘要、详细分析、结论与建议
- 数据要有具体数字支撑
- 语言专业、简洁

原始数据：
{req.data}"""

    resp = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是专业的企业报告撰写专家，擅长将原始数据转化为清晰的管理报告。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=3000,
    )
    content = resp.choices[0].message.content
    latency = (time.perf_counter() - t0) * 1000

    # Save to file
    output_dir = Path("./output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    report_path = output_dir / f"{req.report_type}_report_{ts}.md"
    report_path.write_text(content, encoding="utf-8")

    return {
        "result": content,
        "saved_to": str(report_path),
        "latency_ms": latency,
        "model": LLM_MODEL,
        "report_type": req.report_type,
    }


@app.post("/api/document/qa")
async def document_qa(req: DocQARequest):
    """
    Document Q&A with optional RAG retrieval.
    Uses 4-layer RAG: Semantic Chunking → HyDE → Hybrid Search → MMR Reranking
    """
    t0 = time.perf_counter()
    context = req.document[:6000]
    rag_context = ""

    if req.use_rag:
        rag = get_rag()
        if rag:
            rag_result = rag.query(req.question)
            rag_context = f"\n\n[RAG 检索补充]\n{rag_result.get('context', '')[:2000]}"

    client = get_llm_client()
    prompt = f"""请基于以下文档内容，精确回答问题。
要求：
- 答案必须来自文档，不要编造
- 引用相关段落支撑答案
- 如果文档中没有答案，明确说明

问题：{req.question}

文档内容：
{context}{rag_context}"""

    resp = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是文档分析专家，擅长从文档中精确提取和推理信息。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.05,
        max_tokens=2048,
    )
    latency = (time.perf_counter() - t0) * 1000
    return {
        "answer": resp.choices[0].message.content,
        "latency_ms": latency,
        "model": LLM_MODEL,
        "rag_used": req.use_rag,
    }


@app.post("/api/browser/task")
async def browser_task(req: BrowserTaskRequest):
    """
    Execute browser automation task via CDP (Chrome DevTools Protocol).
    Reuses user's real browser session — no re-login needed.
    Powered by: openclaw-my-browser-operator
    """
    from browser.cdp import CDPEngine, CDPConfig
    from browser.agent import BrowserAgent, AgentConfig

    t0 = time.perf_counter()
    config = CDPConfig(port=req.cdp_port or 9222)
    engine = CDPEngine(config)

    try:
        await engine.connect()
        page = await engine.active_page()
        if req.url:
            from browser.tools import navigate
            await navigate(page, req.url)

        agent = BrowserAgent(
            page,
            AgentConfig(
                llm_model=LLM_MODEL,
                llm_api_key=LLM_API_KEY,
                llm_base_url=LLM_BASE_URL,
            ),
        )
        result = await agent.run(req.task)
        latency = (time.perf_counter() - t0) * 1000
        return {"result": result, "latency_ms": latency, "status": "success"}
    except Exception as e:
        logger.error("Browser task failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Browser task failed: {e}")
    finally:
        try:
            await engine.disconnect()
        except Exception:
            pass


@app.post("/api/hitl/decide")
async def hitl_decide(req: HITLDecision):
    """
    Human-in-the-Loop decision endpoint.
    Resume a paused LangGraph agent with human decision.
    """
    agent = get_agent()
    try:
        result = await agent.resume_with_human_decision(
            session_id=req.session_id,
            decision=req.decision,
            feedback=req.feedback or "",
        )
        return {"status": "resumed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """
    WebSocket streaming chat endpoint.
    Streams Qwen3-Thinking tokens in real-time.
    """
    await ws.accept()
    client = get_llm_client()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            user_msg = msg.get("message", "")
            session_id = msg.get("session_id", "ws-default")

            await ws.send_text(json.dumps({"type": "start", "session_id": session_id}))

            try:
                stream = await client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "你是 OfficeMind，专注于企业办公自动化的 AI 助手，运行在 NVIDIA DGX Spark GB10 上。"},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        await ws.send_text(json.dumps({"type": "token", "content": delta}))

                await ws.send_text(json.dumps({"type": "done"}))

            except Exception as e:
                await ws.send_text(json.dumps({"type": "error", "message": str(e)}))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("OfficeMind starting on DGX Spark GB10...")
    logger.info("LLM: %s @ %s", LLM_MODEL, LLM_BASE_URL)
    Path("./logs").mkdir(exist_ok=True)
    Path("./output/reports").mkdir(parents=True, exist_ok=True)
    # Pre-warm agent
    try:
        get_agent()
        logger.info("LangGraph Agent initialized ✓")
    except Exception as e:
        logger.warning("Agent pre-warm failed: %s", e)


@app.on_event("shutdown")
async def shutdown():
    global _automation
    if _automation:
        await _automation.stop()
    logger.info("OfficeMind shutdown complete")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "officemind_app:app",
        host="0.0.0.0",
        port=APP_PORT,
        log_level="info",
        reload=False,
        workers=1,
    )
