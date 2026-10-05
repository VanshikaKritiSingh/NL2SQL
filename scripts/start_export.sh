#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — LoRA Merge & GGUF / Ollama Exporter (Linux & macOS)
#
# Usage:
#   ./scripts/start_export.sh                      # Merges default LoRA checkpoint
#   ./scripts/start_export.sh --base Qwen/Qwen2.5-Coder-7B-Instruct --lora offline/checkpoints/my_lora
# =============================================================================

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [ -f "${REPO_ROOT}/.venv/bin/python" ]; then
    PYTHON_EXEC="${REPO_ROOT}/.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Model Exporter: LoRA Merge & GGUF Modelfile${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

"${PYTHON_EXEC}" offline/training/export_gguf.py "$@"
