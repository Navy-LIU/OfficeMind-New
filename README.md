# OfficeMind — 企业级全栈 AI 自动化办公助手

> **NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛项目**
> 三层 Claw 架构 · vLLM 推理 · 全本地化部署 · 零云端依赖

[![Platform](https://img.shields.io/badge/Platform-NVIDIA%20DGX%20Spark%20GB10-76b900?style=for-the-badge&logo=nvidia)](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)
[![Engine](https://img.shields.io/badge/Engine-vLLM-76b900?style=for-the-badge&logo=nvidia)](https://github.com/vllm-project/vllm)
[![Framework](https://img.shields.io/badge/Framework-NemoClaw%20%2B%20OpenClaw-blue?style=for-the-badge)](https://github.com/HeKun-NVIDIA/nemoclaw_on_dgx_spark)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## 项目简介

OfficeMind 是一套完全运行在 **NVIDIA DGX Spark GB10**（Blackwell 架构，128GB 统一内存）上的企业级 AI 自动化办公助手。项目以 **RCClaw**（自研多通道网关）为顶层接入层，通过 **NemoClaw**（NVIDIA 官方 DGX Spark 插件）调度 **OpenClaw Agent 框架**，底层由 **vLLM** 提供高性能推理，实现邮件智能处理、企业文档问答（RAG）、屏幕视觉理解、浏览器自动化和结构化报告生成五大核心功能。

**全部模型本地化部署，零云端 API 依赖，数据不出节点。**

---

## 系统架构

```
用户指令（自然语言）
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  RCClaw 多通道网关层（自研）                                │
│  微信 · 飞书 · Telegram · HTTP API 统一接入                │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  NemoClaw 控制层（NVIDIA 官方 DGX Spark 插件）              │
│  OpenClaw Agent · LangGraph ReAct 路由 · HITL 人工审批     │
└──────┬───────────┬───────────┬───────────┬───────────────┘
       │           │           │           │
       ▼           ▼           ▼           ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
  │VLM 屏幕  │ │RAG 文档  │ │Browser  │ │Report   │
  │截图理解  │ │知识库    │ │浏览器   │ │报告生成  │
  │Qwen-VL  │ │4层检索   │ │Playwright│ │Word/PDF │
  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
       └───────────┴───────────┴────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  vLLM 推理层（高性能推理框架）                              │
│  Qwen3-80B :8000 · Qwen2.5-VL :8001 · BGE :8002          │
│  支持 CUDA 加速，充分利用 GB10 统一内存                     │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  NVIDIA DGX Spark GB10 硬件层                             │
│  Blackwell GPU · 128GB 统一内存 · aarch64                 │
└──────────────────────────────────────────────────────────┘
```

---

## 核心功能

### VLM 屏幕阅读器

基于 **Qwen2.5-VL-7B-Instruct**（本地 `:8001`），对屏幕截图进行语义理解，识别 UI 元素、表单字段和操作按钮，为浏览器自动化提供视觉感知能力。针对没有 API 的老旧系统，通过"看屏幕"实现自动化操作，突破传统 DOM 选择器的局限。

### RAG 企业文档问答

采用 **4 层检索架构**：BGE-M3 稠密向量召回 → BM25 稀疏关键词召回 → 候选合并去重 → BGE-Reranker-v2-m3 精排。支持 PDF、Word、Excel 等企业文档格式，检索精度显著优于单一向量检索。HyDE（假设性文档嵌入）技术进一步提升召回质量。

### 浏览器自动化

基于 **Playwright CDP** 实现自动填表、点击导航、数据抓取，结合 VLM 视觉理解实现无需 DOM 选择器的"视觉驱动"自动化。高风险操作（表单提交、支付、邮件发送）自动触发 **HITL 人工审批**流程，保障企业合规安全。

### 报告生成器

由 **Qwen3-80B-A3B-Thinking** 驱动，支持日报、周报、月报、会议纪要、销售报告等多种格式，输出标准 Markdown，可导出 Word/PDF，并通过 RCClaw 网关推送到企业 IM。

### 邮件智能处理

自动分类、摘要、起草回复，支持批量处理，优先级排序，关键信息提取，大幅降低邮件处理时间成本。

---

## 技术栈说明

| 层级 | 组件 | NVIDIA SDK / 工具 | 说明 |
|------|------|-------------------|------|
| **控制层** | NemoClaw | NemoClaw DGX Spark 插件 | NVIDIA 官方 Agent 沙盒 |
| **Agent 框架** | OpenClaw | OpenClaw | 底层 Agent 编排框架 |
| **网关层** | RCClaw（自研） | — | 微信/飞书/Telegram 多通道接入 |
| **编排层** | LangGraph | — | 有状态 ReAct Agent 图，支持 HITL |
| **推理引擎** | vLLM | — | 高性能推理框架，支持 CUDA 加速 |
| **主推理 LLM** | Qwen3-80B-A3B-Thinking | — | MoE 架构，152GB，激活参数 ~3B |
| **视觉 VLM** | Qwen2.5-VL-7B-Instruct | — | 屏幕截图语义理解，16GB |
| **Embedding** | BGE-M3 | — | 稠密+稀疏+多向量三合一，~2GB |
| **Reranker** | BGE-Reranker-v2-m3 | — | 精排重排序，~1GB |
| **后端框架** | FastAPI + Uvicorn | — | OAI 兼容 REST API |
| **浏览器自动化** | Playwright CDP | — | 无头浏览器，视觉驱动 |
| **图形界面** | Open WebUI | — | 本地对话界面，`:3000` |

---

## 算力部署说明

**本项目全部利用本地算力部署大模型，无任何云端 API 依赖，数据不出 DGX Spark 节点。**

| 模型 | 大小 | 端口 | 部署方式 | 用途 |
|------|------|------|---------|------|
| Qwen3-next-80b-a3b-thinking | 152 GB | 8000 | vLLM（本地） | 主推理 LLM，MoE 激活 ~3B |
| Qwen2.5-VL-7B-Instruct | 16 GB | 8001 | vLLM（本地） | 视觉理解 VLM |
| BGE-M3 + BGE-Reranker-v2-m3 | ~3 GB | 8002 | FastAPI（本地） | Embedding + Reranker |

**硬件平台**：NVIDIA DGX Spark GB10，Blackwell 架构，128GB 统一内存，aarch64。vLLM 框架充分利用 CUDA 加速，支持 bfloat16 量化和 chunked-prefill 优化，实现极低延迟推理。

**推理引擎选择**：

- **vLLM**（当前）：快速部署，开箱即用，支持 OpenAI 兼容 API
- **TensorRT-LLM**（未来优化）：NVIDIA 官方引擎，Blackwell 专项优化，性能进一步提升

NemoClaw 配置（`.nemoclaw/config.json`）中所有 `base_url` 均指向 `localhost`，`api_key` 设为 `EMPTY`，确保零云端流量。

---

## 快速开始

### 环境要求

- NVIDIA DGX Spark GB10（或兼容 aarch64 + CUDA 12.x 环境）
- Python 3.11+（系统已有）
- vLLM 0.18.0+（已预装）

### 一键部署

```bash
# 1. 克隆仓库
git clone https://github.com/RussellCooper-DJZ/OfficeMind.git
cd OfficeMind

# 2. 安装依赖（可选，大多数已预装）
pip install -r requirements.txt \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置环境变量
cp .env.example .env

# 4. 一键启动全部服务
bash scripts/start_all_services.sh
```

### 访问服务

建立 SSH 隧道后（运行 `docs/connect_dgx_spark.bat`），在本地浏览器访问：

| 地址 | 服务 |
|------|------|
| `http://localhost:3000` | Open WebUI 图形对话界面 |
| `http://localhost:7860/docs` | OfficeMind API 交互文档 |
| `http://localhost:8000/v1` | vLLM Qwen3-80B |
| `http://localhost:8001/v1` | vLLM Qwen2.5-VL |
| `http://localhost:8002/health` | BGE API 健康检查 |

---

## 项目结构

```
OfficeMind/
├── .nemoclaw/
│   └── config.json              # NemoClaw 本地模型配置（全指向 localhost）
├── .agents/
│   └── main/agent.md            # OpenClaw Agent 定义
├── src/
│   ├── inference/
│   │   └── vllm_engine.py       # vLLM 推理引擎封装
│   ├── agent/
│   │   └── orchestrator.py      # LangGraph ReAct Agent（路由 + HITL）
│   ├── rag/
│   │   ├── pipeline.py          # RAG 检索管道
│   │   └── bge_retriever.py     # BGE 4层检索实现
│   ├── vision/
│   │   └── screen_reader.py     # VLM 屏幕视觉理解
│   ├── browser/
│   │   └── operator.py          # Playwright 浏览器自动化
│   └── api/
│       └── app.py               # FastAPI 后端入口
├── scripts/
│   ├── start_all_services.sh    # 一键启动全栈（vLLM + BGE + WebUI）
│   ├── download_models.py       # 下载 BGE 模型（可选）
│   └── bge_api.py               # BGE Embedding/Reranker API 服务
├── docs/
│   ├── connect_dgx_spark.bat    # Windows SSH 隧道一键脚本
│   └── windows-connect-guide.md # 连接说明文档
├── config/config.yaml           # 服务配置
├── requirements.txt
└── .env.example
```

---

## 评审维度说明

### 技术创新性（30%）

本项目的核心创新在于**三层 Claw 架构**的设计：RCClaw（自研多通道网关）→ NemoClaw（NVIDIA 官方控制层）→ OpenClaw（底层 Agent 框架），形成完整的本地化 AI 办公自动化闭环。RAG 层引入 BGE-M3 的稠密+稀疏+多向量三合一检索能力，结合 Reranker 精排，实现企业级文档问答精度。VLM 驱动的"视觉感知"浏览器自动化突破了传统 DOM 选择器的局限性，可操作任何无 API 的遗留系统。

### 场景落地性（25%）

自动化办公是企业 AI 落地最高频的真实需求场景。OfficeMind 覆盖邮件处理、文档问答、报告生成、浏览器自动化四大高价值工作流，通过 RCClaw 网关支持微信、飞书、Telegram 等主流企业 IM 接入，具备直接落地推广的可行性。HITL 人工审批机制保障高风险操作的安全性，满足企业合规要求。

### 技术完整性（20%）

项目包含完整的五层架构实现：网关层（RCClaw）、控制层（NemoClaw/OpenClaw）、编排层（LangGraph）、推理层（vLLM）、RAG 层（BGE）。提供一键部署脚本、环境配置模板、API 文档、SSH 隧道工具，可在 DGX Spark 节点上完整运行演示。

### 平台适配性（15%）

充分利用 DGX Spark GB10 的全栈能力：使用 NVIDIA 官方 NemoClaw DGX Spark 插件、vLLM 推理框架。128GB 统一内存支持同时加载 Qwen3-80B（152GB MoE 权重，激活 ~3B）+ Qwen2.5-VL-7B + BGE 模型，充分发挥 Blackwell 架构的统一内存优势。

### 演示效果（10%）

通过 Open WebUI 提供直观的图形对话界面，FastAPI 提供 `/docs` 交互式 API 文档，SSH 隧道脚本实现一键本地访问。演示流程：自然语言指令 → NemoClaw 路由 → vLLM 推理 → 结果推送，端到端链路清晰可见。

---

## 团队信息

**团队名称**：RCClaw Team（3 人）
**参赛赛道**：NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松
**项目仓库**：[github.com/RussellCooper-DJZ/OfficeMind](https://github.com/RussellCooper-DJZ/OfficeMind)

---

## 相关资源

- [NVIDIA NemoClaw DGX Spark 插件](https://github.com/HeKun-NVIDIA/nemoclaw_on_dgx_spark)
- [vLLM 高性能推理框架](https://github.com/vllm-project/vllm)
- [BGE-M3 模型（BAAI）](https://huggingface.co/BAAI/bge-m3)
- [Qwen3 模型系列](https://huggingface.co/Qwen/Qwen3-30B-A3B)
- [Open WebUI](https://github.com/open-webui/open-webui)

---

*本项目为 NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛作品。*
