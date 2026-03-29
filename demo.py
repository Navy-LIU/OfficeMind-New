#!/usr/bin/env python3
"""
OfficeMind Demo Script
Demonstrates 3 core scenarios on DGX Spark GB10.
Run: python demo.py [email|report|rag|all]
"""
import asyncio, sys, json, os
from openai import OpenAI

BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = os.getenv("LLM_MODEL", "Qwen3-Thinking")
SYS_PROMPT = (
    "你是 OfficeMind，企业 AI 办公助手，运行在 NVIDIA DGX Spark GB10 上，"
    "拥有 128GB 统一内存（Blackwell 架构），所有推理均在本地完成，无需云端 API。"
)

client = OpenAI(base_url=BASE_URL, api_key="EMPTY")

def chat(user_msg: str, system: str = SYS_PROMPT, temperature: float = 0.1) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        temperature=temperature,
        max_tokens=2048,
    )
    return resp.choices[0].message.content

def demo_email():
    print("\n" + "═" * 70)
    print("DEMO 1: 邮件智能分析")
    print("═" * 70)
    
    email_content = """
发件人: zhang.wei@company.com
收件人: team@company.com
主题: 【紧急】Q2销售复盘 + Q3目标制定

各位同事，

本季度销售额完成 1,850 万，同比增长 23%，超额完成目标 15%。
华东区表现突出（完成率 138%），华北区略有不足（完成率 87%）。

需要各区域负责人：
1. 周五（4月12日）18:00前提交Q2详细数据报告
2. 下周一（4月15日）上午10:00全员复盘会，地点：总部3楼会议室
3. 同步提交Q3目标计划，需包含月度分解

另外，客户满意度调研结果显示 NPS 得分 72，需要重点关注华北区客户流失问题。

请各位务必准时参会，如有特殊情况请提前告知。

张伟
销售总监
"""
    
    result = chat(
        f"请分析以下邮件，提取所有行动项（含负责人、截止日期）、关键数据和优先级，"
        f"并生成一份专业的回复草稿。\n\n{email_content}"
    )
    print(result)

def demo_report():
    print("\n" + "═" * 70)
    print("DEMO 2: 工作日报自动生成")
    print("═" * 70)
    
    raw_data = """
今日工作数据（2026-03-29）：
- 客户拜访：华为技术（达成合作意向）、腾讯云（续签合同 120 万）、字节跳动（初步接触）
- 签署合同：2 份，总金额 85 万（腾讯云 120 万 + 字节 -35 万折扣）
- 处理邮件：15 封（回复 12 封，待处理 3 封）
- 完成产品演示：2 场（华为 + 腾讯）
- 遇到问题：华为要求定制化接口，预计开发周期 3 周
- 明日计划：跟进字节跳动需求，准备华为技术方案
"""
    
    result = chat(
        f"请根据以下数据生成今日工作日报，格式专业，包含：执行摘要、工作完成情况、"
        f"数据亮点、问题与风险、明日计划。使用 Markdown 格式。\n\n{raw_data}",
        temperature=0.2
    )
    print(result)

def demo_data_analysis():
    print("\n" + "═" * 70)
    print("DEMO 3: 销售数据分析 + 趋势预测")
    print("═" * 70)
    
    sales_data = """
2025年月度销售数据（万元）：
1月: 120, 2月: 95（春节影响）, 3月: 180, 4月: 210, 5月: 175, 6月: 230,
7月: 195, 8月: 220, 9月: 265, 10月: 240, 11月: 310, 12月: 285

2026年Q1数据：
1月: 195, 2月: 160（春节）, 3月: 预测中

团队规模：12人
客单价：平均 45 万
"""
    
    result = chat(
        f"请分析以下销售数据：\n{sales_data}\n\n"
        f"要求：\n"
        f"1. 计算年度总额、月均、同比增长率\n"
        f"2. 识别季节性规律和趋势\n"
        f"3. 预测 2026 年 3 月和全年数据\n"
        f"4. 给出 3 条具体的业务建议\n"
        f"5. 用 Markdown 表格展示关键数据",
        temperature=0.1
    )
    print(result)

def demo_rag():
    print("\n" + "═" * 70)
    print("DEMO 4: RAG 文档问答（本地知识库）")
    print("═" * 70)
    
    # Simulate RAG with context injection
    contract_excerpt = """
【采购合同节选】
合同编号：HW-2026-0329-001
甲方：华为技术有限公司
乙方：OfficeMind科技有限公司

第五条 付款方式：
5.1 合同签订后5个工作日内，甲方支付合同总额30%作为预付款。
5.2 项目验收合格后15个工作日内，甲方支付合同总额60%。
5.3 质保期（12个月）届满后10个工作日内，甲方支付剩余10%。

第八条 违约责任：
8.1 乙方逾期交付，每逾期一天按合同总额0.1%支付违约金，最高不超过合同总额10%。
8.2 甲方逾期付款，按中国人民银行同期贷款利率的1.5倍计算利息。

第十条 知识产权：
10.1 本项目定制开发的代码、文档归甲方所有。
10.2 乙方通用技术框架和工具的知识产权归乙方所有。
"""
    
    result = chat(
        f"基于以下合同内容回答问题：\n\n{contract_excerpt}\n\n"
        f"问题：\n"
        f"1. 付款分几期，各期比例是多少？\n"
        f"2. 如果我方（乙方）逾期10天交付，违约金是多少（合同总额100万）？\n"
        f"3. 项目代码的知识产权归谁？有什么风险点需要注意？"
    )
    print(result)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    print("=" * 70)
    print("OfficeMind — NVIDIA DGX Spark GB10 Demo")
    print(f"Model: {MODEL} @ {BASE_URL}")
    print("=" * 70)
    
    # Test connection
    try:
        models = client.models.list()
        print(f"✓ vLLM connected. Available models: {[m.id for m in models.data]}")
    except Exception as e:
        print(f"✗ vLLM connection failed: {e}")
        print("Please start vLLM first: bash scripts/serve_models.sh llm")
        sys.exit(1)
    
    if mode in ("email", "all"):
        demo_email()
    if mode in ("report", "all"):
        demo_report()
    if mode in ("analysis", "all"):
        demo_data_analysis()
    if mode in ("rag", "all"):
        demo_rag()
    
    print("\n" + "=" * 70)
    print("Demo complete! OfficeMind running on NVIDIA DGX Spark GB10")
    print("All inference is 100% local — no cloud API calls.")
    print("=" * 70)
