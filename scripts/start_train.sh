#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — QLoRA Fine-Tuning Launcher (Linux & macOS)
#
# Usage:
#   ./scripts/start_train.sh                       # Fine-tunes default model (0.5B or local)
#   ./scripts/start_train.sh --model Qwen/Qwen2.5-Coder-7B-Instruct
#   ./scripts/start_train.sh --epochs 5 --batch-size 4
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

# Ensure dataset exists before training
if [ ! -f "offline/datasets/train.json" ]; then
    echo -e "${YELLOW}[Notice] Synthetic dataset not found. Generating now...${NC}"
    "${PYTHON_EXEC}" scripts/generate_dataset.py --output-dir offline/datasets --sample-count 250
fi

# If a local downloaded model exists in offline/models/, prefer it by default
DEFAULT_MODEL="offline/models/qwen2.5-coder-0.5b-instruct"
if [ ! -d "$DEFAULT_MODEL" ]; then
    DEFAULT_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct"
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Offline Fine-Tuning Suite (QLoRA)        ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Check for --model in arguments, else inject default
HAS_MODEL=false
for arg in "$@"; do
    if [[ "$arg" == "--model"* ]]; then
        HAS_MODEL=true
        break
    fi
done

if [ "$HAS_MODEL" = true ]; then
    "${PYTHON_EXEC}" offline/training/train_qlora.py "$@"
else
    "${PYTHON_EXEC}" offline/training/train_qlora.py --model "${DEFAULT_MODEL}" "$@"
fi
