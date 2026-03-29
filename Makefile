# OfficeMind Makefile
# Usage: make <target>
# Platform: NVIDIA DGX Spark GB10 (128GB unified memory, Blackwell)

CONDA = /home/xsuper/miniconda3/bin
PYTHON = $(CONDA)/python
PIP = $(CONDA)/pip

.PHONY: help setup install models serve-llm serve-vlm serve-embed serve-all start demo test qa status clean

help:
	@echo "OfficeMind — NVIDIA DGX Spark GB10"
	@echo ""
	@echo "  make setup       — Full DGX Spark setup (NemoClaw + dependencies)"
	@echo "  make install     — Install Python dependencies"
	@echo "  make models      — Download models via modelscope"
	@echo "  make serve-llm   — Start Qwen3-80B vLLM (port 8000)"
	@echo "  make serve-vlm   — Start Qwen2.5-VL-7B vLLM (port 8001)"
	@echo "  make serve-embed — Start Qwen3-Embedding vLLM (port 8002)"
	@echo "  make serve-all   — Start all model servers"
	@echo "  make start       — Start OfficeMind FastAPI app (port 7860)"
	@echo "  make demo        — Run demo scenarios"
	@echo "  make status      — Check service health"
	@echo "  make test        — Run unit tests"
	@echo "  make qa          — Run NemoClaw agent Q&A test suite"
	@echo "  make clean       — Clean logs and output"

setup:
	@echo "Setting up DGX Spark environment..."
	bash scripts/spark_setup.sh

install:
	$(PIP) install -r requirements.txt \
		-i https://pypi.tuna.tsinghua.edu.cn/simple
	$(PYTHON) -m playwright install chromium

models:
	$(PYTHON) -c "from modelscope import snapshot_download; \
		snapshot_download('qwen/Qwen2.5-VL-7B-Instruct', cache_dir='/home/xsuper/models')"
	$(PYTHON) -c "from modelscope import snapshot_download; \
		snapshot_download('Qwen/Qwen3-Embedding', cache_dir='/home/xsuper/models')"

serve-llm:
	@echo "Starting Qwen3-80B-A3B-Thinking on port 8000..."
	bash scripts/serve_models.sh llm

serve-vlm:
	@echo "Starting Qwen2.5-VL-7B on port 8001..."
	bash scripts/serve_models.sh vlm

serve-embed:
	@echo "Starting Qwen3-Embedding on port 8002..."
	bash scripts/serve_models.sh embed

serve-all:
	bash scripts/serve_models.sh all

start:
	@echo "Starting OfficeMind API on port 7860..."
	$(PYTHON) -m uvicorn src.api.app:app \
		--host 0.0.0.0 --port 7860 --log-level info

demo:
	$(PYTHON) demo.py all

status:
	@echo "=== vLLM Services ==="
	@curl -s http://localhost:8000/health > /dev/null && echo "LLM :8000 ONLINE" || echo "LLM :8000 offline"
	@curl -s http://localhost:8001/health > /dev/null && echo "VLM :8001 ONLINE" || echo "VLM :8001 offline"
	@curl -s http://localhost:8002/health > /dev/null && echo "Embed:8002 ONLINE" || echo "Embed:8002 offline"
	@echo ""
	@echo "=== GPU ==="
	@nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "N/A"

test:
	$(PYTHON) -m pytest tests/ -v --asyncio-mode=auto

qa:
	@echo "Running NemoClaw agent Q&A tests..."
	bash scripts/test_agent_qa.sh

clean:
	rm -rf logs/ output/ src/__pycache__/ src/**/__pycache__/
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache dist build *.egg-info
