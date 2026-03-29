#!/bin/bash
# ============================================================
# OfficeMind — Start Qwen3-80B-A3B-Thinking on DGX Spark GB10
# Model: /home/xsuper/models/Qwen3-next-80b-a3b-thinking
# Hardware: NVIDIA GB10, 128GB unified memory
# ============================================================

set -e

MODEL_PATH="/home/xsuper/models/Qwen3-next-80b-a3b-thinking"
MODEL_NAME="Qwen3-Thinking"
PORT=8000
LOG_DIR="/home/xsuper/logs"

mkdir -p "$LOG_DIR"

echo "============================================"
echo "  OfficeMind — Qwen3 vLLM Service"
echo "  Model: $MODEL_PATH"
echo "  Port:  $PORT"
echo "============================================"

# Check model exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    echo "Run: python3 -c \"from modelscope import snapshot_download; snapshot_download('qwen/Qwen3-next-80b-a3b-thinking', cache_dir='/home/xsuper/models')\""
    exit 1
fi

# Install vLLM if not present
if ! python3 -c "import vllm" 2>/dev/null; then
    echo "Installing vLLM for aarch64..."
    pip3 install vllm --extra-index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -5
fi

echo "Starting vLLM server..."
python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --served-model-name "$MODEL_NAME" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.85 \
    --enable-chunked-prefill \
    --max-num-batched-tokens 8192 \
    --tensor-parallel-size 1 \
    2>&1 | tee "$LOG_DIR/qwen3_vllm.log"
