# service-router.md - 服务路由配置

## 本地服务

| 服务 | 地址 | 用途 | 状态 |
|------|------|------|------|
| Ollama | http://127.0.0.1:11434 | 所有模型 | ✅ |
| GLM-OCR | http://localhost:8001 | 高精度 OCR | ✅ |
| BGE-M3 | http://localhost:8002 | 嵌入向量 | ⚠️ 未运行 |
| OpenClaw | ws://127.0.0.1:9000 | Gateway | ✅ |

## 模型服务路由

### 文本生成

```bash
# 通用对话
curl -X POST http://127.0.0.1:11434/chat \
  -d '{"model": "qwen3.5:35b", "messages": [...]}'

# 复杂推理
curl -X POST http://127.0.0.1:11434/chat \
  -d '{"model": "qwen2.5:72b", "messages": [...]}'
```

### 图像分析

```bash
# LLaVA (通用看图)
curl -X POST http://127.0.0.1:11434/chat \
  -d '{"model": "llava:7b", "images": ["base64..."], "messages": [...]}'
```

### OCR 文字识别

```bash
# GLM-OCR (高精度)
curl -X POST http://localhost:8001/ocr \
  -d '{"image": "base64...", "lang": "zh"}'

# Ollama GLM-OCR
curl -X POST http://127.0.0.1:11434/api/generate \
  -d '{"model": "glm-ocr:latest", "prompt": "提取图片中的文字"}'
```

## 动态路由决策

```
用户请求
    ↓
分析任务类型
    ↓
┌─────────────────────────────────────┐
│ 图像 + 文字识别 → GLM-OCR / LLaVA  │
│ 复杂推理/代码  → qwen2.5:72b        │
│ 日常对话       → qwen3.5:35b        │
│ 简单任务       → nemotron           │
└─────────────────────────────────────┘
    ↓
检查资源可用性
    ↓
执行并返回
```

## 负载管理（100GB 运存限制）

- **可用内存 > 60GB**: 可用 qwen2.5:72b（~48GB）
- **可用内存 40-60GB**: 降级到 qwen3.5:35b（~24GB）
- **可用内存 25-40GB**: 使用 qwen3.5:35b + llava:7b（~30GB）
- **可用内存 < 25GB**: 使用 nemotron（~18GB）

**安全组合（不超过 100GB）**:
- qwen2.5:72b + llava:7b = 54GB
- qwen3.5:35b + llava:7b = 30GB
- qwen2.5:72b 单独 = 48GB

## 故障转移

1. 主模型失败 → 自动切换 fallback
2. 服务不可用 → 尝试备用服务
3. 资源不足 → 提示用户并降级
