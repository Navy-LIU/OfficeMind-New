"""
OfficeMind Agent Orchestrator
Based on LangGraph StateGraph + NVIDIA DGX Spark GB10 local inference.
Routes tasks to: Email / Document QA / Report / Browser / HITL
"""
from __future__ import annotations
import os, json, logging
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

# ── LLM Client (points to local vLLM on DGX Spark) ───────────────────────────
def get_llm(model: str = "Qwen3-Thinking", temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("VLLM_API_KEY", "EMPTY"),
        temperature=temperature,
        max_tokens=4096,
    )

# ── Agent State ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    task_type: str          # email | document_qa | report | browser | general
    input_data: dict        # raw input payload
    result: dict            # final output
    confidence: float       # 0.0 - 1.0
    requires_hitl: bool     # human-in-the-loop flag
    hitl_reason: str        # why HITL is needed
    session_id: str

# ── Router Node ───────────────────────────────────────────────────────────────
ROUTER_PROMPT = """你是 OfficeMind 任务路由器，运行在 NVIDIA DGX Spark GB10 上。
分析用户输入，判断任务类型，返回 JSON：
{
  "task_type": "email|document_qa|report|browser|general",
  "confidence": 0.0-1.0,
  "requires_hitl": true/false,
  "hitl_reason": "原因（如不需要则为空）",
  "summary": "任务简述"
}

任务类型说明：
- email: 邮件分析、回复草稿、行动项提取
- document_qa: 文档问答、合同分析、知识检索
- report: 日报/周报/会议纪要/销售报告生成
- browser: 网页操作、表单填写、数据抓取
- general: 其他通用问答

当 confidence < 0.75 时，设置 requires_hitl=true。
"""

def router_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.0)
    last_msg = state["messages"][-1].content if state["messages"] else ""
    
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=f"用户输入：{last_msg}")
    ])
    
    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except json.JSONDecodeError:
        # Fallback: extract JSON from response
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        result = json.loads(match.group()) if match else {
            "task_type": "general", "confidence": 0.5,
            "requires_hitl": True, "hitl_reason": "路由解析失败", "summary": ""
        }
    
    logger.info(f"Router: {result}")
    return {
        **state,
        "task_type": result.get("task_type", "general"),
        "confidence": result.get("confidence", 0.5),
        "requires_hitl": result.get("requires_hitl", False),
        "hitl_reason": result.get("hitl_reason", ""),
    }

def route_decision(state: AgentState) -> str:
    if state.get("requires_hitl") and state.get("confidence", 1.0) < 0.75:
        return "hitl"
    return state.get("task_type", "general")

# ── Email Node ────────────────────────────────────────────────────────────────
EMAIL_PROMPT = """你是企业邮件智能助手，运行在 NVIDIA DGX Spark GB10 本地推理。
任务：分析邮件内容，提取关键信息。

输出格式（JSON）：
{
  "summary": "邮件摘要（2-3句）",
  "action_items": [{"task": "任务描述", "deadline": "截止日期", "owner": "负责人"}],
  "priority": "high|medium|low",
  "sentiment": "positive|neutral|negative",
  "suggested_reply": "建议回复草稿（如适用）",
  "key_dates": ["重要日期列表"]
}
"""

def email_node(state: AgentState) -> AgentState:
    llm = get_llm()
    last_msg = state["messages"][-1].content
    
    response = llm.invoke([
        SystemMessage(content=EMAIL_PROMPT),
        HumanMessage(content=last_msg)
    ])
    
    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except:
        result = {"raw_response": response.content}
    
    # Format for display
    display = _format_email_result(result)
    return {
        **state,
        "result": result,
        "messages": state["messages"] + [AIMessage(content=display)]
    }

def _format_email_result(r: dict) -> str:
    lines = ["## 📧 邮件分析报告\n"]
    if "summary" in r:
        lines.append(f"**摘要**：{r['summary']}\n")
    if "priority" in r:
        emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(r["priority"], "⚪")
        lines.append(f"**优先级**：{emoji} {r['priority'].upper()}\n")
    if "action_items" in r and r["action_items"]:
        lines.append("**行动项**：")
        for i, item in enumerate(r["action_items"], 1):
            deadline = f"（截止：{item.get('deadline', '未指定')}）" if item.get('deadline') else ""
            lines.append(f"  {i}. {item.get('task', '')}{deadline}")
        lines.append("")
    if "key_dates" in r and r["key_dates"]:
        lines.append(f"**关键日期**：{', '.join(r['key_dates'])}\n")
    if "suggested_reply" in r and r["suggested_reply"]:
        lines.append(f"**建议回复**：\n> {r['suggested_reply']}\n")
    return "\n".join(lines)

# ── Document QA Node ──────────────────────────────────────────────────────────
DOC_QA_PROMPT = """你是企业文档智能问答助手，运行在 NVIDIA DGX Spark GB10。
基于提供的文档内容回答问题，要求：
1. 精确引用原文，标注来源段落
2. 如文档中无相关信息，明确说明
3. 对合同/法律文档，特别标注风险点
4. 输出结构化 Markdown 格式
"""

