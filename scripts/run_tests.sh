#!/usr/bin/env bash
# =============================================================================
# NL2SQL Pipeline — Comprehensive Verification & Integration Test Suite (Linux & macOS)
#
# Usage:
#   ./scripts/run_tests.sh                         # Runs all unit & backend integration tests
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
    PYTEST_EXEC="${REPO_ROOT}/.venv/bin/pytest"
else
    PYTHON_EXEC="python3"
    PYTEST_EXEC="pytest"
fi

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}     NL2SQL Pipeline — Integration & Verification     ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Step 1: Core Unit Tests
echo -e "\n${BOLD}[1/2] Running Core & Transpiler Unit Tests (pytest)...${NC}"
PYTHONPATH="${REPO_ROOT}" "${PYTEST_EXEC}" tests/ -v

# Step 2: Backend API & Orchestrator Integration Tests
echo -e "\n${BOLD}[2/2] Running Backend API Integration Tests...${NC}"
PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/GUI/server" "${PYTHON_EXEC}" GUI/server/test_backend.py

echo -e "\n${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}   ALL INTEGRATION & VERIFICATION TESTS PASSED 100%!  ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
