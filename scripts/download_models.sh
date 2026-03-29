#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# OfficeMind — Model Download Script for DGX Spark Node
# Node: spark-59  |  106.13.186.155:6059
# Cache Dir: /home/xsuper/models
#
# Usage:
#   bash scripts/download_models.sh [--all | --vlm | --embed | --rerank]
#
# NOTE: Use modelscope for fast CN mirror download. DO NOT use scp.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

CACHE_DIR="/home/xsuper/models"
LOG_FILE="${CACHE_DIR}/download.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] $*${NC}" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN] $*${NC}" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[ERR]  $*${NC}" | tee -a "$LOG_FILE"; exit 1; }

mkdir -p "$CACHE_DIR"

# ─── Check dependencies ───────────────────────────────────────────────────────
check_deps() {
    python3 -c "import modelscope" 2>/dev/null || {
        log "Installing modelscope..."
        pip install modelscope -q
    }
    log "Dependencies OK"
}

# ─── Download: Qwen-VL-Chat (Vision-Language Model) ──────────────────────────
download_vlm() {
    log "Downloading Qwen-VL-Chat → ${CACHE_DIR}/qwen/Qwen-VL-Chat"
    python3 - <<'EOF'
from modelscope import snapshot_download
snapshot_download(
    'qwen/Qwen-VL-Chat',
    cache_dir='/home/xsuper/models',
    ignore_patterns=['*.bin.index.json']
)
print("✓ Qwen-VL-Chat downloaded")
EOF
}

# ─── Download: BGE-M3 Embedding ───────────────────────────────────────────────
download_embed() {
    log "Downloading BGE-M3 Embedding → ${CACHE_DIR}/BAAI/bge-m3"
    python3 - <<'EOF'
from modelscope import snapshot_download
snapshot_download(
    'BAAI/bge-m3',
    cache_dir='/home/xsuper/models'
)
print("✓ BGE-M3 downloaded")
EOF
}

# ─── Download: BGE-Reranker-v2-m3 ────────────────────────────────────────────
download_rerank() {
    log "Downloading BGE-Reranker-v2-m3 → ${CACHE_DIR}/BAAI/bge-reranker-v2-m3"
    python3 - <<'EOF'
from modelscope import snapshot_download
snapshot_download(
    'BAAI/bge-reranker-v2-m3',
    cache_dir='/home/xsuper/models'
)
print("✓ BGE-Reranker-v2-m3 downloaded")
EOF
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
    check_deps
    MODE="${1:---all}"
    case "$MODE" in
        --all)
            download_vlm
            download_embed
            download_rerank
            ;;
        --vlm)    download_vlm ;;
        --embed)  download_embed ;;
        --rerank) download_rerank ;;
        *) err "Unknown option: $MODE. Use --all | --vlm | --embed | --rerank" ;;
    esac
    log "All models ready in ${CACHE_DIR}"
    du -sh "${CACHE_DIR}"/*/ 2>/dev/null || true
}

main "$@"
