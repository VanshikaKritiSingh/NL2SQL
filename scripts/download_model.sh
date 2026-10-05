#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — Foundation Model Downloader (Linux & macOS)
#
# Usage:
#   ./scripts/download_model.sh                     # Downloads default 0.5B model
#   ./scripts/download_model.sh --preset 7b         # Downloads flagship Qwen2.5-Coder-7B
#   ./scripts/download_model.sh --preset 1.5b       # Downloads balanced Qwen2.5-Coder-1.5B
#   ./scripts/download_model.sh --preset 7b-gguf    # Downloads GGUF Q4_K_M for CPU
#   ./scripts/download_model.sh --list              # Lists all available model presets
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

# Locate Python in .venv
if [ -f "${REPO_ROOT}/.venv/bin/python" ]; then
    PYTHON_EXEC="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
else
    echo -e "${RED}[Error] Python not found. Please run ./scripts/setup_linux.sh first.${NC}"
    exit 1
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Foundation Base Model Downloader          ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Forward all CLI arguments to download_model.py
"${PYTHON_EXEC}" scripts/download_model.py "$@"
