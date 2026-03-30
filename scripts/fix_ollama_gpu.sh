#!/usr/bin/env bash
# =============================================================================
# fix_ollama_gpu.sh — 修复 Ollama 在 DGX Spark GB10 上的 GPU 识别问题
#
# 问题根因：
#   Ollama v0.18.3 ARM64 二进制的 cuda_v13 目录仅包含 libcudart.so.13.0.96，
#   缺少 libcublas.so.13 和 libcublasLt.so.13，导致 Ollama 回退到 CPU 模式。
#
# 解决方案：
#   从系统 CUDA 13 目录创建符号链接到 Ollama 的 cuda_v13 目录。
# =============================================================================
set -euo pipefail

CUDA_SYS="/usr/local/cuda-13.0/targets/sbsa-linux/lib"
OLLAMA_CUDA="$HOME/.local/lib/ollama/cuda_v13"

echo "=== 修复 Ollama GPU 库（CUDA 13 符号链接）==="

# 检查系统 CUDA 库是否存在
if [ ! -f "${CUDA_SYS}/libcublas.so.13.0.2.14" ]; then
    echo "❌ 未找到系统 CUDA 13 库: ${CUDA_SYS}"
    echo "   请确认 CUDA 13.0 已安装（DGX Spark GB10 默认已安装）"
    exit 1
fi

mkdir -p "$OLLAMA_CUDA"

# libcublas
ln -sf "${CUDA_SYS}/libcublas.so.13.0.2.14"   "${OLLAMA_CUDA}/libcublas.so.13.0.2.14"
ln -sf "${OLLAMA_CUDA}/libcublas.so.13.0.2.14" "${OLLAMA_CUDA}/libcublas.so.13"
ln -sf "${OLLAMA_CUDA}/libcublas.so.13"         "${OLLAMA_CUDA}/libcublas.so"
echo "  ✅ libcublas.so.13 → ${CUDA_SYS}"

# libcublasLt
ln -sf "${CUDA_SYS}/libcublasLt.so.13.0.2.14"   "${OLLAMA_CUDA}/libcublasLt.so.13.0.2.14"
ln -sf "${OLLAMA_CUDA}/libcublasLt.so.13.0.2.14" "${OLLAMA_CUDA}/libcublasLt.so.13"
ln -sf "${OLLAMA_CUDA}/libcublasLt.so.13"         "${OLLAMA_CUDA}/libcublasLt.so"
echo "  ✅ libcublasLt.so.13 → ${CUDA_SYS}"

# libcudart（已有真实文件，只需补充软链）
if [ -f "${OLLAMA_CUDA}/libcudart.so.13.0.96" ]; then
    ln -sf "${OLLAMA_CUDA}/libcudart.so.13.0.96" "${OLLAMA_CUDA}/libcudart.so.13"
    ln -sf "${OLLAMA_CUDA}/libcudart.so.13"       "${OLLAMA_CUDA}/libcudart.so"
    echo "  ✅ libcudart.so.13 链接完成"
fi

# libggml-base 符号链接
OLLAMA_LIB="$HOME/.local/lib/ollama"
if [ -f "${OLLAMA_LIB}/libggml-base.so.0.0.0" ]; then
    ln -sf "${OLLAMA_LIB}/libggml-base.so.0.0.0" "${OLLAMA_LIB}/libggml-base.so.0"
    ln -sf "${OLLAMA_LIB}/libggml-base.so.0"      "${OLLAMA_LIB}/libggml-base.so"
    echo "  ✅ libggml-base.so 链接完成"
fi

echo ""
echo "=== 验证库文件 ==="
ls -la "$OLLAMA_CUDA/"

echo ""
echo "=== 重启 Ollama（带完整 CUDA 路径）==="
kill "$(cat /tmp/ollama.pid 2>/dev/null)" 2>/dev/null || true
sleep 2

export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_HOST="0.0.0.0:11434"
export LD_LIBRARY_PATH="${CUDA_SYS}:${OLLAMA_CUDA}:${LD_LIBRARY_PATH:-}"

nohup "$HOME/.local/bin/ollama" serve > /tmp/ollama_gpu.log 2>&1 &
echo "$!" > /tmp/ollama.pid
echo "  Ollama PID: $!"

# 等待启动
for i in $(seq 1 10); do
    sleep 2
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✅ Ollama 就绪！"
        break
    fi
    echo "  Waiting... (${i}/10)"
done

echo ""
echo "=== GPU 识别结果 ==="
grep -E "gpu|GPU|vram|VRAM|cuda|compute|library" /tmp/ollama_gpu.log 2>/dev/null | head -10 || echo "  (查看完整日志: /tmp/ollama_gpu.log)"
