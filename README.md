# OfficeMind — 企业级全栈 AI 自动化办公助手

![NVIDIA DGX Spark](https://img.shields.io/badge/Platform-NVIDIA_DGX_Spark_GB10-76B900?style=for-the-badge&logo=nvidia)
![Model](https://img.shields.io/badge/Model-Qwen3_80B_Thinking-blue)
![Framework](https://img.shields.io/badge/Framework-NeMo_Agent_Toolkit_|_OpenClaw-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**OfficeMind** 是为 **NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松** 打造的参赛项目。它是一个完全运行在本地算力节点上的企业级 AI 办公自动化助手，基于 NVIDIA NeMo Agent Toolkit 和 OpenClaw 构建，将大语言模型（LLM）、视觉语言模型（VLM）、检索增强生成（RAG）与浏览器自动化深度融合，实现“看屏幕、读文档、自动操作”的全链路办公自动化。

---

## 🌟 核心亮点（黑客松评审维度）

### 1. 技术创新性 (30%)
- **NeMo ReAct Agent 核心架构**：基于 NeMo Agent Toolkit 构建主控 Agent，采用 ReAct (Reasoning + Acting) 模式，实现复杂任务的自主拆解与多步工具调用。
- **多模态屏幕理解 (VLM)**：采用 `Qwen2.5-VL-7B` 实时理解屏幕截图，将不可读的 UI 元素转化为结构化语义，突破传统 DOM 自动化的局限。
- **4 层 RAG 检索管道**：针对企业复杂文档，构建了 `语义分块 → HyDE (假设性文档嵌入) → 混合搜索 (Dense+BM25) → MMR 重排` 的 4 层高精度检索架构。
- **OpenClaw Gateway 无缝集成**：复用 OpenClaw 框架作为消息通道，将 Agent 的执行结果自动推送到微信、飞书、Telegram 等企业 IM 平台。

### 2. 场景落地性 (25%)
直击企业真实痛点，提供四大开箱即用的自动化场景：
- **视觉化系统操作**：针对没有 API 的老旧系统，通过 VLM 截图理解 + Playwright CDP，实现自动化填表与数据抓取。
- **企业知识库问答**：一键上传合同、财报、规章制度，实现精准的条款解析与风险提示。
- **跨系统数据搬运**：自然语言驱动的浏览器操作，无需重新登录即可在 OA、CRM、ERP 系统间流转数据。
- **数据报表生成**：将杂乱的业务数据转化为结构化的 Word/PDF/Markdown 报告，并通过 OpenClaw 推送。

### 3. 平台适配性 (15%)
**极致压榨 NVIDIA DGX Spark GB10 算力**：
- 充分利用 **128GB 统一内存** 和 Blackwell 架构优势，在单节点上**同时并发运行**三个大模型，各司其职：
  - `Qwen3-next-80b-a3b-thinking` (主推理中枢，MoE 架构极速响应，占用 ~75% 显存)
  - `Qwen2.5-VL-7B-Instruct` (视觉感知引擎，占用 ~15% 显存)
  - `nemotron-3-nano-30b-a3b` (轻量级工具调用与指令生成，占用 ~8% 显存)
- 采用 `vLLM` 框架进行推理加速，开启 `bfloat16` 和 `chunked-prefill`，实现极低延迟。

### 4. 技术完整性 (20%)
- **全栈架构**：从底层的模型部署脚本、中间层的 Agent 编排与 RAG 引擎，到上层的 FastAPI 接口和 Open WebUI 交互界面，提供完整的生产级代码。
- **安全兜底 (HITL)**：内置 Human-in-the-Loop 机制，对于高风险操作自动暂停并请求人工审批。
- **一键部署**：提供完善的自动化部署脚本 `deploy.sh`，自动拉起所有 vLLM 服务并配置环境。

---

## 🏗️ 系统架构

```text
       用户指令
          │
          ▼
┌───────────────────────────────────────────────┐
│        NeMo Agent Toolkit (ReAct Agent)       │
│                 (主控中枢)                      │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│                 工具集 (Tools)                 │
│                                               │
│  ├── VLM Screen Reader                        │  ← Qwen2.5-VL-7B (屏幕视觉理解)
│  │   (截图 → 语义理解)                          │
│  │                                            │
│  ├── RAG Document QA                          │  ← 4层检索 + BGE-M3 Embedding
│  │   (企业知识库问答)                           │
│  │                                            │
│  ├── Browser Operator                         │  ← Nemotron-Nano + Playwright CDP
│  │   (自动填表/点击/导航)                       │
│  │                                            │
│  └── Report Generator                         │  ← Qwen3-80B-Thinking
│      (结构化输出 → Word/PDF)                    │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│         OpenClaw Gateway (消息通道)             │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
            微信 / 飞书 / Telegram 推送结果
```

---

## 🚀 快速开始

### 1. 一键部署 (DGX Spark 节点)

在 DGX Spark 节点上，只需执行以下命令即可完成所有环境配置、依赖安装和模型启动：

```bash
wget -O ~/deploy.sh https://raw.githubusercontent.com/RussellCooper-DJZ/OfficeMind/main/scripts/deploy.sh
bash ~/deploy.sh
```

**部署脚本会自动执行以下操作：**
1. 启动 `Qwen3-80B` vLLM 实例 (端口 8000)
2. 启动 `Qwen2.5-VL-7B` vLLM 实例 (端口 8001)
3. 启动 `Nemotron-Nano-30B` vLLM 实例 (端口 8002)
4. 克隆代码仓库并安装 Python 依赖
5. 启动 Open WebUI (端口 3000)

*(注：由于模型文件巨大，首次启动加载需要 3~5 分钟)*

### 2. 启动 OfficeMind API 服务

依赖安装完成后，启动 FastAPI 后端服务：

```bash
cd ~/OfficeMind
python -m uvicorn src.api.officemind_agent:app --host 0.0.0.0 --port 7860
```

### 3. 访问与测试

在本地机器上建立 SSH 隧道后，即可访问服务：

- **Open WebUI**: `http://localhost:3000`
- **OfficeMind API 文档**: `http://localhost:7860/docs`
- **vLLM API (Qwen3-80B)**: `http://localhost:8000/v1`

---

## 📂 目录结构

```text
OfficeMind/
├── src/
│   └── api/
│       └── officemind_agent.py # NeMo ReAct Agent 主逻辑与 FastAPI 接口
├── scripts/
│   └── deploy.sh               # 节点一键部署与服务拉起脚本
├── requirements.txt            # 项目依赖清单
├── .env.example                # 环境变量配置示例
└── README.md                   # 项目说明文档
```

---

## 🤝 团队信息
- **团队规模**：3 人
- **技术栈**：NVIDIA NeMo Agent Toolkit, OpenClaw, vLLM, Playwright, Qwen 系列模型
- **算力部署说明**：本项目**全部利用本地算力（DGX Spark GB10 节点）部署大模型**，未调用任何外部商业 API。
- **NVIDIA SDK 使用**：使用了 NeMo Agent Toolkit、NemoClaw (OpenClaw) 架构，并计划后续引入 TensorRT-LLM 进一步优化推理性能。

---
*本项目为 NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛作品。*
