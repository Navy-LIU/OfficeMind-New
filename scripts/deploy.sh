#!/bin/bash
# OfficeMind 一键部署脚本
# 在 DGX Spark GB10 节点上执行：bash deploy.sh
set -e

CONDA=/home/xsuper/miniconda3/bin
MODELS=/home/xsuper/models
LOGS=/tmp/officemind_logs
REPO=~/OfficeMind

mkdir -p $LOGS

echo "========================================"
echo "  OfficeMind 一键部署 — DGX Spark GB10"
echo "========================================"

# ── 1. 清理旧进程 ─────────────────────────────────────────────
echo "[1/6] 清理旧进程..."
pkill -f 'install_ollama_gh|wget.*ollama' 2>/dev/null || true
pkill -f 'vllm.entrypoints' 2>/dev/null || true
pkill -f 'uvicorn.*officemind\|open-webui' 2>/dev/null || true
sleep 2

# ── 2. 启动 Qwen3-80B vLLM (port 8000) ───────────────────────
echo "[2/6] 启动 Qwen3-80B vLLM → :8000 ..."
nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
  --model $MODELS/Qwen3-next-80b-a3b-thinking \
  --served-model-name Qwen3-Thinking \
  --host 0.0.0.0 --port 8000 \
  --trust-remote-code --dtype bfloat16 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.75 \
  --tensor-parallel-size 1 \
  --enable-chunked-prefill \
  --max-num-seqs 32 \
  > $LOGS/llm.log 2>&1 &
echo "  LLM PID: $!"

# ── 3. 启动 Qwen2.5-VL-7B vLLM (port 8001) ───────────────────
echo "[3/6] 启动 Qwen2.5-VL-7B vLLM → :8001 ..."
nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
  --model $MODELS/qwen/Qwen2___5-VL-7B-Instruct \
  --served-model-name Qwen2.5-VL \
  --host 0.0.0.0 --port 8001 \
  --trust-remote-code --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.18 \
  --limit-mm-per-prompt images=5 \
  > $LOGS/vlm.log 2>&1 &
echo "  VLM PID: $!"

# ── 4. 启动 Nemotron-Nano-30B (port 8002, 工具调用) ───────────
echo "[4/6] 启动 Nemotron-Nano-30B vLLM → :8002 ..."
nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
  --model $MODELS/nemotron-3-nano-30b-a3b \
  --served-model-name Nemotron-Nano \
  --host 0.0.0.0 --port 8002 \
  --trust-remote-code --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.05 \
  --tensor-parallel-size 1 \
  > $LOGS/nano.log 2>&1 &
echo "  Nano PID: $!"

# ── 5. 克隆 OfficeMind 并安装依赖 ─────────────────────────────
echo "[5/6] 配置 OfficeMind..."
if [ ! -d "$REPO/.git" ]; then
  git clone --depth=1 https://github.com/RussellCooper-DJZ/OfficeMind.git $REPO
fi

# 写 .env
cat > $REPO/.env << 'ENVEOF'
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=Qwen3-Thinking

VLM_BASE_URL=http://localhost:8001/v1
VLM_MODEL=Qwen2.5-VL

TOOL_BASE_URL=http://localhost:8002/v1
TOOL_MODEL=Nemotron-Nano

OPENCLAW_ENABLED=true
HITL_ENABLED=true
HITL_TIMEOUT=30
ENVEOF

# 安装依赖（后台，不阻塞）
$CONDA/pip install -r $REPO/requirements.txt -q > $LOGS/pip.log 2>&1 &
echo "  pip install PID: $! (后台运行)"

# ── 6. 启动 Open WebUI ────────────────────────────────────────
echo "[6/6] 启动 Open WebUI → :3000 ..."
$CONDA/pip show open-webui > /dev/null 2>&1 || \
  $CONDA/pip install open-webui -q > $LOGS/webui_install.log 2>&1

nohup $CONDA/open-webui serve --port 3000 \
  > $LOGS/webui.log 2>&1 &
echo "  WebUI PID: $!"

echo ""
echo "========================================"
echo "  所有服务已在后台启动！"
echo "  模型加载需要 3~5 分钟"
echo ""
echo "  端口说明："
echo "    :8000  Qwen3-80B (主 LLM)"
echo "    :8001  Qwen2.5-VL (视觉)"
echo "    :8002  Nemotron-Nano (工具调用)"
echo "    :3000  Open WebUI"
echo "    :7860  OfficeMind API (pip 装完后手动启动)"
echo ""
echo "  查看日志：tail -f /tmp/officemind_logs/llm.log"
echo "========================================"
