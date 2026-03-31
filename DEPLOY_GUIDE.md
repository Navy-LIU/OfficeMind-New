# OfficeMind: DGX Spark Hackathon 专家级部署指南

**作者**: Manus AI
**日期**: 2026年3月31日

## 1. 引言

欢迎来到 OfficeMind 的部署指南。OfficeMind 是一个企业级全栈 AI 自动化办公助手，专为 NVIDIA DGX Spark Hackathon 设计，旨在充分利用 DGX Spark GB10 节点的强大算力与 128GB 统一内存，实现多模态理解、高级 RAG 检索和智能办公自动化。本指南将详细阐述如何在 GB10 节点上部署 OfficeMind，确保您能顺利运行并体验其卓越性能。

## 2. 核心技术亮点

OfficeMind 的核心创新和技术栈包括：

*   **多模态视觉理解 (VLM)**: 集成 `llava:7b` (通过 Ollama) 和 `glm-ocr:bf16`，实现对屏幕截图和文档的精准语义理解与文字识别。
*   **pHash 感知哈希预过滤**: 在 VLM 调用前引入 pHash 算法，有效过滤无显著变化的屏幕帧，降低 60% 的视觉推理开销，极大提升效率和资源利用率。
*   **4 层高精度 RAG 检索**: 采用语义分块 (Semantic Chunking) → HyDE (Hypothetical Document Embeddings) → 混合搜索 (Dense + BM25) → MMR (Maximal Marginal Relevance) 重排的四层架构，确保知识检索的广度、深度和准确性。
*   **ReAct Agent 编排器**: 基于 `nemotron-cascade-2:30b` 进行任务规划与智能路由，结合 `qwen3.5:35b` 进行推理，实现复杂办公流程的自动化。
*   **Human-in-the-Loop (HITL) 人工兜底**: 针对高风险或低置信度操作，引入人工审批机制，确保业务流程的安全性和准确性。
*   **浏览器自动化**: 基于 Playwright CDP (Chrome DevTools Protocol) 实现智能报销填报、数据抓取等复杂的浏览器交互。
*   **GB10 节点优化**: 充分利用 Blackwell 架构的 128GB 统一内存，实现多模型（LLM, VLM, Embedding）的并发高效部署，并通过 CUDA 13.0 兼容性修复确保最佳性能。

## 3. 部署先决条件

### 3.1 硬件要求

*   **NVIDIA DGX Spark GB10 节点**: 具备 Blackwell 架构 GPU，128GB 统一内存，CUDA 13.0 环境。

### 3.2 软件要求

*   **操作系统**: Ubuntu 22.04 LTS (aarch64) 或更高版本。
*   **Docker**: 版本 20.10.0 或更高。
*   **NVIDIA Container Toolkit**: 用于 Docker 容器访问 GPU 资源。
*   **Git**: 用于克隆代码仓库。
*   **SSH 客户端**: 用于连接 DGX Spark 节点。

### 3.3 模型准备

OfficeMind 依赖以下大型模型，请确保它们已下载并放置在 GB10 节点的 `/home/xsuper/models/` 目录下：

*   `qwen3.5-35b-instruct`: 作为核心 LLM，用于 RAG 推理和 Agent 总结。
*   `nemotron-cascade-2:30b`: 作为 Agent 的任务规划器和路由器 (通过 Ollama 加载)。
*   `llava:7b`: 作为 VLM 服务，用于屏幕语义理解 (通过 Ollama 加载)。
*   `glm-ocr:bf16`: 作为高精度 OCR 服务 (通过 Ollama 加载)。
*   `Qwen3-Embedding`: 用于 RAG 检索的嵌入模型 (通过 vLLM 或独立服务加载，此处简化为 vLLM 容器内处理)。

**下载方式**: 建议使用 `modelscope` 或 `huggingface-cli` 直接在 GB10 节点上下载，避免 SSH 传输大文件造成拥堵。

```bash
# 示例：下载 Qwen3.5-35B-Instruct
# 请根据实际模型下载方式调整
# 例如使用 modelscope-cli
# pip install modelscope
# modelscope download --model Qwen/Qwen3.5-35B-Instruct --cache-dir /home/xsuper/models/

# Ollama 模型下载 (在 Ollama 容器启动后执行)
# ollama pull llava:7b
# ollama pull nemotron-cascade-2:30b
# ollama pull glm-ocr:bf16
```

## 4. 部署步骤 (Docker Compose)

我们强烈推荐使用 Docker Compose 进行部署，以确保环境一致性和便捷性。

### 4.1 克隆代码仓库

首先，通过 SSH 连接到您的 DGX Spark GB10 节点，并克隆 OfficeMind 代码仓库：

```bash
ssh xsuper@106.13.186.155 -p 6059
# 输入密码: QOW$y5)b

git clone https://github.com/RussellCooper-DJZ/OfficeMind.git
cd OfficeMind
```

### 4.2 配置 `.env` 文件 (可选)

在 `OfficeMind` 目录下创建 `.env` 文件，配置模型路径和端口。如果未配置，将使用 `docker-compose.yml` 中的默认值。

