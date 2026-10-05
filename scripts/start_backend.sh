#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — FastAPI Backend Server Launcher (Linux & macOS)
#
# Usage:
#   ./scripts/start_backend.sh                     # Runs backend on 127.0.0.1:8000 (reload enabled)
#   ./scripts/start_backend.sh --port 8080         # Runs on custom port
#   ./scripts/start_backend.sh --host 0.0.0.0      # Binds to all network interfaces
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

HOST="127.0.0.1"
PORT="8000"
RELOAD="--reload"

while [[ $# -gt 0 ]]; do
    case $1 in
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --host|-h)
            HOST="$2"
            shift 2
            ;;
        --no-reload)
            RELOAD=""
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ -f "${REPO_ROOT}/.venv/bin/python" ]; then
    PYTHON_EXEC="${REPO_ROOT}/.venv/bin/python"
    UVICORN_EXEC="${REPO_ROOT}/.venv/bin/uvicorn"
elif command -v uvicorn &>/dev/null; then
    PYTHON_EXEC="python3"
    UVICORN_EXEC="uvicorn"
else
    echo -e "${RED}[Error] Python/.venv not found. Run ./scripts/setup_linux.sh first.${NC}"
    exit 1
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}       NL2SQL Pipeline — Starting FastAPI Backend     ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "Server URL  : ${GREEN}http://${HOST}:${PORT}${NC}"
echo -e "API Docs    : ${GREEN}http://${HOST}:${PORT}/docs${NC}"
echo -e "Repo Root   : ${REPO_ROOT}"
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop the server.\n"

export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/GUI/server:${PYTHONPATH}"

exec "${PYTHON_EXEC}" -m uvicorn GUI.server.main:app --host "${HOST}" --port "${PORT}" ${RELOAD}
