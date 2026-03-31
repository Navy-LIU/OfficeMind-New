#!/bin/bash
# OfficeMind - NVIDIA DGX Spark GB10 专家级部署脚本
# 核心功能：CUDA 13 适配、多模型并发启动、Ollama GPU 修复、128GB 统一内存优化

set -e

echo "🚀 [OfficeMind] 开始在 NVIDIA GB10 节点上部署..."

# 1. CUDA 13.0 兼容性修复 (针对 vLLM/Ollama)
echo "🔧 [Step 1] 修复 CUDA 13.0 库软链接..."
sudo ln -sf /usr/local/cuda-13.0/lib64/libcublas.so.13 /usr/local/cuda-13.0/lib64/libcublas.so.12 || true
sudo ln -sf /usr/local/cuda-13.0/lib64/libcublasLt.so.13 /usr/local/cuda-13.0/lib64/libcublasLt.so.12 || true

# 2. Ollama GPU 识别修复
echo "🔧 [Step 2] 修复 Ollama GPU 识别..."
OLLAMA_CUDA_DIR="/usr/lib/ollama/cuda_v13"
sudo mkdir -p $OLLAMA_CUDA_DIR
sudo ln -sf /usr/local/cuda-13.0/lib64/libcublas.so.13 $OLLAMA_CUDA_DIR/libcublas.so.13
sudo ln -sf /usr/local/cuda-13.0/lib64/libcublasLt.so.13 $OLLAMA_CUDA_DIR/libcublasLt.so.13

# 3. 并发启动模型服务 (利用 128GB 统一内存)
echo "📦 [Step 3] 启动模型服务 (后台运行)..."

# 3.1 启动 Ollama (用于 VLM, OCR, Agent 路由)
# 模型：llava:7b, nemotron-cascade-2:30b, glm-ocr:bf16
ollama serve > /dev/null 2>&1 &
sleep 5
echo "📥 预加载模型至 Ollama..."
ollama run llava:7b "hello" > /dev/null
ollama run nemotron-cascade-2:30b "hello" > /dev/null

# 3.2 启动 vLLM (用于核心推理 Qwen3.5:35b)
# 优化：启用 --enforce-eager 以减少 CUDA 13 下的内存碎片
python3 -m vllm.entrypoints.openai.api_server \
    --model /home/xsuper/models/qwen3.5-35b-instruct \
    --port 8000 \
    --gpu-memory-utilization 0.7 \
    --max-model-len 8192 \
    --enforce-eager \
    --served-model-name qwen3.5:35b > vllm.log 2>&1 &

# 4. 启动 OfficeMind 核心 Agent
echo "🤖 [Step 4] 启动 OfficeMind Agent (Port 7860)..."
cd /home/ubuntu/OfficeMind/services
python3 officemind_agent.py > agent.log 2>&1 &

echo "✅ [OfficeMind] 部署完成！"
echo "🔗 Agent 接口: http://localhost:7860/chat"
echo "📊 监控日志: tail -f vllm.log"
