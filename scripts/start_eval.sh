#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — AST & Execution Accuracy Benchmark Evaluator (Linux & macOS)
#
# Usage:
#   ./scripts/start_eval.sh                        # Evaluates offline/datasets/eval.json
#   ./scripts/start_eval.sh --eval-file path/to/eval.json
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

# Ensure eval dataset exists
if [ ! -f "offline/datasets/eval.json" ]; then
    echo -e "${YELLOW}[Notice] Eval dataset not found. Generating now...${NC}"
    "${PYTHON_EXEC}" scripts/generate_dataset.py --output-dir offline/datasets --sample-count 250
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Benchmark Evaluator (AST EM & SQLite EX)  ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}"
"${PYTHON_EXEC}" offline/training/evaluate.py "$@"
