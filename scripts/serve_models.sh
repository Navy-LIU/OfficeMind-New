#!/bin/bash
# OfficeMind — Start all local model servers on DGX Spark GB10
# GPU: NVIDIA GB10 Blackwell, 128GB unified memory
# Usage: bash scripts/serve_models.sh [llm|vlm|embed|all]

set -e
CONDA="$HOME/miniconda3/bin"
MODELS_DIR="$HOME/models"
LOG_DIR="/tmp/officemind_logs"
mkdir -p "$LOG_DIR"

MODE="${1:-all}"

# ── 1. Main LLM: Qwen3-next-80b-a3b-thinking ─────────────────────────────────
start_llm() {
    echo "[1/3] Starting Qwen3-80B-A3B-Thinking on port 8000..."
    MODEL="$MODELS_DIR/Qwen3-next-80b-a3b-thinking"
    
    nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --served-model-name "Qwen3-Thinking" \
        --host 0.0.0.0 \
        --port 8000 \
        --trust-remote-code \
        --dtype bfloat16 \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.55 \
        --tensor-parallel-size 1 \
        --enable-chunked-prefill \
        --max-num-seqs 32 \
        2>&1 | tee "$LOG_DIR/llm.log" &
    
    echo "LLM server PID: $! → $LOG_DIR/llm.log"
}

# ── 2. VLM: Qwen2.5-VL-7B-Instruct ──────────────────────────────────────────
start_vlm() {
    echo "[2/3] Starting Qwen2.5-VL-7B on port 8001..."
    MODEL="$MODELS_DIR/qwen/Qwen2___5-VL-7B-Instruct"
    
    # Wait for model to be downloaded
    if [ ! -d "$MODEL" ]; then
        echo "VLM model not found at $MODEL, checking alternatives..."
        MODEL=$(find "$MODELS_DIR" -name "*VL*" -type d 2>/dev/null | head -1)
        if [ -z "$MODEL" ]; then
            echo "VLM model not downloaded yet, skipping..."
            return
        fi
    fi
    
    nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --served-model-name "Qwen2.5-VL" \
        --host 0.0.0.0 \
        --port 8001 \
        --trust-remote-code \
        --dtype bfloat16 \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.20 \
        --limit-mm-per-prompt image=5 \
        2>&1 | tee "$LOG_DIR/vlm.log" &
    
    echo "VLM server PID: $! → $LOG_DIR/vlm.log"
}

# ── 3. Embedding: Qwen3-Embedding ─────────────────────────────────────────────
start_embed() {
    echo "[3/3] Starting Qwen3-Embedding on port 8002..."
    MODEL="$MODELS_DIR/Qwen/Qwen3-Embedding"
    
    if [ ! -d "$MODEL" ]; then
        echo "Embedding model not found, checking alternatives..."
        MODEL=$(find "$MODELS_DIR" -name "*Embedding*" -type d 2>/dev/null | head -1)
        if [ -z "$MODEL" ]; then
            echo "Embedding model not downloaded yet, skipping..."
            return
        fi
    fi
    
    nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --served-model-name "Qwen3-Embedding" \
        --host 0.0.0.0 \
        --port 8002 \
        --trust-remote-code \
        --dtype bfloat16 \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.05 \
        --task embed \
        2>&1 | tee "$LOG_DIR/embed.log" &
    
    echo "Embedding server PID: $! → $LOG_DIR/embed.log"
}

# ── Health check ──────────────────────────────────────────────────────────────
check_health() {
    echo ""
    echo "=== Waiting for servers to start (30s) ==="
    sleep 30
    
    for port in 8000 8001 8002; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo "✓ Port $port: ONLINE"
        else
            echo "✗ Port $port: offline (may still be loading)"
        fi
    done
    
    echo ""
    echo "GPU Memory Usage:"
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo "=== OfficeMind Model Server Startup ==="
echo "Platform: NVIDIA DGX Spark GB10 (128GB unified memory)"
echo "Mode: $MODE"
echo ""

case "$MODE" in
    llm)   start_llm ;;
    vlm)   start_vlm ;;
    embed) start_embed ;;
    all)
        start_llm
        sleep 5
        start_vlm
        sleep 5
        start_embed
        check_health
        ;;
    *)
        echo "Usage: $0 [llm|vlm|embed|all]"
        exit 1
        ;;
esac

echo ""
echo "All servers started. Logs in $LOG_DIR/"
echo "Start OfficeMind API: python -m src.api.app"
