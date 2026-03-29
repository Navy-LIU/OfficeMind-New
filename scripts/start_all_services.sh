#!/bin/bash
# OfficeMind — 一键启动所有服务
# 在 DGX Spark GB10 上运行: bash start_all_services.sh

CONDA="$HOME/miniconda3/bin"
MODELS="$HOME/models"
LOG="/tmp/officemind_logs"
mkdir -p $LOG

echo "=============================================="
echo "  OfficeMind Services Startup"
echo "  Platform: NVIDIA DGX Spark GB10 (128GB)"
echo "=============================================="

# ── 1. LLM: Qwen3-80B-A3B-Thinking ─────────────
echo ""
echo "[1/4] Starting LLM (Qwen3-80B) on port 8000..."
pkill -f "port 8000" 2>/dev/null; sleep 1

nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
    --model $MODELS/Qwen3-next-80b-a3b-thinking \
    --served-model-name Qwen3-Thinking \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.60 \
    --tensor-parallel-size 1 \
    --enable-chunked-prefill \
    --max-num-seqs 16 \
    > $LOG/llm.log 2>&1 &
LLM_PID=$!
echo "  ✓ LLM PID: $LLM_PID  →  tail -f $LOG/llm.log"

# ── 2. VLM: Qwen2.5-VL-7B ───────────────────────
echo ""
echo "[2/4] Starting VLM (Qwen2.5-VL-7B) on port 8001..."
VLM_MODEL=$(find $MODELS -name "config.json" -path "*VL*" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
if [ -n "$VLM_MODEL" ]; then
    pkill -f "port 8001" 2>/dev/null; sleep 1
    nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
        --model "$VLM_MODEL" \
        --served-model-name Qwen2.5-VL \
        --host 0.0.0.0 \
        --port 8001 \
        --trust-remote-code \
        --dtype bfloat16 \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.18 \
        --limit-mm-per-prompt image=5 \
        > $LOG/vlm.log 2>&1 &
    VLM_PID=$!
    echo "  ✓ VLM PID: $VLM_PID  →  tail -f $LOG/vlm.log"
    echo "  Model: $VLM_MODEL"
else
    echo "  ✗ VLM model not found, skipping"
fi

# ── 3. JupyterLab ────────────────────────────────
echo ""
echo "[3/4] Starting JupyterLab on port 8888..."
pkill -f "jupyter" 2>/dev/null; sleep 1

# Install if not present
$CONDA/pip show jupyterlab > /dev/null 2>&1 || \
    $CONDA/pip install jupyterlab -q -i https://pypi.tuna.tsinghua.edu.cn/simple

nohup $CONDA/jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    --notebook-dir=/home/xsuper \
    > $LOG/jupyter.log 2>&1 &
JUPYTER_PID=$!
echo "  ✓ JupyterLab PID: $JUPYTER_PID  →  tail -f $LOG/jupyter.log"

# ── 4. Open WebUI ────────────────────────────────
echo ""
echo "[4/4] Starting Open WebUI on port 3000..."
pkill -f "open-webui" 2>/dev/null; sleep 1

$CONDA/pip show open-webui > /dev/null 2>&1 || \
    $CONDA/pip install open-webui -q -i https://pypi.tuna.tsinghua.edu.cn/simple

nohup $CONDA/python -m open_webui.main serve \
    --host 0.0.0.0 \
    --port 3000 \
    > $LOG/webui.log 2>&1 &
WEBUI_PID=$!
echo "  ✓ Open WebUI PID: $WEBUI_PID  →  tail -f $LOG/webui.log"

# ── Summary ──────────────────────────────────────
echo ""
echo "=============================================="
echo "  All services started!"
echo "=============================================="
echo ""
echo "  Service         Port   Status"
echo "  ─────────────────────────────"
echo "  Qwen3-80B LLM   8000   loading (~3-5min)"
echo "  Qwen2.5-VL VLM  8001   loading (~1-2min)"
echo "  JupyterLab       8888   ready"
echo "  Open WebUI       3000   loading (~30s)"
echo ""
echo "  Windows 端口转发（MobaXterm/VSCode）："
echo "  本地 8000 → 节点 8000  (LLM API)"
echo "  本地 8001 → 节点 8001  (VLM API)"
echo "  本地 8888 → 节点 8888  (JupyterLab)"
echo "  本地 3000 → 节点 3000  (Open WebUI 对话界面)"
echo ""
echo "  浏览器访问："
echo "  http://localhost:8888  →  JupyterLab"
echo "  http://localhost:3000  →  Open WebUI (对话大模型)"
echo "  http://localhost:8000/docs  →  LLM API Docs"
echo ""
echo "  查看日志: tail -f $LOG/llm.log"
echo "=============================================="