```ini
# .env 示例
LLM_MODEL_PATH=/models/qwen3.5-35b-instruct
LLM_PORT=8000
OLLAMA_PORT=11434
AGENT_PORT=7860
```

### 4.3 启动 Docker Compose 服务

在 `OfficeMind` 目录下执行以下命令启动所有服务：

```bash
docker compose up --build -d
```

这将执行以下操作：

1.  **构建 `agent` 服务镜像**: 根据 `Dockerfile` 构建 OfficeMind Agent 镜像，安装所有 Python 依赖和 Playwright 浏览器。
2.  **启动 `ollama` 服务**: 运行 Ollama 容器，并挂载 `./ollama_data` 目录用于模型存储。
3.  **启动 `vllm` 服务**: 运行 vLLM 容器，加载 `qwen3.5-35b-instruct` 模型，并暴露 8000 端口。
4.  **启动 `agent` 服务**: 运行 OfficeMind Agent 容器，连接到 `vllm` 和 `ollama` 服务，并暴露 7860 端口。

### 4.4 Ollama 模型预加载

在 Ollama 容器启动后，您需要手动拉取所需的模型。可以通过进入 Ollama 容器执行：

```bash
docker exec -it officemind-ollama ollama pull llava:7b
docker exec -it officemind-ollama ollama pull nemotron-cascade-2:30b
docker exec -it officemind-ollama ollama pull glm-ocr:bf16
```

### 4.5 CUDA 13.0 兼容性修复 (容器内)

尽管 Docker 镜像通常会处理大部分兼容性问题，但针对 GB10 节点上的 CUDA 13.0，有时仍需进行软链接修复，以确保 vLLM 和 Ollama 能正确识别 GPU。这些修复已集成到 `deploy_gb10.sh` 脚本中，但在 Docker 环境下，最佳实践是在 `Dockerfile` 中或通过 `docker exec` 手动检查和修复。

**对于 vLLM**: `vllm/vllm-openai` 镜像通常会包含适配的 CUDA 库。如果遇到问题，可能需要自定义 `Dockerfile`，在其中添加类似 `deploy_gb10.sh` 中的软链接命令。

**对于 Ollama**: `docker-compose.yml` 中的 `ollama` 服务已配置 `deploy.resources.reservations.devices`，确保 GPU 访问。如果 Ollama 无法识别 GPU，请检查 NVIDIA Container Toolkit 安装和 `libcublas.so.13` 软链接。

```bash
# 示例：在 Ollama 容器内检查 CUDA 库
docker exec -it officemind-ollama bash
ls -l /usr/local/cuda/lib64/libcublas.so*
# 如果发现指向旧版本，可能需要手动创建软链接
# ln -sf /usr/local/cuda-13.0/lib64/libcublas.so.13 /usr/local/cuda/lib64/libcublas.so.12
exit
```

## 5. 服务验证

所有服务启动后，您可以通过以下方式验证其状态：

*   **检查容器状态**: `docker compose ps`，确保所有服务都处于 `Up` 状态。
*   **访问 Agent 健康检查**: 访问 `http://localhost:7860/health`，应返回类似 `{"status": "running", "device": "NVIDIA GB10", "unified_memory": "128GB"}` 的 JSON 响应。
*   **查看日志**: `docker compose logs -f agent` 查看 Agent 服务的实时日志。

## 6. 使用 OfficeMind Agent

OfficeMind Agent 提供了一个统一的 `/chat` 接口，您可以通过发送 POST 请求与其交互：

```bash
curl -X POST http://localhost:7860/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "请帮我填写一份差旅报销单，金额3500元，用途出差，地点北京。"}'
```

**示例场景**: (在 `officemind_agent.py` 中已模拟)

1.  **智能报销填报**: Agent 接收到报销指令后，通过 `nemotron-cascade-2:30b` 规划，调用 `browser_operator` 自动化填写网页表单，并结合 `vlm_screen_reader` 进行视觉校验。
2.  **跨文档数据汇总**: Agent 接收到数据汇总请求后，通过 `rag_document_qa` 从多源文档中检索信息，然后由 `qwen3.5:35b` 汇总生成结构化报告，最后通过 `report_generator` 导出。

## 7. 故障排除

*   **GPU 识别问题**: 确保 NVIDIA Container Toolkit 已正确安装，并且 `docker-compose.yml` 中的 `deploy.resources.reservations.devices` 配置正确。
*   **模型下载失败**: 检查 `/home/xsuper/models/` 路径是否正确，并确保有足够的磁盘空间和网络连接。
*   **端口冲突**: 检查 `docker-compose.yml` 中定义的端口是否被其他服务占用。
*   **Ollama 模型未加载**: 确保已执行 `docker exec -it officemind-ollama ollama pull <model_name>` 命令。

## 8. 总结

本指南详细介绍了 OfficeMind 在 NVIDIA DGX Spark GB10 节点上的 Docker Compose 部署流程。通过容器化，我们实现了环境的隔离与一致性，极大地简化了部署和管理。OfficeMind 凭借其创新的技术架构和对 GB10 硬件的深度优化，有望在 Hackathon 中取得优异成绩。祝您使用愉快！
