#!/bin/bash
# model-manager.sh - 智能模型管理器
# 根据任务类型自动切换最优模型

set -e

# 模型配置
MODELS_DIR="/root/.ollama/models"
DEFAULT_MODEL="qwen3.5:35b"
COMPLEX_MODEL="qwen2.5:72b"
LIGHT_MODEL="nemotron-3-nano:30b"
VISION_MODEL="llava:7b"
OCR_MODEL="glm-ocr:latest"

# vLLM配置
VLLM_PORT=8000
VLLM_MODEL="qwen2.5-72b"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 分析任务复杂度
analyze_task() {
    local input="$1"
    local length=${#input}

    # 优先级检测
    case "$input" in
        *图片*|*图像*|*截图*|*看图*|*分析图片*|*OCR*)
            echo "vision"
            return
            ;;
        *代码*|*编程*|*调试*|*函数*|*算法*|*写代码*|*debug*)
            echo "complex"
            return
            ;;
        *分析*|*架构*|*设计*|*复杂*|*深度*|*详细*|*详细解释*)
            echo "complex"
            return
            ;;
        *简单*|*快速*|*列表*|*显示*|*天气*|*时间*)
            echo "light"
            return
            ;;
    esac

    # 基于长度判断
    if [ $length -gt 3000 ]; then
        echo "complex"
    elif [ $length -gt 500 ]; then
        echo "medium"
    else
        echo "light"
    fi
}

# 获取当前运行的模型
get_current_model() {
    local result=$(ollama ps 2>/dev/null | grep -v "^NAME" | awk '{print $1}' | head -1)
    if [ -z "$result" ]; then
        echo "none"
    else
        echo "$result"
    fi
}

# 停止模型
stop_model() {
    local model="$1"
    log_info "Stopping model: $model"
    ollama stop "$model" 2>/dev/null || true
    sleep 1
}

# 加载模型到GPU
load_model() {
    local model="$1"
    local current=$(get_current_model)

    if [ "$current" == "$model" ]; then
        log_info "Model $model is already running"
        return 0
    fi

    if [ "$current" != "none" ]; then
        stop_model "$current"
    fi

    log_info "Loading model: $model"
    ollama run "$model" &
    OLLAMA_PID=$!

    # 等待模型加载
    for i in {1..30}; do
        sleep 2
        if ollama ps 2>/dev/null | grep -q "$model"; then
            log_info "Model $model loaded successfully"
            return 0
        fi
        echo -n "."
    done

    log_error "Failed to load model $model"
    return 1
}

# 启动vLLM服务
start_vllm() {
    log_info "Starting vLLM service..."

    # 检查是否已有vLLM运行
    if curl -s http://localhost:$VLLM_PORT/health > /dev/null 2>&1; then
        log_info "vLLM is already running"
        return 0
    fi

    # 使用Ollama的qwen2.5:72b通过vLLM
    nohup vllm serve ollama:///$COMPLEX_MODEL \
        --port $VLLM_PORT \
        --gpu-memory-utilization 0.90 \
        --max-model-len 32768 \
        > /tmp/vllm.log 2>&1 &

    VLLM_PID=$!
    log_info "vLLM started with PID: $VLLM_PID"

    # 等待vLLM就绪
    for i in {1..60}; do
        sleep 2
        if curl -s http://localhost:$VLLM_PORT/health > /dev/null 2>&1; then
            log_info "vLLM is ready"
            return 0
        fi
        echo -n "."
    done

    log_error "Failed to start vLLM"
    return 1
}

# 停止vLLM服务
stop_vllm() {
    log_info "Stopping vLLM service..."
    pkill -f "vllm serve" 2>/dev/null || true
    sleep 2
}

# 选择最优模型
select_model() {
    local task="${1:-对话}"
    local complexity=$(analyze_task "$task")

    case $complexity in
        vision)
            echo "$VISION_MODEL"
            ;;
        complex)
            # 复杂任务优先使用vLLM
            if curl -s http://localhost:$VLLM_PORT/health > /dev/null 2>&1; then
                echo "vllm"
            else
                echo "$COMPLEX_MODEL"
            fi
            ;;
        medium)
            echo "$DEFAULT_MODEL"
            ;;
        light|*)
            echo "$LIGHT_MODEL"
            ;;
    esac
}

# 路由到模型
route_to_model() {
    local task="$1"
    local model=$(select_model "$task")

    case "$model" in
        vllm)
            log_info "Routing to vLLM (qwen2.5-72b)"
            start_vllm
            ;;
        *)
            log_info "Routing to Ollama: $model"
            load_model "$model"
            ;;
    esac
}

# 状态显示
show_status() {
    echo "======================================"
    echo "       模型管理状态"
    echo "======================================"
    echo ""

    echo "Ollama 模型:"
    ollama list 2>/dev/null | grep -v "^" || echo "  无"
    echo ""

    echo "当前运行:"
    local current=$(get_current_model)
    if [ "$current" != "none" ]; then
        echo "  $current"
    else
        echo "  无"
    fi
    echo ""

    echo "GPU 状态:"
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "  N/A"
    echo ""

    echo "vLLM 状态:"
    if curl -s http://localhost:$VLLM_PORT/health > /dev/null 2>&1; then
        echo "  ✅ 运行中 (端口 $VLLM_PORT)"
    else
        echo "  ❌ 未运行"
    fi
    echo ""

    echo "======================================"
    echo "推荐使用:"
    echo "  日常对话 → qwen3.5:35b"
    echo "  复杂推理 → qwen2.5:72b (vLLM)"
    echo "  轻量任务 → nemotron"
    echo "  图像理解 → llava:7b"
    echo "  OCR识别  → glm-ocr:latest"
    echo "======================================"
}

# 主逻辑
CMD="${1:-status}"
shift || true

case "$CMD" in
    select)
        select_model "$@"
        ;;
    load)
        load_model "$2"
        ;;
    route)
        route_to_model "$2"
        ;;
    start-vllm)
        start_vllm
        ;;
    stop-vllm)
        stop_vllm
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 {select|load|route|start-vllm|stop-vllm|status}"
        echo ""
        show_status
        ;;
esac