#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# OfficeMind — vLLM Serving Script for DGX Spark Node
# Serves Qwen-VL-Chat as OpenAI-compatible API on port 8000
# Node: spark-59  |  106.13.186.155:6059
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

MODEL_PATH="/home/xsuper/models/qwen/Qwen-VL-Chat"
PORT=8000
GPU_MEM_UTIL=0.85
MAX_MODEL_LEN=4096

echo "[OfficeMind] Starting vLLM server for Qwen-VL-Chat..."
echo "  Model:   ${MODEL_PATH}"
echo "  Port:    ${PORT}"
echo "  GPU Mem: ${GPU_MEM_UTIL}"

# Install vLLM if not present
python3 -c "import vllm" 2>/dev/null || {
    echo "Installing vllm..."
    pip install vllm -q
}

python3 -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --served-model-name "Qwen-VL-Chat" \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --trust-remote-code \
    --dtype auto \
    --enforce-eager \
    2>&1 | tee /tmp/vllm_server.log
