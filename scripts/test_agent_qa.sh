#!/bin/bash
# ============================================================
# OfficeMind — NemoClaw Agent Q&A Test Suite
# Runs after: nemoclaw officemind connect
# ============================================================

export PATH="$HOME/.local/bin:$(npm config get prefix 2>/dev/null)/bin:$PATH"
SANDBOX="officemind"
AGENT_CMD="openclaw agent --agent main --local"

echo "============================================"
echo "  OfficeMind Agent Q&A Test Suite"
echo "  Sandbox: $SANDBOX"
echo "  Model: Qwen3-80B-A3B-Thinking (local)"
echo "============================================"

run_test() {
    local id=$1
    local desc=$2
    local msg=$3
    echo ""
    echo "──────────────────────────────────────────"
    echo "[TEST $id] $desc"
    echo "──────────────────────────────────────────"
    nemoclaw "$SANDBOX" connect -- \
        $AGENT_CMD -m "$msg" --session-id "test_$id" 2>&1
}

# Test 1: 自我介绍
run_test 1 "自我介绍 & 能力说明" \
    "你好！请用中文介绍你自己，说明你运行在什么硬件上，以及你能帮我做哪些办公自动化任务。"

# Test 2: 邮件分析
run_test 2 "邮件智能分析" \
    "请分析这封邮件并提取行动项：主题：Q1季度销售复盘，内容：本季度销售额达到500万，同比增长20%，华东区贡献最大。需要在本周五前提交各区域详细数据，并在下周一召开全员复盘会议。请各区域负责人提前准备PPT。"

# Test 3: 日报生成
run_test 3 "日报自动生成" \
    "请帮我生成今日工作日报。今日完成：1.拜访客户3家（华为、腾讯、字节），2.签署合同2份（总金额85万），3.处理邮件15封，4.完成季度销售预测报告。明日计划：参加产品发布会，跟进3个待签合同。"

# Test 4: 文档问答
run_test 4 "文档智能问答" \
    "这份合同条款中，关于违约责任的规定是什么？合同内容：第五条 违约责任：甲方未按时交付产品的，每延误一天需支付合同总金额0.1%的违约金，最高不超过合同总金额的10%。乙方未按时付款的，每延误一天需支付未付款项0.05%的滞纳金。"

# Test 5: 跨系统数据整理
run_test 5 "数据整理与分析" \
    "请帮我整理以下销售数据并生成分析报告：1月：120万，2月：95万，3月：180万，4月：210万，5月：175万，6月：230万。请计算总额、月均、最高月、增长趋势，并给出销售建议。"

echo ""
echo "============================================"
echo "  All tests completed!"
echo "  Check logs at: ~/.openclaw/logs/"
echo "============================================"
