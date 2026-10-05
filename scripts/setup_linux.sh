#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — Linux Setup & Environment Bootstrap Script
#
# Usage:
#   ./scripts/setup_linux.sh               # Core runtime + GUI + local dataset
#   ./scripts/setup_linux.sh --ml          # Core + Heavy AI/ML training suite
#   ./scripts/setup_linux.sh --skip-gui    # Skip Node/NPM GUI setup
#   ./scripts/setup_linux.sh --help        # Show usage help
# =============================================================================

set -e

# Terminal colors
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

INSTALL_ML=false
SKIP_GUI=false
GEN_DATASET=true

for arg in "$@"; do
    case $arg in
        --ml|--train|--gpu)
            INSTALL_ML=true
            shift
            ;;
        --skip-gui|--no-gui)
            SKIP_GUI=true
            shift
            ;;
        --no-data|--skip-data)
            GEN_DATASET=false
            shift
            ;;
        --help|-h)
            echo -e "${BOLD}NL2SQL Pipeline — Linux Setup Script${NC}"
            echo ""
            echo "Options:"
            echo "  --ml         Install heavy AI/ML training dependencies (PyTorch, PEFT, TRL, Transformers)"
            echo "  --skip-gui   Skip Node.js / NPM package installation in GUI directory"
            echo "  --no-data    Skip synthetic fine-tuning dataset generation"
            echo "  --help       Display this help message"
            echo ""
            exit 0
            ;;
        *)
            ;;
    esac
done

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Production Pipeline — Environment Setup   ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "Repository Root: ${REPO_ROOT}"
echo ""

# -----------------------------------------------------------------------------
# 1. Directory Structure Setup (Volume-Safe)
# -----------------------------------------------------------------------------
echo -e "${BOLD}[1/5] Initializing local volume-safe directories...${NC}"
mkdir -p offline/datasets offline/checkpoints offline/models

# -----------------------------------------------------------------------------
# 2. Python Virtual Environment Setup
# -----------------------------------------------------------------------------
echo -e "${BOLD}[2/5] Setting up Python virtual environment (.venv)...${NC}"
if [ ! -d ".venv" ]; then
    if command -v python3 &>/dev/null; then
        python3 -m venv .venv
        echo -e "${GREEN}[OK] Created virtual environment in .venv${NC}"
    else
        echo -e "${RED}[Error] python3 not found. Please install Python 3.10+${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[OK] Existing .venv detected.${NC}"
fi

VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
VENV_PIP="${REPO_ROOT}/.venv/bin/pip"

# Upgrade pip
"${VENV_PIP}" install --upgrade pip setuptools wheel > /dev/null 2>&1

# -----------------------------------------------------------------------------
# 3. Install Core Python Dependencies (Zero Heavy GPU Overhead)
# -----------------------------------------------------------------------------
echo -e "${BOLD}[3/5] Installing core lightweight dependencies (requirements.txt)...${NC}"
"${VENV_PIP}" install -r requirements.txt

if [ "$INSTALL_ML" = true ]; then
    echo -e "${YELLOW}[Notice] Installing isolated AI/ML fine-tuning dependencies (PyTorch, Transformers, PEFT)...${NC}"
    "${VENV_PIP}" install -r offline/training/requirements-train.txt
    echo -e "${GREEN}[OK] ML training stack installed.${NC}"
else
    echo -e "${GREEN}[OK] Core runtime installed (Heavy ML/GPU packages skipped to save disk space).${NC}"
fi

# -----------------------------------------------------------------------------
# 4. Generate Local Fine-Tuning Dataset (Git-Ignored)
# -----------------------------------------------------------------------------
if [ "$GEN_DATASET" = true ]; then
    echo -e "${BOLD}[4/5] Generating local fine-tuning dataset (offline/datasets/)...${NC}"
    "${VENV_PYTHON}" scripts/generate_dataset.py --output-dir offline/datasets --sample-count 250
    echo -e "${GREEN}[OK] Synthetic fine-tuning datasets prepared (0 bytes committed to git).${NC}"
else
    echo -e "${YELLOW}[Skip] Dataset generation skipped.${NC}"
fi

# -----------------------------------------------------------------------------
# 5. Frontend & Desktop GUI Setup
# -----------------------------------------------------------------------------
if [ "$SKIP_GUI" = false ]; then
    echo -e "${BOLD}[5/5] Setting up Desktop & Web Studio GUI (GUI/)...${NC}"
    if command -v npm &>/dev/null; then
        cd GUI
        npm install --silent
        cd "${REPO_ROOT}"
        echo -e "${GREEN}[OK] GUI npm dependencies installed.${NC}"
    else
        echo -e "${YELLOW}[Warning] npm not found in PATH. Skipping GUI npm install.${NC}"
        echo -e "${YELLOW}Install Node.js 18+ to launch the Desktop & Web Studio UI.${NC}"
    fi
else
    echo -e "${YELLOW}[Skip] GUI installation skipped.${NC}"
fi

# -----------------------------------------------------------------------------
# Run Verification Tests
# -----------------------------------------------------------------------------
echo ""
echo -e "${BOLD}Running core verification test suite...${NC}"
PYTHONPATH=. "${VENV_PYTHON}" -m pytest tests/ -v

echo ""
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}   NL2SQL Environment Setup Completed Successfully!  ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo ""
echo -e "Quick Start Commands:"
echo -e "  - Run Tests     : PYTHONPATH=. ./.venv/bin/pytest tests/ -v"
echo -e "  - Launch GUI    : cd GUI && npm run desktop:dev  (or npm run dev)"
echo -e "  - Fine-Tune     : ./.venv/bin/python offline/training/train_qlora.py"
echo -e "  - Generate Data : ./.venv/bin/python scripts/generate_dataset.py"
echo ""
