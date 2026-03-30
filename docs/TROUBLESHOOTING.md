# OfficeMind 部署问题排查与解决措施 (Troubleshooting)

本文档记录了在 NVIDIA DGX Spark GB10 节点上部署 OfficeMind 全栈 AI 自动化办公助手时遇到的主要技术问题、根本原因分析以及最终的解决措施。这些经验对于在类似 Blackwell 架构和受限网络环境下部署大模型具有重要参考价值。

## 1. Ollama 无法识别 GPU (回退到 CPU 推理)

**现象描述**：
启动 Ollama 服务并加载 `llava:7b` 模型时，日志显示 `inference compute: library=cpu` 和 `total_vram="0 B"`，模型推理极慢，完全没有使用 GB10 的 GPU 算力。

**根本原因**：
DGX Spark GB10 节点使用的是 **CUDA 13.0**。虽然我们上传了支持 CUDA 13 的 Ollama ARM64 二进制文件，但其自带的 `cuda_v13` 依赖库目录中仅包含了 `libcudart.so.13.0.96`，缺少了进行矩阵运算的核心库 `libcublas.so.13` 和 `libcublasLt.so.13`。由于缺少这些关键动态链接库，Ollama 的 GPU 检测机制失败，自动回退到了 CPU 模式。

**解决措施**：
无需重新下载庞大的 CUDA 库文件，直接利用节点系统自带的 CUDA 13 库创建符号链接。
编写并执行了 `scripts/fix_ollama_gpu.sh` 脚本：
1. 定位系统 CUDA 库路径：`/usr/local/cuda-13.0/targets/sbsa-linux/lib`
2. 将系统中的 `libcublas.so.13.0.2.14` 和 `libcublasLt.so.13.0.2.14` 软链接到 Ollama 的 `~/.local/lib/ollama/cuda_v13/` 目录下。
3. 补全 `libggml-base.so` 的版本号软链接。
4. 在启动 Ollama 时，显式导出 `LD_LIBRARY_PATH` 包含这两个路径。

## 2. vLLM 与 CUDA 版本不兼容 (libcudart.so.12 缺失)

**现象描述**：
尝试通过 `pip install vllm` 安装 vLLM 0.18.0 后，导入时报错 `libcudart.so.12: cannot open shared object file: No such file or directory`。

**根本原因**：
PyPI 上预编译的 vLLM 和 PyTorch 包是基于 **CUDA 12.x** 编译的，硬编码了对 `libcudart.so.12` 的依赖。而 GB10 节点环境是纯粹的 **CUDA 13.0**。即使设置了环境变量或创建了软链接，底层 PyTorch 的 C++ 扩展依然会因为 ABI 不兼容或缺少其他 CUDA 12 特定库（如 `libtorch_cuda.so`）而崩溃。

**解决措施**：
放弃在当前 conda 环境中强行使用预编译的 vLLM。改为采用以下两种替代方案：
1. **主 LLM 推理**：使用 `llama-cpp-python` 加载 GGUF 格式模型（`qwen2.5-72b-instruct-q4_k_m.gguf`），通过配置 `n_gpu_layers=-1` 将计算完全卸载到 GPU。
2. **VLM 视觉推理**：使用自带 CUDA 13 兼容层的 Ollama 运行 `llava:7b`。

## 3. 节点网络限制与大文件传输中断

**现象描述**：
1. 在节点上直接使用 `wget` 或 `curl` 从 GitHub 下载 Ollama 二进制文件时，速度极慢（~9KB/s）或直接连接超时。
2. 尝试通过 SFTP 从本地向节点传输大文件（如 600MB 的 CUDA 库）时，传输中途 SSH 连接被重置（`Connection reset by peer`）。

**根本原因**：
1. 节点所在的网络环境对 GitHub 等境外开发资源的访问存在严格的带宽限制或防火墙拦截。
2. 节点的 SSH 服务配置了严格的会话超时机制和防暴力破解（Rate Limiting）策略。长时间的大文件传输或高频的 SSH 连接建立会触发安全机制，导致连接被强制切断。

**解决措施**：
1. **绕过 GitHub 限制**：优先使用国内镜像源（如 ModelScope 魔搭社区下载模型，清华/阿里镜像源安装 Python 包）。
2. **优化传输策略**：
   - 放弃单次大文件 SFTP 传输。
   - 使用 `rsync -avz` 利用 SSH 压缩进行断点续传。
   - 在脚本中加入 `sleep` 冷却时间，避免高频发起 SSH 连接触发节点的封锁机制。

## 4. 架构不匹配 (x86_64 vs aarch64)

**现象描述**：
节点上原本存在一个 `ollama-linux-amd64.tgz` 安装包，但解压后无法运行，提示 `Exec format error`。

**根本原因**：
DGX Spark GB10 节点使用的是基于 ARM 架构的 NVIDIA Grace CPU（`aarch64`），而下载的安装包是为 Intel/AMD x86_64 架构编译的。

**解决措施**：
重新从官方渠道获取并上传专为 ARM64 编译的二进制文件（`ollama-linux-arm64`），确保所有二进制依赖（包括 Node.js 等）均显式指定为 `arm64` 或 `aarch64` 版本。

## 总结

在 NVIDIA DGX Spark GB10 (Blackwell + Grace ARM64) 这样前沿的硬件平台上部署全栈 AI 应用，核心挑战在于**软件生态的兼容性**（CUDA 13 支持、ARM64 架构适配）。通过灵活切换推理后端（llama.cpp + Ollama）、巧妙利用系统自带库（软链接修复 GPU 识别），以及适应性的网络传输策略，最终成功实现了 OfficeMind 的全本地化、全 GPU 加速部署。
