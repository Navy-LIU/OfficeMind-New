# OfficeMind — 企业级全栈 AI 自动化办公助手

![NVIDIA DGX Spark](https://img.shields.io/badge/Platform-NVIDIA_DGX_Spark_GB10-76B900?style=for-the-badge&logo=nvidia)
![Model](https://img.shields.io/badge/Model-Qwen3_80B_Thinking-blue)
![Framework](https://img.shields.io/badge/Framework-NemoClaw_|_LangGraph-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**OfficeMind** 是为 **NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松** 打造的参赛项目。它是一个完全运行在本地算力节点上的企业级 AI 办公自动化助手，将大语言模型（LLM）、视觉语言模型（VLM）、检索增强生成（RAG）与浏览器自动化深度融合，实现“看屏幕、读文档、自动操作”的全链路办公自动化。

---

## 🌟 核心亮点（黑客松评审维度）

### 1. 技术创新性 (30%)
- **多模态屏幕理解 (VLM + pHash)**：摒弃传统的脆弱 DOM 规则和 OCR，采用 `Qwen2.5-VL-7B` 实时理解屏幕截图。创新性引入 **pHash 感知哈希预过滤**，仅在屏幕发生实质性变化时才调用 VLM，将视觉推理开销降低 60% 以上。
- **4 层 RAG 检索管道**：针对企业复杂文档，构建了 `语义分块 → HyDE (假设性文档嵌入) → 混合搜索 (Dense+BM25) → MMR 重排` 的 4 层高精度检索架构，彻底解决传统 RAG 召回率低、上下文冗余的问题。
- **LangGraph 状态机路由**：采用图结构编排 Agent，实现邮件处理、文档问答、报告生成、浏览器操作的智能路由与状态流转。

### 2. 场景落地性 (25%)
直击企业真实痛点，提供四大开箱即用的自动化场景：
- **邮件智能处理**：自动提取长邮件/邮件流中的行动项（Action Items）、截止日期和优先级，并生成专业回复草稿。
- **跨系统数据搬运与填表**：基于 Playwright CDP 协议接管浏览器，无需重新登录即可在 OA、CRM、ERP 系统间自动提取数据并填写表单。
- **企业知识库问答**：一键上传合同、财报、规章制度，实现精准的条款解析与风险提示。
- **数据报表生成**：将杂乱的销售数据、会议记录一键转化为结构化的 Markdown/PDF 报告。

### 3. 平台适配性 (15%)
**极致压榨 NVIDIA DGX Spark GB10 算力**：
- 充分利用 **128GB 统一内存** 和 Blackwell 架构优势，在单节点上**同时并发运行**三个大模型：
  - `Qwen3-next-80b-a3b-thinking` (主推理中枢，MoE 架构极速响应)
  - `Qwen2.5-VL-7B-Instruct` (视觉感知)
  - `Qwen3-Embedding` (向量检索)
- 深度集成 **NVIDIA NemoClaw** 框架，利用其沙盒环境和 Agent 能力。
- 采用 `vLLM` 框架进行推理加速，开启 `bfloat16` 和 `chunked-prefill`，实现极低延迟。

### 4. 技术完整性 (20%)
- **全栈架构**：从底层的模型部署脚本、中间层的 Agent 编排与 RAG 引擎，到上层的 FastAPI 接口，提供完整的生产级代码。
- **安全兜底 (HITL)**：内置 Human-in-the-Loop 机制，对于高风险操作（如提交表单、发送邮件）或低置信度推理，自动暂停并请求人工审批。
- **一键部署**：提供完善的 `Makefile` 和自动化脚本，屏蔽复杂的环境依赖。

---

## 🏗️ 系统架构

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          OfficeMind API (FastAPI)                       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                       Agent Orchestrator (LangGraph)                    │
│  ┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│  │  Email  │  │ Document QA │  │  Report  │  │ Browser │  │   HITL   │  │
│  └─────────┘  └─────────────┘  └──────────┘  └─────────┘  └──────────┘  │
└─┬───────────────────┬─────────────────────────────┬───────────────────┬─┘
  │                   │                             │                   │
┌─▼───────┐ ┌─────────▼─────────┐ ┌─────────────────▼─────────┐ ┌───────▼─┐
│ Prompt  │ │ 4-Layer RAG Engine│ │ Browser Operator (CDP)    │ │ Vision  │
│ Builder │ │ (HyDE + MMR)      │ │ (Playwright + Auto-Retry) │ │ (pHash) │
└─┬───────┘ └─────────┬─────────┘ └─────────────────┬─────────┘ └───────┬─┘
  │                   │                             │                   │
┌─▼───────────────────▼─────────────────────────────▼───────────────────▼─┐
│                       NVIDIA DGX Spark GB10 (128GB)                     │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌─────────────────┐  │
│  │ Qwen3-80B-Thinking   │ │ Qwen2.5-VL-7B        │ │ Qwen3-Embedding │  │
│  │ (vLLM / TRT-LLM)     │ │ (vLLM Vision)        │ │ (vLLM Embed)    │  │
│  └──────────────────────┘ └──────────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 环境准备 (DGX Spark 节点)

项目提供了一键安装脚本，自动配置 Node.js、NemoClaw、vLLM 及相关依赖。

```bash
# 克隆仓库
git clone https://github.com/RussellCooper-DJZ/OfficeMind.git
cd OfficeMind

# 安装 Python 依赖及浏览器内核
make install

# 下载视觉与向量模型 (Qwen2.5-VL & Qwen3-Embedding)
make models
```

### 2. 启动模型服务

利用 DGX Spark 的 128GB 统一内存，同时启动三个模型服务：

```bash
# 一键启动所有模型 (LLM:8000, VLM:8001, Embed:8002)
make serve-all

# 查看服务状态与 GPU 显存占用
make status
```

### 3. 启动应用与测试

```bash
# 启动 OfficeMind FastAPI 后端
make start

# 运行核心场景演示 (邮件分析、日报生成、数据分析、RAG问答)
make demo
```

---

## 📂 目录结构

```text
OfficeMind/
├── src/
│   ├── agent/          # LangGraph 状态机与路由逻辑
│   ├── rag/            # 4层 RAG 检索管道 (分块, HyDE, 混合搜索, MMR)
│   ├── vision/         # 视觉理解模块 (pHash 预过滤 + Qwen-VL)
│   ├── browser/        # 浏览器自动化操作 (Playwright CDP)
│   └── api/            # FastAPI 接口层
├── scripts/            # 部署与启动脚本 (serve_models.sh 等)
├── config/             # 配置文件
├── .agents/            # NemoClaw Agent 配置
├── demo.py             # 核心场景演示脚本
├── Makefile            # 一键构建与运行指令
└── requirements.txt    # Python 依赖
```

---

## 💡 典型使用场景演示

### 场景一：智能邮件分析
**输入**：一封包含多项任务、数据和会议安排的冗长邮件。
**输出**：OfficeMind 自动提取出结构化的行动项（负责人、截止日期）、关键数据亮点，并判断邮件优先级，最后生成一封得体的回复草稿。

### 场景二：RAG 合同审查
**输入**：上传一份 50 页的 PDF 采购合同，提问“如果我方逾期交付，违约金如何计算？”
**输出**：OfficeMind 通过 `语义分块 -> HyDE -> 混合检索 -> MMR` 管道，精准定位到第 8 条违约责任，提取出“每日 0.1%，最高 10%”的条款，并给出风险提示。

### 场景三：浏览器自动化填表
**输入**：自然语言指令“打开OA系统，填写差旅报销申请，金额3500元，出差地点北京”。
**输出**：OfficeMind 将指令解析为浏览器操作序列，自动导航、定位输入框并填写。在点击“提交”按钮前，触发 HITL 机制，截取当前屏幕并请求用户确认。

---

## 🤝 团队信息
- **团队规模**：3 人
- **技术栈**：NVIDIA NeMo Agent Toolkit, LangGraph, vLLM, Playwright, Qwen 系列模型
- **算力支持**：NVIDIA DGX Spark 云算力节点 (GB10)

---
*本项目为 NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛作品。*
