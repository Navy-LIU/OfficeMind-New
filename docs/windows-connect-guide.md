# Windows 11 图形化连接 DGX Spark GB10 完整指南

> **节点信息**  
> - SSH 地址：`ssh xsuper@106.13.186.155 -p 6059`  
> - 密码：`QOW$y5)b`  
> - 平台：NVIDIA DGX Spark GB10（128GB 统一内存，Blackwell 架构）

---

## 方案总览

| 方案 | 工具 | 适用场景 | 推荐指数 |
|---|---|---|---|
| **方案 A** | MobaXterm（SSH + SFTP + 端口转发一体化） | 日常开发首选，功能最全 | ⭐⭐⭐⭐⭐ |
| **方案 B** | VS Code Remote-SSH | 写代码、调试 Python | ⭐⭐⭐⭐⭐ |
| **方案 C** | Open WebUI（浏览器访问大模型） | 图形化对话大模型 | ⭐⭐⭐⭐ |
| **方案 D** | JupyterLab（浏览器 Notebook） | 数据分析、实验 | ⭐⭐⭐⭐ |
| **方案 E** | RDP 远程桌面（完整 Linux GUI） | 需要完整桌面环境 | ⭐⭐⭐ |

---

## 方案 A：MobaXterm（强烈推荐，一体化图形化工具）

MobaXterm 是 Windows 上最强大的 SSH 客户端，内置 SFTP 文件管理器、端口转发、X11 图形转发，**一个工具解决所有需求**。

### 安装步骤

1. 下载 MobaXterm 免费版：https://mobaxterm.mobatek.net/download-home-edition.html
2. 选择 **Installer edition**，安装后打开。

### 连接 DGX Spark

1. 点击左上角 **Session** → **SSH**
2. 填写以下信息：

```
Remote host:  106.13.186.155
Username:     xsuper
Port:         6059
```

3. 点击 **Advanced SSH settings** → 勾选 **Use private key**（如有密钥）或直接用密码。
4. 点击 **OK**，输入密码 `QOW$y5)b`，连接成功。

### MobaXterm 核心功能

连接成功后，左侧自动出现 **SFTP 文件管理器**，可直接拖拽上传/下载文件（包括模型文件）。

**端口转发（访问节点上的 Web 服务）**：

1. 点击 **Tunneling** → **New SSH tunnel**
2. 配置如下（将节点 8000 端口映射到本地）：

```
Tunnel type:    Local port forwarding
Local port:     8000
Remote server:  localhost
Remote port:    8000
SSH server:     106.13.186.155
SSH port:       6059
SSH user:       xsuper
```

3. 点击 **Start**，然后在 Windows 浏览器访问 `http://localhost:8000` 即可操控大模型。

---

## 方案 B：VS Code Remote-SSH（写代码首选）

### 安装步骤

