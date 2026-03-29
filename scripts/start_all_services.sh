#!/usr/bin/env bash
# OfficeMind 全栈启动脚本
# 架构：NemoClaw 控制层 → TRT-LLM 推理层 → BGE RAG 层 → Open WebUI 界面层
# 全部使用本地模型，无云端依赖
# 用法: bash scripts/start_all_services.sh
set -euo pipefail

CONDA_PYTHON=/home/xsuper/miniconda3/envs/ai311/bin/python
MODELS=/home/xsuper/models
LOGS=/tmp/officemind_logs
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$LOGS"

port_in_use() { ss -tlnp 2>/dev/null | grep -q ":${1}"; }

echo "=============================================="
echo "  OfficeMind — NVIDIA DGX Spark GB10"
echo "  TensorRT-LLM + NemoClaw 全本地部署"
echo "=============================================="

# ── Layer 1: TensorRT-LLM 推理层 ─────────────────

# Qwen3-80B-A3B-Thinking — 主推理 LLM（MoE，激活参数~3B，速度快）
if port_in_use 8000; then
    echo "[skip]  Qwen3-80B already on :8000"
else
    echo "[1/5] TRT-LLM Qwen3-80B → :8000"
    nohup "$CONDA_PYTHON" -m tensorrt_llm.serve \
        "$MODELS/Qwen3-next-80b-a3b-thinking" \
        --host 0.0.0.0 --port 8000 \
        --trust-remote-code \
        > "$LOGS/trtllm_qwen3.log" 2>&1 &
    echo "  PID=$!  |  tail -f $LOGS/trtllm_qwen3.log"
fi

# Qwen2.5-VL-7B-Instruct — 视觉理解 VLM（屏幕截图语义分析）
if port_in_use 8001; then
    echo "[skip]  Qwen2.5-VL already on :8001"
else
    VL_PATH=$(find "$MODELS" -maxdepth 4 -name "config.json" 2>/dev/null \
              | xargs grep -l "Qwen2-VL\|Qwen2\.5-VL" 2>/dev/null \
              | head -1 | xargs dirname 2>/dev/null \
              || echo "$MODELS/qwen/Qwen2___5-VL-7B-Instruct")
    echo "[2/5] TRT-LLM Qwen2.5-VL → :8001  ($VL_PATH)"
    nohup "$CONDA_PYTHON" -m tensorrt_llm.serve \
        "$VL_PATH" \
        --host 0.0.0.0 --port 8001 \
        --trust-remote-code \
        > "$LOGS/trtllm_qwenvl.log" 2>&1 &
    echo "  PID=$!"
fi

# ── Layer 2: BGE RAG 层 ───────────────────────────

if port_in_use 8002; then
    echo "[skip]  BGE API already on :8002"
else
    echo "[3/5] BGE Embedding/Reranker API → :8002"
    nohup "$CONDA_PYTHON" "$PROJECT_DIR/scripts/bge_api.py" \
        > "$LOGS/bge_api.log" 2>&1 &
    echo "  PID=$!"
fi

# ── Layer 3: OfficeMind FastAPI 后端 ─────────────

if port_in_use 7860; then
    echo "[skip]  OfficeMind API already on :7860"
else
    echo "[4/5] OfficeMind FastAPI → :7860"
    cd "$PROJECT_DIR"
    nohup "$CONDA_PYTHON" -m uvicorn src.api.app:app \
        --host 0.0.0.0 --port 7860 --workers 2 \
        > "$LOGS/officemind_api.log" 2>&1 &
    echo "  PID=$!"
fi

# ── Layer 4: Open WebUI 图形界面 ──────────────────

if port_in_use 3000; then
    echo "[skip]  Open WebUI already on :3000"
else
    echo "[5/5] Open WebUI → :3000"
    nohup "$CONDA_PYTHON" -m open_webui.main serve \
        --host 0.0.0.0 --port 3000 \
        > "$LOGS/open_webui.log" 2>&1 &
    echo "  PID=$!"
fi

# ── 状态汇报 ─────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 服务地址（运行 connect_spark.bat 建立 SSH 隧道后访问）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " http://localhost:3000   Open WebUI          图形对话界面"
echo " http://localhost:7860   OfficeMind API      /docs 查看接口"
echo " http://localhost:8000   TRT-LLM Qwen3-80B  主推理 LLM"
echo " http://localhost:8001   TRT-LLM Qwen2.5-VL 视觉理解 VLM"
echo " http://localhost:8002   BGE API             Embedding + Reranker"
echo ""
echo " NemoClaw 配置: .nemoclaw/config.json（全本地，无云端依赖）"
echo " 日志目录: $LOGS/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
