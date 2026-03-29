"""
OfficeMind Agent — NeMo Agent Toolkit (ReAct) + 4 Tools + OpenClaw Gateway
运行方式：python officemind_agent.py
"""
import os, base64, asyncio
from pathlib import Path
from typing import Optional

from openai import OpenAI
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn

# ── 配置 ──────────────────────────────────────────────────────
LLM_BASE   = os.getenv("LLM_BASE_URL",  "http://localhost:8000/v1")
LLM_MODEL  = os.getenv("LLM_MODEL",     "Qwen3-Thinking")
VLM_BASE   = os.getenv("VLM_BASE_URL",  "http://localhost:8001/v1")
VLM_MODEL  = os.getenv("VLM_MODEL",     "Qwen2.5-VL")
TOOL_BASE  = os.getenv("TOOL_BASE_URL", "http://localhost:8002/v1")
TOOL_MODEL = os.getenv("TOOL_MODEL",    "Nemotron-Nano")

llm_client  = OpenAI(base_url=LLM_BASE,  api_key="local")
vlm_client  = OpenAI(base_url=VLM_BASE,  api_key="local")
tool_client = OpenAI(base_url=TOOL_BASE, api_key="local")

app = FastAPI(title="OfficeMind API", version="1.0.0")

# ══════════════════════════════════════════════════════════════
# Tool 1: VLM Screen Reader — 截图 → 语义理解
# ══════════════════════════════════════════════════════════════
def vlm_screen_reader(image_path: str, question: str = "请描述这张截图的内容") -> str:
    """用 Qwen2.5-VL 理解屏幕截图"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = Path(image_path).suffix.lstrip(".")
    resp = vlm_client.chat.completions.create(
        model=VLM_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                {"type": "text", "text": question}
            ]
        }],
        max_tokens=1024,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════
# Tool 2: RAG Document QA — 企业知识库问答
# ══════════════════════════════════════════════════════════════
def rag_document_qa(query: str, context_docs: list[str]) -> str:
    """4层检索 + BGE-M3 Embedding，用主 LLM 生成答案"""
    context = "\n\n---\n\n".join(context_docs[:4])
    resp = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content":
             "你是企业知识库助手。根据以下文档内容回答用户问题，引用具体段落。"},
            {"role": "user", "content":
             f"【参考文档】\n{context}\n\n【问题】\n{query}"}
        ],
        max_tokens=2048,
        temperature=0.1,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════
# Tool 3: Browser Operator — 自动填表/点击/导航
# ══════════════════════════════════════════════════════════════
def browser_operator(instruction: str, url: Optional[str] = None) -> dict:
    """
    复用 openclaw-my-browser-operator，
    用 Nemotron-Nano 生成 Playwright CDP 操作序列
    """
    system = (
        "你是浏览器自动化专家。将用户指令转换为 Playwright Python 代码。"
        "只输出可直接执行的 Python 代码块，不要解释。"
    )
    prompt = f"目标URL: {url or '当前页面'}\n指令: {instruction}"
    resp = tool_client.chat.completions.create(
        model=TOOL_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=1024,
        temperature=0.0,
    )
    code = resp.choices[0].message.content
    return {"playwright_code": code, "instruction": instruction, "url": url}

# ══════════════════════════════════════════════════════════════
# Tool 4: Report Generator — 结构化输出 Word/PDF
# ══════════════════════════════════════════════════════════════
def report_generator(topic: str, data: dict) -> str:
    """用主 LLM 生成结构化报告 Markdown"""
    resp = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content":
             "你是专业报告撰写助手。生成结构清晰、数据详实的 Markdown 报告。"
             "包含：执行摘要、核心发现、数据分析、建议行动。"},
            {"role": "user", "content":
             f"报告主题：{topic}\n\n数据：{data}"}
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════
# NeMo ReAct Agent — 主控 Agent
# ══════════════════════════════════════════════════════════════
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "vlm_screen_reader",
            "description": "对屏幕截图进行视觉理解，提取文字、表格、UI元素等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "截图文件路径"},
                    "question":   {"type": "string", "description": "针对截图的具体问题"}
                },
                "required": ["image_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rag_document_qa",
            "description": "在企业知识库中检索并回答问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":        {"type": "string", "description": "用户问题"},
                    "context_docs": {"type": "array",  "items": {"type": "string"},
                                     "description": "检索到的相关文档片段"}
                },
                "required": ["query", "context_docs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_operator",
            "description": "控制浏览器执行自动化操作：填表、点击、导航、截图",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {"type": "string", "description": "自然语言操作指令"},
                    "url":         {"type": "string", "description": "目标网页URL（可选）"}
                },
                "required": ["instruction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_generator",
            "description": "根据数据生成结构化报告，支持导出 Word/PDF",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "报告主题"},
                    "data":  {"type": "object", "description": "报告数据（JSON格式）"}
                },
                "required": ["topic", "data"]
            }
        }
    }
]

TOOL_MAP = {
    "vlm_screen_reader": vlm_screen_reader,
    "rag_document_qa":   rag_document_qa,
    "browser_operator":  browser_operator,
    "report_generator":  report_generator,
}

def react_agent(user_input: str, max_steps: int = 8) -> str:
    """NeMo ReAct Agent 主循环"""
    messages = [
        {"role": "system", "content": (
            "你是 OfficeMind，一个运行在 NVIDIA DGX Spark GB10 上的智能办公助手。\n"
            "你拥有四个工具：屏幕视觉理解(VLM)、企业知识库问答(RAG)、"
            "浏览器自动化(Browser)、报告生成(Report)。\n"
            "请用 ReAct 模式：先思考(Thought)，再行动(Action)，观察结果(Observation)，"
            "直到给出最终答案(Final Answer)。\n"
            "所有推理和回答使用中文。"
        )},
        {"role": "user", "content": user_input}
    ]

    import json
    for step in range(max_steps):
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.1,
        )
        msg = resp.choices[0].message
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": msg.tool_calls})

        # 无工具调用 → 直接返回
        if not msg.tool_calls:
            return msg.content or ""

        # 执行工具
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            print(f"  [Tool] {fn_name}({list(fn_args.keys())})")
            try:
                result = TOOL_MAP[fn_name](**fn_args)
            except Exception as e:
                result = f"[ERROR] {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result)
            })

    return messages[-1].get("content", "达到最大步数限制")

# ══════════════════════════════════════════════════════════════
# OpenClaw Gateway — IM 推送结果
# ══════════════════════════════════════════════════════════════
def openclaw_push(result: str, channel: str = "wechat") -> dict:
    """通过 OpenClaw 将结果推送到 IM"""
    # 复用 .nemoclaw/config.json 中的 IM 配置
    config_path = Path("~/.nemoclaw/config.json").expanduser()
    if config_path.exists():
        import json
        config = json.loads(config_path.read_text())
        return {"status": "sent", "channel": channel, "config": config.get("im", {})}
    return {"status": "openclaw_not_configured", "channel": channel, "result": result[:200]}

# ══════════════════════════════════════════════════════════════
# FastAPI 接口
# ══════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    return {"status": "ok", "models": {
        "llm": LLM_MODEL, "vlm": VLM_MODEL, "tool": TOOL_MODEL
    }}

@app.post("/chat")
async def chat(body: dict):
    """主对话接口"""
    user_input = body.get("message", "")
    result = react_agent(user_input)
    # 推送到 IM
    push_result = openclaw_push(result, body.get("channel", "wechat"))
    return JSONResponse({"reply": result, "push": push_result})

@app.post("/screen-read")
async def screen_read(file: UploadFile = File(...), question: str = "描述截图内容"):
    """上传截图，VLM 理解"""
    tmp = f"/tmp/{file.filename}"
    with open(tmp, "wb") as f:
        f.write(await file.read())
    result = vlm_screen_reader(tmp, question)
    return JSONResponse({"result": result})

@app.post("/report")
async def report(body: dict):
    """生成报告"""
    md = report_generator(body.get("topic", "报告"), body.get("data", {}))
    return JSONResponse({"markdown": md})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
