@echo off
:: OfficeMind — Windows 一键连接 DGX Spark GB10
:: 双击运行此脚本，自动建立所有端口转发
:: 需要已安装 OpenSSH（Windows 11 默认已内置）

title OfficeMind — DGX Spark GB10 连接

echo ================================================
echo   OfficeMind — DGX Spark GB10 连接工具
echo   NVIDIA GB10 Blackwell / 128GB 统一内存
echo ================================================
echo.
echo 正在建立 SSH 端口转发...
echo 节点: 106.13.186.155:6059
echo.
echo 转发端口映射:
echo   本地 8000 → 节点 8000  (Qwen3-80B LLM API)
echo   本地 8001 → 节点 8001  (Qwen2.5-VL VLM API)
echo   本地 8888 → 节点 8888  (JupyterLab)
echo   本地 3000 → 节点 3000  (Open WebUI 对话界面)
echo   本地 7860 → 节点 7860  (OfficeMind API)
echo.
echo 连接成功后，请在浏览器访问:
echo   http://localhost:3000   — Open WebUI (对话大模型)
echo   http://localhost:8888   — JupyterLab
echo   http://localhost:7860   — OfficeMind API
echo.
echo 按任意键开始连接... (首次需输入密码: QOW$y5)b)
pause > nul

:: 使用 Windows 内置 SSH 建立多端口转发
ssh -N ^
    -L 8000:localhost:8000 ^
    -L 8001:localhost:8001 ^
    -L 8888:localhost:8888 ^
    -L 3000:localhost:3000 ^
    -L 7860:localhost:7860 ^
    -p 6059 ^
    -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=60 ^
    -o ServerAliveCountMax=10 ^
    xsuper@106.13.186.155

echo.
echo 连接已断开。按任意键退出...
pause > nul
