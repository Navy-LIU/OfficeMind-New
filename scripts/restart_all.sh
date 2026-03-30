#!/usr/bin/env bash
# =============================================================================
# OfficeMind — 一键重启所有服务（DGX Spark GB10）
# 执行顺序：Ollama GPU → LLM(8000) → VLM(8001) → Embedding(8002) → Agent(7860)
# =============================================================================
set -euo pipefail

LOGS_DIR="$HOME/logs/officemind"
MODELS_DIR="$HOME/models"
CUDA_SYS="/usr/local/cuda-13.0/targets/sbsa-linux/lib"
OLLAMA_CUDA="$HOME/.local/lib/ollama/cuda_v13"
SERVICES_DIR="$(cd "$(dirname "$0")/../services" && pwd)"

mkdir -p "$LOGS_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OfficeMind — DGX Spark GB10 服务启动"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 0. 停止旧进程 ─────────────────────────────────────────────────────────────
echo "[0] 清理旧进程..."
for svc in "llm_service" "vlm_service" "embedding_service" "officemind_agent"; do
    pkill -f "$svc" 2>/dev/null && echo "  Stopped: $svc" || true
done
sleep 2

# ── 1. 启动 Ollama（GPU 模式）────────────────────────────────────────────────
echo "[1] 启动 Ollama GPU 服务..."
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_HOST="0.0.0.0:11434"
export OLLAMA_NUM_PARALLEL=2
export LD_LIBRARY_PATH="${CUDA_SYS}:${OLLAMA_CUDA}:${LD_LIBRARY_PATH:-}"

nohup "$HOME/.local/bin/ollama" serve \
    > "$LOGS_DIR/ollama.log" 2>&1 &
echo "  Ollama PID: $!"

# 等待 Ollama 就绪（最多 20 秒）
for i in $(seq 1 10); do
    sleep 2
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✅ Ollama ready"
        break
    fi
    echo "  Waiting Ollama... (${i}/10)"
done

# ── 2. 启动 LLM 服务（8000）──────────────────────────────────────────────────
echo "[2] 启动 LLM 服务 (port 8000)..."
nohup python3 "$SERVICES_DIR/llm_service.py" \
    > "$LOGS_DIR/llm.log" 2>&1 &
echo "  LLM PID: $!"
echo "  ⏳ 等待 GPU 模型加载（约 60 秒）..."
sleep 60

# ── 3. 启动 VLM 服务（8001）──────────────────────────────────────────────────
echo "[3] 启动 VLM 服务 (port 8001)..."
nohup python3 "$SERVICES_DIR/vlm_service.py" \
    > "$LOGS_DIR/vlm.log" 2>&1 &
echo "  VLM PID: $!"
sleep 5

# ── 4. 启动 Embedding 服务（8002）────────────────────────────────────────────
echo "[4] 启动 Embedding 服务 (port 8002)..."
nohup python3 "$SERVICES_DIR/embedding_service.py" \
    > "$LOGS_DIR/embedding.log" 2>&1 &
echo "  Embedding PID: $!"
sleep 5

# ── 5. 启动 Agent（7860）─────────────────────────────────────────────────────
echo "[5] 启动 OfficeMind Agent (port 7860)..."
nohup python3 "$SERVICES_DIR/officemind_agent.py" \
    > "$LOGS_DIR/agent.log" 2>&1 &
echo "  Agent PID: $!"
sleep 5

# ── 6. 健康检查 ───────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  服务健康检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for port_svc in "8000:LLM" "8001:VLM" "8002:Embedding" "7860:Agent"; do
    port="${port_svc%%:*}"
    svc="${port_svc##*:}"
    status=$(curl -sf "http://localhost:${port}/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "❌ not ready")
    echo "  ${svc} (:${port}) → ${status}"
done

echo ""
echo "  日志目录: $LOGS_DIR"
echo "  Ollama 模型: $(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; [print('  -',m['name']) for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
