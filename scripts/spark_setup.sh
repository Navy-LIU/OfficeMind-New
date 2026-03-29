#!/bin/bash
# ============================================================
# OfficeMind — DGX Spark Setup Script
# Installs: Node.js 22 → OpenShell → NemoClaw → setup-spark
# Then starts OfficeMind sandbox
# ============================================================

set -e
SUDO_PASS="QOW\$y5)b"
export DEBIAN_FRONTEND=noninteractive

echo "============================================"
echo "  OfficeMind — DGX Spark Setup"
echo "  Hardware: NVIDIA GB10 (128GB unified mem)"
echo "============================================"

# ── Step 1: Fix Docker cgroup v2 ──────────────────────────────────────────────
echo "[1/6] Fix Docker cgroup v2..."
echo "$SUDO_PASS" | sudo -S python3 -c "
import json, os
path = '/etc/docker/daemon.json'
d = json.load(open(path)) if os.path.exists(path) else {}
d['default-cgroupns-mode'] = 'host'
json.dump(d, open(path, 'w'), indent=2)
print('  daemon.json updated:', d)
"
echo "$SUDO_PASS" | sudo -S systemctl restart docker
sleep 3
echo "  Docker restarted ✓"

# ── Step 2: Add user to docker group ─────────────────────────────────────────
echo "[2/6] Fix Docker permissions..."
echo "$SUDO_PASS" | sudo -S usermod -aG docker "$USER" 2>/dev/null || true
echo "  Added $USER to docker group ✓"

# ── Step 3: Install Node.js 22 ───────────────────────────────────────────────
echo "[3/6] Install Node.js 22..."
NODE_VER=$(node --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
if [ "$NODE_VER" -lt 20 ]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | echo "$SUDO_PASS" | sudo -S -E bash - 2>&1 | tail -3
    echo "$SUDO_PASS" | sudo -S apt-get install -y nodejs 2>&1 | tail -3
    echo "  Node.js $(node --version) installed ✓"
else
    echo "  Node.js $(node --version) already OK ✓"
fi

# ── Step 4: Install OpenShell ────────────────────────────────────────────────
echo "[4/6] Install OpenShell CLI..."
if ! which openshell &>/dev/null; then
    ARCH=$(uname -m)
    curl -fsSL "https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh" | sh
    echo "  OpenShell installed ✓"
else
    echo "  OpenShell already installed ✓"
fi

# ── Step 5: Install NemoClaw ─────────────────────────────────────────────────
echo "[5/6] Install NemoClaw..."
export PATH="$HOME/.local/bin:$(npm config get prefix 2>/dev/null)/bin:$PATH"
if ! which nemoclaw &>/dev/null; then
    curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
    source ~/.bashrc 2>/dev/null || true
    echo "  NemoClaw installed ✓"
else
    echo "  NemoClaw $(nemoclaw --version 2>/dev/null) already installed ✓"
fi

# ── Step 6: setup-spark ──────────────────────────────────────────────────────
echo "[6/6] Run nemoclaw setup-spark..."
export PATH="$HOME/.local/bin:$(npm config get prefix 2>/dev/null)/bin:$PATH"
nemoclaw setup-spark 2>&1
echo "  setup-spark complete ✓"

echo ""
echo "============================================"
echo "  Setup Complete! Next steps:"
echo ""
echo "  1. Start Qwen3 inference server:"
echo "     bash scripts/serve_qwen3.sh"
echo ""
echo "  2. Onboard NemoClaw (need NVIDIA API key):"
echo "     nemoclaw onboard"
echo "     → Select: Local Ollama / vLLM"
echo "     → Model: Qwen3-Thinking"
echo ""
echo "  3. Start OfficeMind sandbox:"
echo "     nemoclaw officemind connect"
echo ""
echo "  4. Test the agent:"
echo "     openclaw agent --agent main --local \\"
echo "       -m '帮我生成今日工作日报' --session-id test1"
echo "============================================"
