# OfficeMind: 企业级全栈 AI 自动化办公助手 (DGX Spark Hackathon)

![NVIDIA DGX Spark](https://img.shields.io/badge/Platform-NVIDIA_DGX_Spark_GB10-76B900?style=for-the-badge&logo=nvidia)
![CUDA 13.0](https://img.shields.io/badge/CUDA-13.0-76B900?style=for-the-badge)
![Docker](https://img.shields.io/badge/Deployment-Docker_Compose-2496ED?style=for-the-badge&logo=docker)

> **仓库说明**: 本仓库为 `RussellCooper-DJZ/OfficeMind` 的迁移版本，旨在解决原仓库访问异常问题，并持续维护 OfficeMind 项目的核心代码与文档。

OfficeMind 是一个专为 **NVIDIA DGX Spark Hackathon** 打造的智能办公自动化平台。它深度适配了 **NVIDIA GB10 (Blackwell 架构)** 节点，充分利用其 **128GB 统一内存**，实现了多模态视觉理解、高精度 RAG 检索和智能 Agent 编排的本地化全栈部署。

---

## 🚀 核心技术亮点

*   **多模态视觉理解 (VLM + pHash)**: 集成 `llava:7b` 与 `glm-ocr:bf16`。创新性引入 **pHash 感知哈希预过滤**，仅在屏幕发生实质性变化时触发 VLM 推理，将视觉计算开销降低 **60%**。
*   **4 层高精度 RAG 引擎**: 采用 `语义分块 → HyDE (假设性文档增强) → 混合搜索 (Dense+BM25) → MMR 重排` 的四层架构，彻底解决传统 RAG 召回率低和信息冗余的问题。
*   **智能 Agent 编排 (Nemotron-Cascade)**: 基于 `nemotron-cascade-2:30b` 进行任务规划与智能路由，结合 **HITL (Human-in-the-Loop)** 人工审批机制，确保高风险操作（如财务报销、邮件发送）的安全可控。
*   **GB10 极致优化**: 针对 Blackwell 架构和 CUDA 13.0 环境进行了深度适配，支持多模型（Qwen3.5, Nemotron, Llava）在 128GB 统一内存上的并发高效运行。
*   **一键式容器化部署**: 提供完整的 Docker Compose 方案，屏蔽复杂的底层环境依赖，实现分钟级快速部署。

---

## 🛠️ 技术架构

OfficeMind 采用容器化微服务架构，各组件通过高性能 API 通信：

| 模块 | 技术栈 | 核心功能 |
| :--- | :--- | :--- |
| **核心推理 (LLM)** | vLLM / Qwen3.5:35b | 逻辑推理、RAG 生成、任务总结 |
| **视觉感知 (VLM)** | Ollama / llava:7b | 屏幕截图语义理解、UI 元素识别 |
| **文字识别 (OCR)** | glm-ocr:bf16 | 高精度表单与文档文字提取 |
| **任务规划 (Agent)** | Nemotron-Cascade-2:30b | 智能路由、任务拆解、工具选择 |
| **自动化执行** | Playwright CDP | 浏览器自动化、填表、数据抓取 |
| **RAG 检索** | 4-Layer Pipeline | 语义分块、HyDE、混合搜索、MMR |

---

## 📦 快速开始 (DGX Spark GB10)

### 1. 环境准备
确保您的节点已安装 Docker 和 NVIDIA Container Toolkit。

### 2. 克隆仓库与部署
```bash
git clone https://github.com/RussellCooper-DJZ/OfficeMind-New.git
cd OfficeMind-New

# 启动所有服务 (LLM, VLM, Agent)
docker compose up --build -d
```

### 3. 预加载模型
```bash
docker exec -it officemind-ollama ollama pull llava:7b
docker exec -it officemind-ollama ollama pull nemotron-cascade-2:30b
docker exec -it officemind-ollama ollama pull glm-ocr:bf16
```

---

## 📖 详细文档

*   [**专家级部署指南 (DEPLOY_GUIDE.md)**](./DEPLOY_GUIDE.md): 包含 CUDA 13 适配、内存优化及详细步骤。
*   [**评审亮点解析 (JUDGING_POINTS.md)**](./JUDGING_POINTS.md): 深度解析项目的技术创新与 Hackathon 评分对齐。
*   [**故障排除指南 (TROUBLESHOOTING.md)**](./docs/TROUBLESHOOTING.md): 针对 GB10 节点的常见问题及解决方案。

---

## 🤝 团队信息
*   **参赛目标**: 挑战 NVIDIA DGX Spark Hackathon 最高分。
*   **核心理念**: 极致压榨硬件性能，用 AI 重新定义办公效率。
*   **技术支持**: Russell Cooper

---
*本项目为 NVIDIA 首届 DGX Spark 全栈 AI 开发黑客松参赛作品。*
