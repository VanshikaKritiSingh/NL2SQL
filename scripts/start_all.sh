#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — Unified Full-Stack Launcher (Linux & macOS)
#
# Starts both the FastAPI Backend Server and Web Studio GUI concurrently.
# Provides automatic graceful shutdown on Ctrl+C (SIGINT / SIGTERM).
#
# Usage:
#   ./scripts/start_all.sh                         # Start Backend + Web UI
#   ./scripts/start_all.sh --desktop               # Start Backend + Electron Desktop
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

DESKTOP_MODE=false
for arg in "$@"; do
    case $arg in
        --desktop|-d)
            DESKTOP_MODE=true
            ;;
    esac
done

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}       NL2SQL Full-Stack Pipeline — Starting Services ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Cleanup handler for background processes
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}[Shutting down] Stopping all NL2SQL pipeline services...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}[OK] All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start FastAPI Backend in background
echo -e "${BOLD}[1/2] Launching FastAPI Backend Server on http://127.0.0.1:8000...${NC}"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/GUI/server:${PYTHONPATH}"
if [ -f "${REPO_ROOT}/.venv/bin/python" ]; then
    "${REPO_ROOT}/.venv/bin/python" -m uvicorn GUI.server.main:app --host 127.0.0.1 --port 8000 --reload &
    BACKEND_PID=$!
else
    python3 -m uvicorn GUI.server.main:app --host 127.0.0.1 --port 8000 --reload &
    BACKEND_PID=$!
fi

# Wait briefly for backend to initialize
sleep 1.5

# 2. Start Frontend UI
echo -e "${BOLD}[2/2] Launching Studio GUI...${NC}"
cd "${REPO_ROOT}/GUI"

if [ ! -d "node_modules" ]; then
    npm install --cache .npm-cache
fi

if [ "$DESKTOP_MODE" = true ]; then
    echo -e "${GREEN}[OK] Starting Electron Desktop UI...${NC}"
    npm run desktop:dev &
    FRONTEND_PID=$!
else
    echo -e "${GREEN}[OK] Starting Web UI on http://localhost:5173...${NC}"
    npm run dev &
    FRONTEND_PID=$!
fi

echo ""
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}  NL2SQL Full-Stack Environment is Active & Ready!    ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "  - Backend API : ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  - API Swagger : ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo -e "  - Web Studio  : ${CYAN}http://localhost:5173${NC}"
echo -e "  - Press ${YELLOW}Ctrl+C${NC} anytime to terminate all services."
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