1. 安装 [VS Code](https://code.visualstudio.com/)
2. 安装扩展：**Remote - SSH**（搜索 `ms-vscode-remote.remote-ssh`）

### 配置 SSH

按 `Ctrl+Shift+P` → 输入 `Remote-SSH: Open SSH Configuration File` → 选择 `C:\Users\你的用户名\.ssh\config`，添加：

```ssh-config
Host dgx-spark-gb10
    HostName 106.13.186.155
    Port 6059
    User xsuper
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

保存后，按 `Ctrl+Shift+P` → `Remote-SSH: Connect to Host` → 选择 `dgx-spark-gb10` → 输入密码。

### 端口转发（在 VS Code 中）

连接成功后，点击底部状态栏 **PORTS** 标签 → **Forward a Port**：

```
Port 8000  →  访问 vLLM LLM 服务
Port 8001  →  访问 vLLM VLM 服务  
Port 7860  →  访问 OfficeMind API
Port 8888  →  访问 JupyterLab
```

转发后，直接在 Windows 浏览器访问 `http://localhost:8000` 等。

---

## 方案 C：Open WebUI（图形化大模型对话界面）

Open WebUI 是一个类 ChatGPT 的图形化界面，可以直接对话 DGX Spark 上运行的 Qwen3 模型。

### 在节点上安装 Open WebUI

通过 MobaXterm 或 VS Code 连接节点后，执行：

```bash
# 方式1：Docker（推荐）
docker run -d \
  --network=host \
  --name open-webui \
  -e OPENAI_API_BASE_URL=http://localhost:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main

# 方式2：pip 安装
pip install open-webui
open-webui serve --port 3000
```

### Windows 访问

在 MobaXterm 或 VS Code 中转发端口 `3000`，然后在 Windows 浏览器访问：

```
http://localhost:3000
```

注册账号后，即可在图形界面中与 **Qwen3-80B-Thinking** 对话，效果与 ChatGPT 完全一致。

---

## 方案 D：JupyterLab（浏览器 Notebook 环境）

适合数据分析、模型实验，在浏览器中直接运行 Python 代码。

### 在节点上启动 JupyterLab

```bash
# 安装
/home/xsuper/miniconda3/bin/pip install jupyterlab -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动（无密码，绑定所有接口）
nohup /home/xsuper/miniconda3/bin/jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    > /tmp/jupyter.log 2>&1 &

echo "JupyterLab started! PID: $!"
```

### Windows 访问

转发端口 `8888` 后，浏览器访问 `http://localhost:8888`，即可在 Notebook 中：
- 直接调用 Qwen3-80B API
- 运行 OfficeMind demo 脚本
- 可视化分析结果

---

## 方案 E：RDP 远程桌面（完整 Linux GUI）

如果需要完整的图形化 Linux 桌面（运行 GUI 应用），可以安装 xrdp。

### 在节点上安装 xrdp

```bash
# 安装桌面环境（轻量级 XFCE）
sudo apt-get install -y xfce4 xrdp -q

# 配置 xrdp 使用 XFCE
echo "startxfce4" > ~/.xsession
sudo systemctl enable xrdp
sudo systemctl start xrdp

# 开放 3389 端口（或用端口转发）
echo "xRDP running on port 3389"
```

### Windows 连接

在 MobaXterm 中转发端口 `3389`，然后：
1. 按 `Win+R` → 输入 `mstsc` → 打开远程桌面
2. 地址填 `localhost:3389`
3. 用户名 `xsuper`，密码 `QOW$y5)b`

---

## 一键启动脚本（在节点上运行）

将以下脚本保存为 `~/start_all_services.sh`，一键启动所有服务：

```bash
#!/bin/bash
# OfficeMind — 一键启动所有服务
# 在 DGX Spark GB10 上运行

CONDA="/home/xsuper/miniconda3/bin"
MODELS="/home/xsuper/models"
LOG="/tmp/officemind_logs"
mkdir -p $LOG

echo "=== OfficeMind Services Startup ==="

# 1. LLM (Qwen3-80B)
echo "[1/4] Starting LLM on :8000..."
nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
    --model $MODELS/Qwen3-next-80b-a3b-thinking \
    --served-model-name Qwen3-Thinking \
    --host 0.0.0.0 --port 8000 \
    --trust-remote-code --dtype bfloat16 \
    --max-model-len 16384 --gpu-memory-utilization 0.60 \
    > $LOG/llm.log 2>&1 &
echo "  LLM PID: $!"

# 2. VLM (Qwen2.5-VL-7B)
echo "[2/4] Starting VLM on :8001..."
nohup $CONDA/python -m vllm.entrypoints.openai.api_server \
    --model $MODELS/qwen/Qwen2___5-VL-7B-Instruct \
    --served-model-name Qwen2.5-VL \
    --host 0.0.0.0 --port 8001 \
    --trust-remote-code --dtype bfloat16 \
    --max-model-len 8192 --gpu-memory-utilization 0.18 \
    --limit-mm-per-prompt image=5 \
    > $LOG/vlm.log 2>&1 &
echo "  VLM PID: $!"

# 3. JupyterLab
echo "[3/4] Starting JupyterLab on :8888..."
nohup $CONDA/jupyter lab \
    --ip=0.0.0.0 --port=8888 --no-browser \
    --NotebookApp.token='' --NotebookApp.password='' \
    > $LOG/jupyter.log 2>&1 &
echo "  Jupyter PID: $!"

# 4. OfficeMind API
echo "[4/4] Starting OfficeMind API on :7860..."
cd /home/xsuper/OfficeMind
nohup $CONDA/python -m uvicorn src.api.app:app \
    --host 0.0.0.0 --port 7860 \
    > $LOG/api.log 2>&1 &
echo "  API PID: $!"

echo ""
echo "=== All services started! ==="
echo "Logs: $LOG/"
echo ""
echo "Port forwarding needed (run on Windows via MobaXterm/VSCode):"
echo "  8000 → Qwen3-80B LLM API"
echo "  8001 → Qwen2.5-VL VLM API"
echo "  7860 → OfficeMind API"
echo "  8888 → JupyterLab"
```

---

## 推荐工作流（Windows 11 日常使用）

```
Windows 11
    │
    ├─ MobaXterm ──────────── SSH 终端 + SFTP 文件管理
    │       │
    │       └─ 端口转发 ──── 8000/8001/7860/8888
    │
    ├─ VS Code ────────────── 代码编辑 + 调试
    │       │
    │       └─ Remote-SSH ── 直接在节点上写代码
    │
    └─ Chrome 浏览器
            ├─ localhost:8888  →  JupyterLab（运行实验）
            ├─ localhost:3000  →  Open WebUI（对话大模型）
            └─ localhost:7860  →  OfficeMind API Docs
```
