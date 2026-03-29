"""
OfficeMind FastAPI Application
Provides REST API for all office automation capabilities.
"""
from __future__ import annotations
import os, logging, time, uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Pydantic Models ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    context: Optional[Dict[str, Any]] = None

class EmailRequest(BaseModel):
    subject: str
    body: str
    sender: str = ""
    recipients: List[str] = []

class ReportRequest(BaseModel):
    report_type: str  # daily | weekly | meeting | sales
    data: str
    title: str = ""
    date: str = ""

class RAGIngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

class RAGQueryRequest(BaseModel):
    question: str
    k: int = 5
    use_hyde: bool = True

class BrowserRequest(BaseModel):
    instruction: str
    url: str = ""
    require_confirmation: bool = True

# ── App Lifespan ──────────────────────────────────────────────────────────────
_rag_pipeline = None
_agent_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag_pipeline, _agent_app
    logger.info("OfficeMind starting up on DGX Spark GB10...")
    
    # Initialize RAG pipeline
    try:
        from src.rag.pipeline import RAGPipeline
        _rag_pipeline = RAGPipeline(persist_dir="./data/chroma_db")
        logger.info("RAG pipeline initialized")
    except Exception as e:
        logger.warning(f"RAG pipeline init failed: {e}")
    
    # Initialize Agent
    try:
        from src.agent.orchestrator import get_app
        _agent_app = get_app()
        logger.info("Agent orchestrator initialized")
    except Exception as e:
        logger.warning(f"Agent init failed: {e}")
    
    yield
    logger.info("OfficeMind shutting down...")

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="OfficeMind API",
    description="企业级全栈 AI 自动化办公助手 — NVIDIA DGX Spark GB10",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health & Info ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "OfficeMind",
        "version": "1.0.0",
        "platform": "NVIDIA DGX Spark GB10",
        "gpu": "NVIDIA GB10 Blackwell (128GB unified memory)",
        "models": {
            "llm": "Qwen3-next-80b-a3b-thinking (local)",
            "vlm": "Qwen2.5-VL-7B-Instruct (local)",
            "embedding": "Qwen3-Embedding (local)",
        },
        "capabilities": ["email_analysis", "document_qa", "report_generation",
                         "browser_automation", "hitl_approval"],
    }

@app.get("/health")
async def health():
    vllm_ok = False
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                os.getenv("VLLM_BASE_URL", "http://localhost:8000") + "/health",
                timeout=3.0
            )
            vllm_ok = r.status_code == 200
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "vllm": "online" if vllm_ok else "offline",
        "rag": "ready" if _rag_pipeline else "unavailable",
        "agent": "ready" if _agent_app else "unavailable",
        "timestamp": time.time(),
    }

# ── Chat / Agent ──────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint — routes to appropriate agent node."""
    try:
        from src.agent.orchestrator import run_agent
        result = await run_agent(
            message=req.message,
            session_id=req.session_id,
            input_data=req.context or {},
        )
        return result
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(500, str(e))

# ── Email Analysis ────────────────────────────────────────────────────────────
@app.post("/email/analyze")
async def analyze_email(req: EmailRequest):
    """Analyze email: extract action items, priority, suggested reply."""
    try:
        from src.agent.orchestrator import run_agent
        message = (
            f"请分析以下邮件：\n"
            f"发件人：{req.sender}\n"
            f"收件人：{', '.join(req.recipients)}\n"
            f"主题：{req.subject}\n"
            f"正文：\n{req.body}"
        )
        result = await run_agent(message=message, session_id=str(uuid.uuid4()))
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

# ── Report Generation ─────────────────────────────────────────────────────────
@app.post("/report/generate")
async def generate_report(req: ReportRequest):
    """Generate structured work report from raw data."""
    type_map = {
        "daily": "日报", "weekly": "周报",
        "meeting": "会议纪要", "sales": "销售报告"
    }
    report_type_cn = type_map.get(req.report_type, req.report_type)
    
    try:
        from src.agent.orchestrator import run_agent
        message = (
            f"请生成{report_type_cn}。\n"
            f"标题：{req.title or f'工作{report_type_cn}'}\n"
            f"日期：{req.date or '今日'}\n"
            f"数据：\n{req.data}"
        )
        result = await run_agent(message=message, session_id=str(uuid.uuid4()))
        return {
            "report_type": req.report_type,
            "content": result.get("response", ""),
            "session_id": result.get("session_id", ""),
        }
    except Exception as e:
        raise HTTPException(500, str(e))

# ── RAG Document QA ───────────────────────────────────────────────────────────
@app.post("/rag/ingest")
async def ingest_document(req: RAGIngestRequest):
    """Add text to knowledge base."""
    if not _rag_pipeline:
        raise HTTPException(503, "RAG pipeline not available")
    try:
        count = _rag_pipeline.ingest(req.text, req.metadata)
        return {"chunks_added": count, "status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/rag/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Upload and ingest a document file (PDF, DOCX, TXT)."""
    if not _rag_pipeline:
        raise HTTPException(503, "RAG pipeline not available")
    
    import tempfile, shutil
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        count = _rag_pipeline.ingest_file(tmp_path)
        return {"filename": file.filename, "chunks_added": count, "status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        os.unlink(tmp_path)

@app.post("/rag/query")
async def query_rag(req: RAGQueryRequest):
    """Query knowledge base with 4-layer RAG pipeline."""
    if not _rag_pipeline:
        raise HTTPException(503, "RAG pipeline not available")
    try:
        result = _rag_pipeline.query(req.question, k=req.k, use_hyde=req.use_hyde)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

# ── Browser Automation ────────────────────────────────────────────────────────
@app.post("/browser/execute")
async def browser_execute(req: BrowserRequest):
    """Execute browser automation from natural language instruction."""
    try:
        from src.browser.operator import NLPActionParser, BrowserOperator, BrowserAction
        
        parser = NLPActionParser()
        actions = parser.parse(req.instruction)
        
        if not actions:
            raise HTTPException(400, "无法解析浏览器操作指令")
        
        # Check for high-risk actions
        high_risk = ["submit", "click #submit", "click button[type=submit]"]
        has_risk = any(
            any(r in a.target.lower() for r in high_risk)
            for a in actions
        )
        
        if has_risk and req.require_confirmation:
            return {
                "status": "pending_confirmation",
                "actions": [{"action": a.action, "target": a.target, 
                             "value": a.value, "description": a.description}
                            for a in actions],
                "message": "包含高风险操作，请确认后执行",
            }
        
        async with BrowserOperator(headless=True) as browser:
            results = await browser.execute(actions)
            return {
                "status": "completed",
                "results": [
                    {"action": r.action, "success": r.success,
                     "error": r.error, "latency_ms": round(r.latency_ms, 1)}
                    for r in results
                ],
                "audit_log": browser.get_audit_log(),
            }
    except Exception as e:
        raise HTTPException(500, str(e))

# ── Screen Analysis ───────────────────────────────────────────────────────────
@app.post("/vision/analyze")
async def analyze_screenshot(file: UploadFile = File(...), task: str = ""):
    """Analyze a screenshot using Qwen2.5-VL."""
    import tempfile, shutil
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        from src.vision.screen_reader import ScreenReader
        reader = ScreenReader(
            vlm_base_url=os.getenv("VLM_BASE_URL", "http://localhost:8001/v1")
        )
        result = reader.analyze_image_file(tmp_path, task_hint=task)
        return {
            "elements": result.elements,
            "suggested_action": result.suggested_action,
            "confidence": result.confidence,
            "latency_ms": round(result.latency_ms, 1),
        }
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        reload=False,
        log_level="info",
    )
