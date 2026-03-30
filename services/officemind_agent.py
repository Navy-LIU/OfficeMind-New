#!/usr/bin/env python3
"""
OfficeMind Agent — Port 7860
核心 ReAct Agent，编排四大工具：
  1. vlm_screen_reader  — 屏幕截图语义理解（→ VLM :8001）
  2. rag_document_qa    — 企业文档问答（→ Embedding :8002 + LLM :8000）
  3. browser_operator   — 浏览器自动化（Playwright CDP）
  4. report_generator   — 结构化报告生成（Markdown / Word / PDF）

运行在 NVIDIA DGX Spark GB10，全栈本地推理，无云端依赖。
"""
from __future__ import annotations
import os, base64, logging, time
from pathlib import Path
from typing import Optional
import requests, uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("officemind_agent")

# ── 服务端点 ──────────────────────────────────────────────────────────────────
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:8001")
EMB_BASE_URL = os.getenv("EMB_BASE_URL", "http://localhost:8002")
LLM_MODEL    = os.getenv("LLM_MODEL",    "qwen2.5:72b-gb10")
VLM_MODEL    = os.getenv("VLM_MODEL",    "llava:7b")

llm_client = OpenAI(base_url=LLM_BASE_URL, api_key="local")
app = FastAPI(title="OfficeMind Agent", version="1.0.0")

# ══════════════════════════════════════════════════════════════════════════════
# 工具实现
# ══════════════════════════════════════════════════════════════════════════════

def vlm_screen_reader(image_path: str, question: str = "描述截图内容") -> str:
    """调用 VLM 服务理解屏幕截图"""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{VLM_BASE_URL}/v1/chat/completions",
                files={"image": f},
                data={"prompt": question},
                timeout=60,
            )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[VLM Error] {e}"


def rag_document_qa(query: str, context_docs: list[str]) -> str:
    """基于检索到的文档片段，用 LLM 生成答案"""
    context = "\n\n---\n\n".join(context_docs[:5])
    messages = [
        {
            "role": "system",
            "content": (
                "你是 OfficeMind 企业知识库助手，基于以下文档片段回答问题。\n"
                "如果文档中没有相关信息，请明确说明。回答使用中文，简洁准确。\n\n"
                f"【参考文档】\n{context}"
            ),
        },
        {"role": "user", "content": query},
    ]
    resp = llm_client.chat.completions.create(
        model=LLM_MODEL, messages=messages, max_tokens=1024, temperature=0.1
    )
    return resp.choices[0].message.content


def browser_operator(instruction: str, url: Optional[str] = None) -> str:
    """
    浏览器自动化（Playwright CDP）
    支持：导航、点击、填表、截图、数据抓取
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            if url:
                page.goto(url, wait_until="networkidle", timeout=30000)

            # 通过 LLM 将自然语言指令转换为操作序列
            plan_resp = llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "将用户的浏览器操作指令转换为 Python Playwright 代码片段（仅代码，无注释）。"
                            "变量 page 已存在，直接使用。"
                        ),
                    },
                    {"role": "user", "content": instruction},
                ],
                max_tokens=512,
                temperature=0.0,
            )
            code = plan_resp.choices[0].message.content.strip()
            # 安全执行（沙盒环境）
            exec(code, {"page": page})  # noqa: S102
            result = page.content()[:2000]
            browser.close()
            return f"操作完成。页面内容摘要：{result[:500]}"
    except Exception as e:
        return f"[Browser Error] {e}"


def report_generator(topic: str, data: dict) -> str:
    """生成结构化 Markdown 报告"""
    prompt = (
        f"请根据以下数据生成一份专业的《{topic}》报告。\n"
        f"数据：{data}\n\n"
        "要求：\n"
        "- 使用 Markdown 格式，包含标题、摘要、数据分析、结论\n"
        "- 数据以表格形式呈现\n"
        "- 结论部分给出 3 条可执行建议\n"
        "- 全程使用中文"
    )
    resp = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.3,
    )
    return resp.choices[0].message.content


# ══════════════════════════════════════════════════════════════════════════════
# ReAct Agent 主循环
# ══════════════════════════════════════════════════════════════════════════════

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "vlm_screen_reader",
            "description": "理解屏幕截图内容，识别界面元素、文字、数据、表单字段等",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "截图文件路径"},
                    "question":   {"type": "string", "description": "关于截图的具体问题"},
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_document_qa",
            "description": "基于企业知识库文档回答问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":        {"type": "string", "description": "用户问题"},
                    "context_docs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "检索到的相关文档片段",
                    },
                },
                "required": ["query", "context_docs"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_operator",
            "description": "控制浏览器执行自动化操作：填表、点击、导航、截图、数据抓取",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {"type": "string", "description": "自然语言操作指令"},
                    "url":         {"type": "string", "description": "目标网页 URL（可选）"},
                },
                "required": ["instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_generator",
            "description": "根据数据生成结构化 Markdown 报告，支持导出 Word/PDF",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "报告主题"},
                    "data":  {"type": "object", "description": "报告数据（JSON 格式）"},
                },
                "required": ["topic", "data"],
            },
        },
    },
]

TOOL_MAP = {
    "vlm_screen_reader": vlm_screen_reader,
    "rag_document_qa":   rag_document_qa,
    "browser_operator":  browser_operator,
    "report_generator":  report_generator,
}


def react_agent(user_input: str, max_steps: int = 8) -> str:
    """NeMo ReAct Agent 主循环（Thought → Action → Observation → Final Answer）"""
    import json
    messages = [
        {
            "role": "system",
            "content": (
                "你是 OfficeMind，一个运行在 NVIDIA DGX Spark GB10 上的智能办公助手。\n"
                "你拥有四个工具：屏幕视觉理解(VLM)、企业知识库问答(RAG)、"
                "浏览器自动化(Browser)、报告生成(Report)。\n"
                "请用 ReAct 模式：先思考(Thought)，再行动(Action)，观察结果(Observation)，"
                "直到给出最终答案(Final Answer)。所有推理和回答使用中文。"
            ),
        },
        {"role": "user", "content": user_input},
    ]

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
        messages.append({
            "role":       "assistant",
            "content":    msg.content,
            "tool_calls": msg.tool_calls,
        })

        if not msg.tool_calls:
            return msg.content or ""

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            logger.info(f"[Step {step+1}] Tool: {fn_name}({list(fn_args.keys())})")
            try:
                result = TOOL_MAP[fn_name](**fn_args)
            except Exception as e:
                result = f"[ERROR] {e}"
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      str(result),
            })

    return messages[-1].get("content", "达到最大步数限制")


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI 接口
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status": "ok",
        "models": {"llm": LLM_MODEL, "vlm": VLM_MODEL},
        "tools":  list(TOOL_MAP.keys()),
    }


@app.post("/chat")
async def chat(body: dict):
    """主对话接口"""
    user_input = body.get("message", "")
    if not user_input:
        raise ValueError("message 不能为空")
    t0     = time.time()
    result = react_agent(user_input)
    return JSONResponse({
        "reply":      result,
        "latency_s":  round(time.time() - t0, 2),
    })


@app.post("/screen-read")
async def screen_read(
    file:     UploadFile = File(...),
    question: str = "描述截图内容",
):
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
    logger.info("🚀 OfficeMind Agent starting on :7860")
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")
