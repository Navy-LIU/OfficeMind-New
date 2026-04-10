# model-router.md - 动态模型路由配置

## 系统资源约束

- **总运存限制**: ≤ 100GB
- **当前可用内存**: ~65GB
- **GPU 显存**: 32GB

## 模型内存占用矩阵

| 模型 | 磁盘大小 | 运行时内存 | GPU 显存 |
|------|----------|-----------|----------|
| **qwen2.5:72b** | 47GB | ~48GB | 32GB |
| **qwen3.5:35b** | 23GB | ~24GB | 24GB |
| **nemotron-3-nano:30b** | 24GB | ~18GB | 16GB |
| **llava:7b** | 4.7GB | ~6GB | 6GB |
| **glm-ocr:latest** | 2.2GB | ~2GB | - |

## 100GB 运存安全配置

### 模型组合策略（不超过 100GB）

| 场景 | 加载模型 | 总内存占用 | 可用空间 |
|------|----------|-----------|----------|
| **日常对话** | qwen3.5:35b | ~24GB | 76GB |
| **复杂推理** | qwen2.5:72b | ~48GB | 52GB |
| **代码+对话** | qwen3.5:35b + llava:7b | ~30GB | 70GB |
| **重载模式** | qwen2.5:72b + llava:7b | ~54GB | 46GB |
| **轻量模式** | nemotron | ~18GB | 82GB |

**注意**: 不要同时加载 qwen2.5:72b + qwen3.5:35b (72GB > 100GB 限制)

## 路由规则

### 按任务类型（113GB 限制内）

```yaml
复杂推理/代码生成/深度分析:
  - model: qwen2.5:72b
    reason: "72B 参数，复杂推理能力强"
    memory: ~48GB

代码生成/调试（兼顾速度）:
  - model: qwen3.5:35b
    reason: "速度更快，效果均衡"
    memory: ~24GB

日常对话/快速任务:
  - model: qwen3.5:35b 或 nemotron-3-nano:30b
    reason: "qwen3.5 已预加载，nemotron 更轻量"
    memory: 18-24GB

图像分析/看图:
  - model: llava:7b
    reason: "专用视觉模型"
    memory: ~6GB

OCR 文字识别:
  - model: glm-ocr:latest
    reason: "高精度中文 OCR"
    memory: ~2GB
```

### 内存自适应降级

当系统内存不足时自动降级：

- **可用内存 > 60GB**: 可用 qwen2.5:72b
- **可用内存 40-60GB**: 降级到 qwen3.5:35b + llava:7b
- **可用内存 25-40GB**: 使用 qwen3.5:35b
- **可用内存 < 25GB**: 降级到 nemotron-3-nano:30b

### 按上下文长度

- **短 (< 4k tokens)**: nemotron 或 qwen3.5:35b
- **中 (4k-32k tokens)**: qwen3.5:35b
- **长 (> 32k tokens)**: qwen2.5:72b (注意内存)

### 按复杂度

- **简单**: nemotron > qwen3.5:35b > qwen2.5:72b
- **中等**: qwen3.5:35b > qwen2.5:72b
- **复杂**: qwen2.5:72b (确认内存充足时)

## 调用示例

### 直接调用特定模型

```bash
# 使用 qwen2.5:72b 进行复杂分析
ollama run qwen2.5:72b "分析这个代码库的架构..."

# 使用 llava 分析图片
ollama run llava:7b "描述这张图片的内容"

# 使用 glm-ocr 提取文字
curl -X POST http://localhost:8001/ocr -d '{"image": "base64..."}'
```

### 在代码中调用

```javascript
// 根据任务选择模型
const model = selectModel({
  task: 'code-generation',
  contextLength: 5000,
  complexity: 'high'
});

// 调用
const response = await ollama.chat({
  model: model,
  messages: [{ role: 'user', content: prompt }]
});
```

## 性能监控

| 模型 | 平均响应时间 | 内存占用 | GPU 使用 |
|------|-------------|----------|----------|
| qwen2.5:72b | ~30s | ~48GB | 高 |
| qwen3.5:35b | ~15s | ~24GB | 中 |
| nemotron | ~10s | ~18GB | 中低 |

## 配置优先级

1. **明确指定** > **任务路由** > **默认模型**
2. **资源优先**: 内存不足时自动降级到小模型
3. **负载均衡**: 多请求时轮询可用模型
