import requests
import json
from typing import List, Dict

class ReportGenerator:
    """
    高级 AI 架构师重构版：报告生成器
    场景：跨文档数据汇总 (Cross-Document Summarization)
    创新点：基于 Qwen3.5:35b 的多源数据聚合与结构化 Markdown 报告生成。
    """
    def __init__(self, llm_url="http://localhost:8000"):
        self.llm_url = llm_url

    def generate_report(self, topic: str, data_sources: List[Dict]) -> str:
        """
        根据多个数据源生成一份专业的《{topic}》报告。
        数据源可以是：RAG 检索结果、数据库查询结果、VLM 识别结果。
        """
        # 1. 数据预处理：将多个数据源聚合为结构化上下文
        context = ""
        for idx, source in enumerate(data_sources):
            context += f"数据源 {idx+1} ({source['type']}): {source['content']}\n\n"

        # 2. 生成报告提示词
        prompt = f"""
        你是一个高级办公助手。请根据以下多源数据，生成一份专业的《{topic}》报告。
        数据上下文：{context}
        要求：
        1. 使用 Markdown 格式，包含标题、摘要、数据分析、结论。
        2. 数据以表格形式呈现。
        3. 结论部分给出 3 条可执行建议。
        4. 全程使用中文。
        5. 报告应体现出跨文档汇总的深度，而不是简单的罗列。
        """
        
        payload = {
            "model": "qwen3.5:35b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0.3
        }
        
        try:
            resp = requests.post(f"{self.llm_url}/v1/chat/completions", json=payload, timeout=60)
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Report Generation Error: {str(e)}"

    def export_to_pdf(self, markdown_content: str, output_path: str):
        """
        将 Markdown 报告导出为 PDF。
        在 GB10 节点上，这通常通过 `manus-md-to-pdf` 工具或 `weasyprint` 实现。
        """
        # 模拟导出逻辑
        print(f"正在将报告导出至 {output_path}...")
        # 实际调用：os.system(f"manus-md-to-pdf {md_file} {output_path}")
        return f"PDF 报告已保存至 {output_path}"

if __name__ == "__main__":
    gen = ReportGenerator()
    # 模拟多源数据
    mock_data = [
        {"type": "RAG", "content": "2025年第一季度差旅预算执行率为 85%。"},
        {"type": "VLM", "content": "从屏幕截图中识别到 3 月份有 5 笔未报销的差旅单据。"},
        {"type": "DB", "content": "当前部门剩余预算为 12,500 元。"}
    ]
    # report = gen.generate_report("2025年Q1差旅预算执行分析报告", mock_data)
    # print(report)
