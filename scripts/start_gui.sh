#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — Desktop & Web Studio GUI Launcher (Linux & macOS)
#
# Usage:
#   ./scripts/start_gui.sh                         # Starts Web Studio (Vite dev server)
#   ./scripts/start_gui.sh --desktop               # Starts Electron Desktop App
#   ./scripts/start_gui.sh --host                  # Exposes Vite to local network
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
GUI_DIR="${REPO_ROOT}/GUI"

DESKTOP_MODE=false
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --desktop|-d)
            DESKTOP_MODE=true
            shift
            ;;
        --host)
            EXTRA_ARGS+=(--host)
            shift
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if ! command -v npm &>/dev/null; then
    echo -e "${RED}[Error] Node.js and npm are required to launch the GUI.${NC}"
    echo -e "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

cd "${GUI_DIR}"

# Ensure node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[Notice] Installing GUI dependencies first...${NC}"
    npm install --cache .npm-cache
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
if [ "$DESKTOP_MODE" = true ]; then
    echo -e "${CYAN}${BOLD}     NL2SQL Pipeline — Launching Electron Desktop GUI ${NC}"
    echo -e "${CYAN}${BOLD}======================================================${NC}"
    exec npm run desktop:dev
else
    echo -e "${CYAN}${BOLD}     NL2SQL Pipeline — Launching Web Studio UI        ${NC}"
    echo -e "${CYAN}${BOLD}======================================================${NC}"
    echo -e "UI Web URL  : ${GREEN}http://localhost:5173${NC}"
    echo -e "Press ${YELLOW}Ctrl+C${NC} to stop the frontend server.\n"
    exec npm run dev -- "${EXTRA_ARGS[@]}"
fi
