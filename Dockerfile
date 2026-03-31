# 使用 NVIDIA 官方 CUDA 12.4 镜像作为基础（GB10 节点已预装驱动）
# 注意：虽然节点是 CUDA 13，但 CUDA 12.4 镜像通常具有更好的库兼容性
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 暴露 Agent 端口
EXPOSE 7860

# 启动命令
CMD ["python3", "services/officemind_agent.py"]
