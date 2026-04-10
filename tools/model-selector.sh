#!/bin/bash
# model-selector.sh - 动态模型选择器
# 遵守 113GB 运存限制

set -e

# 模型配置
DEFAULT_MODEL="qwen3.5:35b"
LARGE_MODEL="qwen2.5:72b"
LIGHT_MODEL="nemotron-3-nano:30b"
VISION_MODEL="llava:7b"
OCR_MODEL="glm-ocr:latest"

# 运存限制: 100GB
MAX_MEMORY_GB=100

# 获取可用内存 (GB)
get_available_memory() {
    free -g | awk 'NR==2 {print $7}'
}

# 检查是否可以加载大模型 (需要 ~50GB)
can_load_large() {
    local available=$(get_available_memory)
    # 需要预留 25GB 给系统和其他进程 (100GB - 48GB - 25GB = 27GB余量)
    [ $available -gt 55 ]
}

# 分析任务复杂度
analyze_complexity() {
    local input="$1"
    local length=${#input}

    # 关键词检测 - 优先级从高到低
    if echo "$input" | grep -qiE "图片|图像|截图|看图|分析图片"; then
        echo "vision"
    elif echo "$input" | grep -qiE "OCR|文字|识别|提取|扫描"; then
        echo "ocr"
    elif echo "$input" | grep -qiE "代码|编程|调试|函数|算法|写代码|debug"; then
        echo "code"
    elif echo "$input" | grep -qiE "分析|架构|设计|复杂|深度|详细"; then
        echo "high"
    elif echo "$input" | grep -qiE "简单|快速|列表|显示|天气|今天"; then
        echo "low"
    elif [ $length -gt 5000 ]; then
        echo "high"
    elif [ $length -gt 2000 ]; then
        echo "medium"
    else
        echo "default"
    fi
}

# 选择模型（遵守 113GB 限制）
select_model() {
    local task="${1:-对话}"
    local complexity=$(analyze_complexity "$task")
    local available=$(get_available_memory)

    case $complexity in
        vision)
            echo "$VISION_MODEL"
            ;;
        ocr)
            echo "$OCR_MODEL"
            ;;
        code)
            # 代码任务：检查内存
            if can_load_large; then
                echo "$LARGE_MODEL"
            else
                echo "$DEFAULT_MODEL"
            fi
            ;;
        high)
            # 复杂推理：检查内存
            if can_load_large && [ $available -gt 55 ]; then
                echo "$LARGE_MODEL"
            elif [ $available -gt 30 ]; then
                echo "$DEFAULT_MODEL"
            else
                echo "$LIGHT_MODEL"
            fi
            ;;
        medium)
            if [ $available -gt 30 ]; then
                echo "$DEFAULT_MODEL"
            else
                echo "$LIGHT_MODEL"
            fi
            ;;
        low|default|*)
            # 简单任务用轻量模型
            if [ $available -gt 25 ]; then
                echo "$DEFAULT_MODEL"
            else
                echo "$LIGHT_MODEL"
            fi
            ;;
    esac
}

# 获取当前运行的模型
get_current_model() {
    ollama ps 2>/dev/null | grep -v "^NAME" | awk '{print $1}' | head -1 || echo "none"
}

# 显示状态
show_status() {
    echo "======================================"
    echo "       模型路由状态 (100GB 限制)"
    echo "======================================"
    echo "可用内存: $(get_available_memory)GB / 100GB"
    echo "当前模型: $(get_current_model)"
    echo ""
    echo "可用模型:"
    echo "  - $DEFAULT_MODEL (23GB, 日常)"
    echo "  - $LARGE_MODEL   (47GB, 复杂推理)"
    echo "  - $LIGHT_MODEL   (24GB, 轻量)"
    echo "  - $VISION_MODEL  (4.7GB, 视觉)"
    echo "  - $OCR_MODEL     (2.2GB, OCR)"
    echo ""
    echo "内存安全组合:"
    echo "  ✓ qwen2.5:72b + llava:7b = 54GB"
    echo "  ✓ qwen3.5:35b + llava:7b = 30GB"
    echo "  ✗ 不要同时加载两个大模型 (>70GB)"
    echo "======================================"
}

# 主逻辑
CMD="${1:-select}"
shift || true

case $CMD in
    select)
        select_model "$@"
        ;;
    list)
        echo "可用模型:"
        echo "  - $DEFAULT_MODEL (默认)"
        echo "  - $LARGE_MODEL (大型)"
        echo "  - $LIGHT_MODEL (轻量)"
        echo "  - $VISION_MODEL (视觉)"
        echo "  - $OCR_MODEL (OCR)"
        ;;
    status)
        show_status
        ;;
    test)
        MODEL=$(select_model "$@")
        echo "选择模型: $MODEL"
        ollama run "$MODEL" "回复'测试成功'，简洁回复。" --verbose
        ;;
    can-load)
        if can_load_large; then
            echo "可以加载大模型 (qwen2.5:72b)"
        else
            echo "内存不足，建议使用 qwen3.5:35b 或 nemotron"
        fi
        ;;
esac
