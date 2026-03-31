# OfficeMind — Windows 11 一键连接 DGX Spark GB10
# 右键 → 用 PowerShell 运行（或在 PowerShell 中执行）
# 需要 Windows 11 内置 OpenSSH（默认已安装）

$Host.UI.RawUI.WindowTitle = "OfficeMind — DGX Spark GB10"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  OfficeMind — DGX Spark GB10 连接工具" -ForegroundColor Cyan
Write-Host "  NVIDIA GB10 Blackwell / 128GB 统一内存" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$DGX_HOST = "<DGX_HOST>"
$DGX_PORT = "<DGX_PORT>"
$DGX_USER = "<DGX_USER>"

Write-Host "节点信息:" -ForegroundColor Yellow
Write-Host "  地址: ${DGX_HOST}:${DGX_PORT}" -ForegroundColor White
Write-Host "  用户: $DGX_USER" -ForegroundColor White
Write-Host ""

Write-Host "端口转发映射:" -ForegroundColor Yellow
Write-Host "  本地 3000 → 节点 3000  Open WebUI (图形化对话大模型)" -ForegroundColor Green
Write-Host "  本地 8888 → 节点 8888  JupyterLab (Notebook 环境)" -ForegroundColor Green
Write-Host "  本地 8000 → 节点 8000  Qwen3-80B LLM API" -ForegroundColor Green
Write-Host "  本地 8001 → 节点 8001  Qwen2.5-VL VLM API" -ForegroundColor Green
Write-Host "  本地 7860 → 节点 7860  OfficeMind FastAPI" -ForegroundColor Green
Write-Host ""

Write-Host "连接成功后，在浏览器访问:" -ForegroundColor Yellow
Write-Host "  http://localhost:3000   — Open WebUI (推荐，类 ChatGPT 界面)" -ForegroundColor Magenta
Write-Host "  http://localhost:8888   — JupyterLab" -ForegroundColor Magenta
Write-Host "  http://localhost:7860/docs — OfficeMind API 文档" -ForegroundColor Magenta
Write-Host ""

# 检查 SSH 是否可用
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshPath) {
    Write-Host "错误: 未找到 SSH 命令！" -ForegroundColor Red
    Write-Host "请在 Windows 设置 → 可选功能 中安装 OpenSSH 客户端" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "SSH 已就绪: $($sshPath.Source)" -ForegroundColor Green
Write-Host ""
Write-Host "首次连接需输入密码: <YOUR_PASSWORD>" -ForegroundColor Yellow
Write-Host "（建议配置 SSH 密钥免密登录，见下方说明）" -ForegroundColor Gray
Write-Host ""
Write-Host "按 Enter 开始连接，Ctrl+C 断开..." -ForegroundColor Cyan
Read-Host

# 建立 SSH 端口转发（-N 不执行命令，只转发端口）
$sshArgs = @(
    "-N",
    "-L", "3000:localhost:3000",
    "-L", "8888:localhost:8888",
    "-L", "8000:localhost:8000",
    "-L", "8001:localhost:8001",
    "-L", "7860:localhost:7860",
    "-p", $DGX_PORT,
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=60",
    "-o", "ServerAliveCountMax=10",
    "${DGX_USER}@${DGX_HOST}"
)

Write-Host "正在连接..." -ForegroundColor Green
Write-Host "命令: ssh $($sshArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# 打开浏览器（延迟5秒等连接建立）
Start-Job -ScriptBlock {
    Start-Sleep 5
    Start-Process "http://localhost:3000"
} | Out-Null

# 执行 SSH
& ssh @sshArgs

Write-Host ""
Write-Host "连接已断开。" -ForegroundColor Yellow
Read-Host "按 Enter 退出"
