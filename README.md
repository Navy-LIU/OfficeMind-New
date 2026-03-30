# OfficeMind — 企业级全栈 AI 自动化办公助手

![NVIDIA DGX Spark](https://img.shields.io/badge/Platform-NVIDIA_DGX_Spark_GB10-76B900?style=for-the-badge&logo=nvidia)
![CUDA 13.0](https://img.shields.io/badge/CUDA-13.0-76B900?style=for-the-badge)
![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

[![Platform](https://img.shields.io/badge/Platform-NVIDIA%20DGX%20Spark%20GB10-76b900?style=for-the-badge&logo=nvidia)](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)
[![Engine](https://img.shields.io/badge/Engine-vLLM-76b900?style=for-the-badge&logo=nvidia)](https://github.com/vllm-project/vllm)
[![Framework](https://img.shields.io/badge/Framework-NemoClaw%20%2B%20OpenClaw-blue?style=for-the-badge)](https://github.com/HeKun-NVIDIA/nemoclaw_on_dgx_spark)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## 项目简介

### 1. 技术创新性 (30%)
- **多模态屏幕理解 (VLM + pHash)**：摒弃传统的脆弱 DOM 规则和 OCR，采用 `llava:7b` 实时理解屏幕截图。创新性引入 **pHash 感知哈希预过滤**，仅在屏幕发生实质性变化时才调用 VLM，将视觉推理开销降低 60% 以上。
- **4 层 RAG 检索管道**：针对企业复杂文档，构建了 `语义分块 → HyDE (假设性文档嵌入) → 混合搜索 (Dense+BM25) → MMR 重排` 的 4 层高精度检索架构，彻底解决传统 RAG 召回率低、上下文冗余的问题。
- **ReAct Agent 编排**：采用基于 ReAct 模式的 Agent 编排器，实现邮件处理、文档问答、报告生成、浏览器操作的智能路由与状态流转。

### 2. 场景落地性 (25%)
直击企业真实痛点，提供四大开箱即用的自动化场景：
- **邮件智能处理**：自动提取长邮件/邮件流中的行动项（Action Items）、截止日期和优先级，并生成专业回复草稿。
- **跨系统数据搬运与填表**：基于 Playwright CDP 协议接管浏览器，无需重新登录即可在 OA、CRM、ERP 系统间自动提取数据并填写表单。
- **企业知识库问答**：一键上传合同、财报、规章制度，实现精准的条款解析与风险提示。
- **数据报表生成**：将杂乱的销售数据、会议记录一键转化为结构化的 Markdown/PDF 报告。

### 3. 平台适配性 (15%)
**极致压榨 NVIDIA DGX Spark GB10 算力**：
- 充分利用 **128GB 统一内存** 和 Blackwell 架构优势，在单节点上**同时并发运行**三个大模型：
  - `Qwen2.5-72B-Instruct` (主推理中枢，llama_cpp 全 GPU 卸载)
  - `llava:7b` (视觉感知，Ollama GPU 加速)
  - `Qwen3-Embedding` (向量检索)
- 针对 **CUDA 13.0** 进行了深度适配，通过系统库软链接修复了预编译包的兼容性问题。

### 4. 技术完整性 (20%)
- **全栈架构**：从底层的模型部署脚本、中间层的 Agent 编排与 RAG 引擎，到上层的 FastAPI 接口，提供完整的生产级代码。
- **安全兜底 (HITL)**：内置 Human-in-the-Loop 机制，对于高风险操作（如提交表单、发送邮件）或低置信度推理，自动暂停并请求人工审批。
- **一键部署**：提供完善的部署脚本，屏蔽复杂的环境依赖。

---

## 系统架构

OfficeMind 采用微服务架构，各组件通过 REST API 通信，由核心 Agent 进行统一编排：

```text
┌─────────────────────────────────────────────────────────────┐
│                    OfficeMind Agent (:7860)                 │
│  (ReAct 编排器 / 任务规划 / 工具调用 / Human-in-the-Loop)   │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ LLM Service │    │ VLM Service │    │ EMB Service │
│   (:8000)   │    │   (:8001)   │    │   (:8002)   │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ Qwen2.5-72B │    │  llava:7b   │    │ Qwen3-Embed │
│ (llama_cpp) │    │  (Ollama)   │    │ (SentenceT) │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
        NVIDIA DGX Spark GB10 (128GB 统一内存)
```

### 核心工具集 (Tools)
1. `vlm_screen_reader`：屏幕截图语义理解（表单识别、数据提取、异常检测）。
2. `rag_document_qa`：企业文档问答（语义分块 → HyDE → 混合搜索 → MMR 重排）。
3. `browser_operator`：浏览器自动化（基于 Playwright CDP 的导航、点击、填表）。
4. `report_generator`：结构化报告生成（Markdown/Word/PDF 导出）。

---

## 🚀 部署指南 (DGX Spark GB10)

本项目专为 DGX Spark GB10 节点（Ubuntu 24.04, aarch64, CUDA 13.0）优化。

### 1. 环境准备

确保节点已安装 `miniconda3` (Python 3.13) 和系统级 CUDA 13.0。

```bash
# 1. 克隆仓库
git clone https://github.com/RussellCooper-DJZ/OfficeMind.git
cd OfficeMind

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 模型准备

项目依赖以下本地模型，请确保它们位于 `/home/xsuper/models/` 目录下：
- `qwen2.5-72b-instruct-q4_k_m.gguf` (主 LLM)
- `Qwen/Qwen3-Embedding` (向量模型)

### 3. 安装与修复 Ollama (VLM 后端)

由于 GB10 是 ARM64 架构且使用 CUDA 13，需执行专用修复脚本以开启 GPU 加速：

```bash
# 1. 下载并安装 Ollama ARM64 二进制
curl -fsSL https://ollama.com/install.sh | sh

# 2. 执行 GPU 修复脚本（创建 CUDA 13 软链接）
bash scripts/fix_ollama_gpu.sh

# 3. 下载 VLM 模型
ollama pull llava:7b
```

### 4. 一键启动所有服务

```bash
bash scripts/restart_all.sh
```
该脚本将按顺序启动：Ollama GPU -> LLM(8000) -> VLM(8001) -> Embedding(8002) -> Agent(7860)。

---

## 🛠️ 常见问题排查

在 Blackwell 架构上部署时，可能会遇到 CUDA 库缺失、vLLM 预编译包不兼容等问题。详细的排查过程与解决措施请参考：
👉 [部署问题排查与解决措施 (TROUBLESHOOTING.md)](docs/TROUBLESHOOTING.md)

---

## 评审维度说明

### 场景一：智能报销填报
**输入**：自然语言指令“打开OA系统，填写差旅报销申请，金额3500元，出差地点北京”。
**输出**：Agent 接收发票截图 -> VLM 提取金额和类目 -> Browser 自动登录财务系统并填表。在点击“提交”按钮前，触发 HITL 机制，截取当前屏幕并请求用户确认。

### 场景二：跨文档数据汇总
**输入**：上传多个项目周报，提问“总结本月各项目的核心进展”。
**输出**：Agent 检索多个项目周报 (RAG) -> 提取关键指标 -> 生成 Markdown 格式的综合月度报告。

---

## 🤝 团队信息
- **团队规模**：3 人
- **技术栈**：LangGraph, Playwright, Qwen 系列模型, Ollama, llama.cpp
- **算力支持**：NVIDIA DGX Spark 云算力节点 (GB10)

---

## 相关资源

- [NVIDIA NemoClaw DGX Spark 插件](https://github.com/HeKun-NVIDIA/nemoclaw_on_dgx_spark)
- [vLLM 高性能推理框架](https://github.com/vllm-project/vllm)
- [BGE-M3 模型（BAAI）](https://huggingface.co/BAAI/bge-m3)
- [Qwen3 模型系列](https://huggingface.co/Qwen/Qwen3-30B-A3B)
- [Open WebUI](https://github.com/open-webui/open-webui)

---

*本项目为 NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛作品。*
