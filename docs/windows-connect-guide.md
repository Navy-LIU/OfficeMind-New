# Windows 11 图形化连接 DGX Spark GB10 完整指南

> **节点信息（请替换为您的实际参数）**
>
> 请在本地创建 `.env` 文件或设置环境变量：
> ```bash
> DGX_HOST=<your-node-ip>
> DGX_PORT=<your-ssh-port>
> DGX_USER=<your-username>
> ```
> 连接命令：`ssh $DGX_USER@$DGX_HOST -p $DGX_PORT`

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
2. 填写节点信息：

```
Remote host:  <DGX_HOST>
Username:     <DGX_USER>
Port:         <DGX_PORT>
```

3. 点击 **OK**，输入密码，连接成功。

### MobaXterm 核心功能

连接成功后，左侧自动出现 **SFTP 文件管理器**，可直接拖拽上传/下载文件。

**端口转发（访问节点上的 Web 服务）**：

1. 点击 **Tunneling** → **New SSH tunnel**
2. 配置如下（将节点 11434 端口映射到本地）：

```
Tunnel type:    Local port forwarding
Local port:     11434
Remote server:  localhost
Remote port:    11434
SSH server:     <DGX_HOST>
SSH port:       <DGX_PORT>
SSH user:       <DGX_USER>
```

3. 点击 **Start**，然后在 Windows 浏览器访问 `http://localhost:3000` 即可操控大模型。

---

## 方案 B：VS Code Remote-SSH（写代码首选）

### 安装步骤

1. 安装 [VS Code](https://code.visualstudio.com/)
2. 安装扩展：**Remote - SSH**（搜索 `ms-vscode-remote.remote-ssh`）

### 配置 SSH

按 `Ctrl+Shift+P` → 输入 `Remote-SSH: Open SSH Configuration File` → 选择 `C:\Users\你的用户名\.ssh\config`，添加：

```ssh-config
Host dgx-spark-gb10
    HostName <DGX_HOST>
    Port <DGX_PORT>
    User <DGX_USER>
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

保存后，按 `Ctrl+Shift+P` → `Remote-SSH: Connect to Host` → 选择 `dgx-spark-gb10` → 输入密码。

### 端口转发（在 VS Code 中）

连接成功后，点击底部状态栏 **PORTS** 标签 → **Forward a Port**：

```
Port 11434  →  访问 Ollama API（大模型推理）
Port 3000   →  访问 Open WebUI（图形化对话界面）
Port 8888   →  访问 JupyterLab
Port 7860   →  访问 OfficeMind API
```

转发后，直接在 Windows 浏览器访问 `http://localhost:11434` 等。

---

## 方案 C：Open WebUI（图形化大模型对话界面）

Open WebUI 是一个类 ChatGPT 的图形化界面，可以直接对话 DGX Spark 上运行的 Qwen3 模型。

### 在节点上安装 Open WebUI

通过 MobaXterm 或 VS Code 连接节点后，执行：

```bash
# 方式1：pip 安装（推荐）
pip install open-webui
OLLAMA_BASE_URL=http://localhost:11434 open-webui serve --port 3000

# 方式2：Docker
docker run -d \
  --network=host \
  --name open-webui \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
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
pip install jupyterlab -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动（无密码，绑定所有接口）
nohup jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    > /tmp/jupyter.log 2>&1 &

echo "JupyterLab started!"
```

### Windows 访问

转发端口 `8888` 后，浏览器访问 `http://localhost:8888`，即可在 Notebook 中：
- 直接调用 Qwen3-80B API（Ollama）
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

echo "xRDP running on port 3389"
```

### Windows 连接

在 MobaXterm 中转发端口 `3389`，然后：
1. 按 `Win+R` → 输入 `mstsc` → 打开远程桌面
2. 地址填 `localhost:3389`
3. 输入节点用户名和密码

---

## 一键启动脚本（在节点上运行）

将以下脚本保存为 `~/start_all_services.sh`，一键启动所有服务：

```bash
#!/bin/bash
# OfficeMind — 一键启动所有服务
# 在 DGX Spark GB10 上运行

CONDA="$HOME/miniconda3/bin"
MODELS="$HOME/models"
LOG="/tmp/officemind_logs"
mkdir -p $LOG

echo "=== OfficeMind Services Startup ==="

# 1. Ollama (Qwen3-80B)
echo "[1/3] Starting Ollama on :11434..."
OLLAMA_HOST=0.0.0.0:11434 \
OLLAMA_MODELS=$MODELS/ollama \
nohup ollama serve > $LOG/ollama.log 2>&1 &
echo "  Ollama PID: $!"

# 2. JupyterLab
echo "[2/3] Starting JupyterLab on :8888..."
nohup $CONDA/jupyter lab \
    --ip=0.0.0.0 --port=8888 --no-browser \
    --NotebookApp.token='' --NotebookApp.password='' \
    > $LOG/jupyter.log 2>&1 &
echo "  Jupyter PID: $!"

# 3. OfficeMind API
echo "[3/3] Starting OfficeMind API on :7860..."
cd $HOME/OfficeMind
nohup $CONDA/python -m uvicorn src.api.app:app \
    --host 0.0.0.0 --port 7860 \
    > $LOG/api.log 2>&1 &
echo "  API PID: $!"

echo ""
echo "=== All services started! ==="
echo "Port forwarding needed (MobaXterm/VSCode):"
echo "  11434 → Ollama API"
echo "  3000  → Open WebUI"
echo "  7860  → OfficeMind API"
echo "  8888  → JupyterLab"
```

---

## 推荐工作流（Windows 11 日常使用）

```
Windows 11
    │
    ├─ MobaXterm ──────────── SSH 终端 + SFTP 文件管理
    │       │
    │       └─ 端口转发 ──── 11434 / 3000 / 7860 / 8888
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
