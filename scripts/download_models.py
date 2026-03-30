"""
通过 ModelScope 下载 BGE 模型到本地
BGE-M3: 稠密向量 Embedding（~2GB）
BGE-Reranker-v2-m3: 重排序模型（~1GB）
用法: python scripts/download_models.py
"""
from modelscope import snapshot_download

MODELS_DIR = "/home/xsuper/models"

MODELS = {
    "bge-m3":               "AI-ModelScope/bge-m3",
    "bge-reranker-v2-m3":   "AI-ModelScope/bge-reranker-v2-m3",
}

for name, model_id in MODELS.items():
    save_path = f"{MODELS_DIR}/bge/{name}"
    print(f"[download] {model_id} → {save_path}")
    snapshot_download(model_id, cache_dir=save_path)
    print(f"[done]     {name}")

print("\n所有 BGE 模型下载完成")
