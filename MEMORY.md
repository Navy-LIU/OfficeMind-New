# MEMORY.md - OfficeMind 长期记忆

## 系统架构

| 组件 | 配置 |
|------|------|
| Gateway | ws://127.0.0.1:9000 |
| Dashboard | http://192.168.110.59:9000/ |
| 微信 | openclaw-weixin 已连接 |
| 模型 | 全本地 ollama |

## 模型配置

| 模型 | ID | 状态 | 用途 |
|------|-----|------|------|
| Qwen2.5-72B-Instruct-GGUF | qwen2.5:72b (vLLM) | 下载中 11/42 | vLLM高性能推理 |
| Qwen2.5-72B-Instruct | qwen2.5:72b (Ollama) | 就绪 | Ollama备用 |
| Qwen3.5-35B | qwen3.5:35b | 就绪 | 日常对话 |
| Nemotron-30B | nemotron-3-nano:30b | 就绪 | 轻量任务 |
| LLaVA-7B | llava:7b | 就绪 | 图像理解 |
| GLM-OCR | glm-ocr:latest | 就绪 | OCR文字识别 |

## vLLM配置

| 项目 | 值 |
|------|-----|
| vLLM地址 | http://localhost:8000/v1 |
| 模型路径 | /home/xsuper/models/huggingface/qwen2.5-72b |
| 下载进度 | ~47GB / ~150GB |
| 预计完成 | 约2小时后 |

## 安全策略

- sandbox: 宽松模式（工具完整）
- auth rate limit: 5次/分钟
- plugins.allow: 仅微信插件

## 用户偏好

_待填充（从对话中学习）_

## 项目上下文

- 工作目录: ~/claude-code-haha/officemind
- 配置文件: ~/.openclaw/openclaw.json

## 重要决策

- 优先使用本地模型，保护隐私
- 外部操作需明确确认
- 危险命令使用安全替代方案

---

_最后更新: 2026-04-05_