def document_qa_node(state: AgentState) -> AgentState:
    llm = get_llm()
    last_msg = state["messages"][-1].content
    context = state.get("input_data", {}).get("document_context", "")
    
    prompt = last_msg
    if context:
        prompt = f"文档内容：\n{context}\n\n问题：{last_msg}"
    
    response = llm.invoke([
        SystemMessage(content=DOC_QA_PROMPT),
        HumanMessage(content=prompt)
    ])
    
    return {
        **state,
        "result": {"answer": response.content},
        "messages": state["messages"] + [AIMessage(content=response.content)]
    }

# ── Report Node ───────────────────────────────────────────────────────────────
REPORT_PROMPT = """你是企业报告生成专家，运行在 NVIDIA DGX Spark GB10。
根据用户提供的数据和要求，生成专业的工作报告。

报告类型：日报 / 周报 / 月报 / 会议纪要 / 销售报告 / 项目进展报告

输出要求：
- 使用标准 Markdown 格式
- 包含：标题、日期、执行摘要、详细内容、数据分析、下一步计划
- 数据部分使用表格展示
- 语言专业、简洁、有力
"""

def report_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.2)
    last_msg = state["messages"][-1].content
    
    response = llm.invoke([
        SystemMessage(content=REPORT_PROMPT),
        HumanMessage(content=last_msg)
    ])
    
    return {
        **state,
        "result": {"report": response.content},
        "messages": state["messages"] + [AIMessage(content=response.content)]
    }

# ── Browser Node ──────────────────────────────────────────────────────────────
BROWSER_PROMPT = """你是浏览器自动化规划器，运行在 NVIDIA DGX Spark GB10。
将用户的自然语言指令转换为结构化的浏览器操作步骤。

输出 JSON：
{
  "steps": [
    {"action": "navigate|click|type|screenshot|extract", "target": "...", "value": "..."}
  ],
  "requires_confirmation": true/false,
  "risk_level": "low|medium|high",
  "estimated_duration": "预计耗时"
}

高风险操作（提交表单、付款、发送邮件）必须设置 requires_confirmation=true。
"""

def browser_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.0)
    last_msg = state["messages"][-1].content
    
    response = llm.invoke([
        SystemMessage(content=BROWSER_PROMPT),
        HumanMessage(content=last_msg)
    ])
    
    try:
        plan = json.loads(response.content.strip().strip("```json").strip("```"))
        if plan.get("requires_confirmation") or plan.get("risk_level") == "high":
            return {
                **state,
                "result": plan,
                "requires_hitl": True,
                "hitl_reason": f"浏览器操作需要确认（风险级别：{plan.get('risk_level')}）",
                "messages": state["messages"] + [AIMessage(
                    content=f"⚠️ 以下操作需要您确认：\n\n```json\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n```"
                )]
            }
    except:
        plan = {"raw": response.content}
    
    return {
        **state,
        "result": plan,
        "messages": state["messages"] + [AIMessage(content=f"浏览器操作计划已生成：\n{response.content}")]
    }

# ── General Node ──────────────────────────────────────────────────────────────
GENERAL_PROMPT = """你是 OfficeMind，企业 AI 办公助手，运行在 NVIDIA DGX Spark GB10（128GB 统一内存，Blackwell 架构）。
你的核心能力：邮件智能处理、文档问答（RAG）、报告自动生成、浏览器自动化、人工兜底审批。
请用专业、简洁的中文回答用户问题。"""

def general_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.3)
    response = llm.invoke([SystemMessage(content=GENERAL_PROMPT)] + state["messages"])
    return {
        **state,
        "result": {"response": response.content},
        "messages": state["messages"] + [AIMessage(content=response.content)]
    }

# ── HITL Node ─────────────────────────────────────────────────────────────────
def hitl_node(state: AgentState) -> AgentState:
    reason = state.get("hitl_reason", "置信度不足，需要人工确认")
    msg = (
        f"⚠️ **需要人工审批**\n\n"
        f"原因：{reason}\n\n"
        f"置信度：{state.get('confidence', 0):.0%}\n\n"
        f"请确认是否继续执行，或提供更多信息。"
    )
    return {
        **state,
        "result": {"status": "pending_human_review", "reason": reason},
        "messages": state["messages"] + [AIMessage(content=msg)]
    }

# ── Build Graph ───────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    graph.add_node("router", router_node)
    graph.add_node("email", email_node)
    graph.add_node("document_qa", document_qa_node)
    graph.add_node("report", report_node)
    graph.add_node("browser", browser_node)
    graph.add_node("general", general_node)
    graph.add_node("hitl", hitl_node)
    
    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "email": "email",
            "document_qa": "document_qa",
            "report": "report",
            "browser": "browser",
            "general": "general",
            "hitl": "hitl",
        }
    )
    
    for node in ["email", "document_qa", "report", "browser", "general", "hitl"]:
        graph.add_edge(node, END)
    
    return graph.compile()

# Singleton
_app = None

def get_app():
    global _app
    if _app is None:
        _app = build_graph()
    return _app

async def run_agent(message: str, session_id: str = "default",
                    input_data: dict = None) -> dict:
    app = get_app()
    state = AgentState(
        messages=[HumanMessage(content=message)],
        task_type="",
        input_data=input_data or {},
        result={},
        confidence=1.0,
        requires_hitl=False,
        hitl_reason="",
        session_id=session_id,
    )
    result = await app.ainvoke(state)
    return {
        "session_id": session_id,
        "task_type": result["task_type"],
        "confidence": result["confidence"],
        "requires_hitl": result["requires_hitl"],
        "result": result["result"],
        "response": result["messages"][-1].content if result["messages"] else "",
    }
