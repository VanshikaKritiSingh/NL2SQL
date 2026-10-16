#!/usr/bin/env bash
# =============================================================================
# NL2SQL — Training Environment Setup Script
# =============================================================================
#
# WHAT THIS SCRIPT DOES (read before running):
#
#   1.  Creates a Python 3.12 venv at .venv312 (PyTorch CUDA 12.4 wheels need
#       Python <=3.12; our system Python 3.14 has no pre-built CUDA wheels).
#
#   2.  Installs PyTorch 2.6 + torchvision compiled for CUDA 12.4 (cu124) from
#       the official PyTorch index. This is the GPU compute backend.
#       Size: ~3.5 GB download.  Run this on a good connection.
#
#   3.  Installs the PEFT training stack:
#         • transformers  — HF model/tokenizer loader
#         • peft          — QLoRA (LoraConfig) + AdaLoRA (AdaLoraConfig) adapters
#         • trl           — SFTTrainer with completion-only masking
#         • bitsandbytes  — 4-bit NF4 & 8-bit quantization kernels for VRAM savings
#         • accelerate    — automatic device placement & mixed precision
#         • datasets      — fast JSONL loader and data collators
#
#   4.  Installs the project's own runtime deps (sqlglot, fastapi, etc.) from
#       the existing requirements.txt into the same venv.
#
#   5.  Self-tests: imports torch + checks CUDA device name, then peft.
#
# GOAL:
#   After this script completes, you can run the fine-tuning engine:
#
#     # Dry-run: 10 steps on the local 0.5B model — verifies everything works
#     .venv312/bin/python offline/training/train_engine.py \
#         --peft qlora \
#         --model offline/models/qwen2.5-coder-0.5b-instruct \
#         --max-steps 10 \
#         --max-samples 128 \
#         --output-dir offline/checkpoints/smoke-test-qlora
#
#     # Full AdaLoRA run on 0.5B (baseline benchmark comparison):
#     .venv312/bin/python offline/training/train_engine.py \
#         --peft adalora \
#         --model offline/models/qwen2.5-coder-0.5b-instruct \
#         --epochs 3 \
#         --output-dir offline/checkpoints/nl2sql-adalora-0.5b
#
#     # Evaluate the trained adapter against the benchmark harness:
#     .venv312/bin/python offline/training/evaluate.py \
#         --base-model offline/models/qwen2.5-coder-0.5b-instruct \
#         --adapter    offline/checkpoints/nl2sql-adalora-0.5b \
#         --max-samples 200 \
#         --report     offline/checkpoints/nl2sql-adalora-0.5b/eval_report.json
#
# HARDWARE REQUIREMENTS:
#   • Minimum:  RTX 4060 8GB (your GPU)    — works for all runs below
#   • Optimal:  RTX 3090 / RTX 4090 24GB  — full 7B runs without batching tricks
#
# WHEN YOU'RE READY TO TRAIN THE 7B MODEL FOR SHIPPING:
#   Replace --model with  Qwen/Qwen2.5-Coder-7B-Instruct
#   The script will download ~15GB from Hugging Face automatically.
#
# =============================================================================

set -e  # Exit on any error
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()    { echo -e "${CYAN}[setup]${NC} $1"; }
ok()     { echo -e "${GREEN}[ok]${NC} $1"; }
warn()   { echo -e "${YELLOW}[warn]${NC} $1"; }
error()  { echo -e "${RED}[error]${NC} $1"; exit 1; }
banner() { echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${CYAN} $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════${NC}"; }

# ── 0. Prerequisites Check ──────────────────────────────────────────────────
banner "Step 0: Prerequisites"

command -v python3.12 >/dev/null 2>&1 || error "python3.12 is not on PATH. Install it and retry."
PY312_VERSION=$(python3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Found Python $PY312_VERSION at $(which python3.12)"

# Confirm NVIDIA driver is visible from the user's session
if nvidia-smi &>/dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)
    ok "GPU detected: $GPU_NAME"
else
    warn "nvidia-smi is not accessible from this shell. CUDA-based training will fall back to CPU."
    warn "If you ran nvidia-smi in Kitty and it shows your RTX 4060, this is a sandbox isolation issue."
    warn "Run this script from your real terminal, not from the AI assistant's shell."
fi

# ── 1. Create Python 3.12 venv ──────────────────────────────────────────────
banner "Step 1: Python 3.12 venv"

if [ -d ".venv312" ]; then
    warn ".venv312 already exists — skipping creation."
else
    log "Creating venv at .venv312 ..."
    python3.12 -m venv .venv312
    ok "Created .venv312"
fi

VENV_PY=".venv312/bin/python"
VENV_PIP=".venv312/bin/pip"

log "Upgrading pip inside venv..."
"$VENV_PIP" install --upgrade pip --quiet

# ── 2. PyTorch + CUDA 12.4 ──────────────────────────────────────────────────
banner "Step 2: PyTorch 2.6 + CUDA 12.4 (~3.5 GB)"

if "$VENV_PY" -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    ok "PyTorch with CUDA already installed — skipping."
else
    log "Installing PyTorch 2.6 + torchvision from PyTorch CUDA 12.4 index..."
    log "(This is a ~3.5 GB download — get a coffee ☕)"
    "$VENV_PIP" install \
        torch==2.6.0+cu124 \
        torchvision==0.21.0+cu124 \
        --index-url https://download.pytorch.org/whl/cu124 \
        --no-cache-dir

    # Verify CUDA
    if "$VENV_PY" -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'"; then
        GPU_INFO=$("$VENV_PY" -c "import torch; print(torch.cuda.get_device_name(0))")
        ok "PyTorch CUDA working: $GPU_INFO"
    else
        warn "PyTorch installed but CUDA is not available."
        warn "If nvidia-smi works in your terminal, reboot and run this script again."
    fi
fi

# ── 3. PEFT Training Stack ───────────────────────────────────────────────────
banner "Step 3: PEFT Training Stack"
log "Installing transformers, peft, trl, bitsandbytes, accelerate, datasets..."
"$VENV_PIP" install \
    "transformers>=4.44.0" \
    "peft>=0.12.0" \
    "trl>=0.9.0" \
    "bitsandbytes>=0.43.0" \
    "accelerate>=0.30.0" \
    "datasets>=2.20.0" \
    "safetensors>=0.4.2" \
    "sentencepiece>=0.2.0" \
    --quiet

ok "PEFT training stack installed."

# ── 4. Project Runtime Deps ──────────────────────────────────────────────────
banner "Step 4: Project Runtime Dependencies"

if [ -f "requirements.txt" ]; then
    log "Installing from requirements.txt..."
    "$VENV_PIP" install -r requirements.txt --quiet
    ok "Project dependencies installed."
else
    warn "No requirements.txt found at project root — skipping."
fi

# Also install sqlglot standalone (needed for evaluate.py even without training)
"$VENV_PIP" install sqlglot --quiet

# ── 5. Self-Tests ────────────────────────────────────────────────────────────
banner "Step 5: Self-Tests"

log "Testing torch..."
"$VENV_PY" -c "
import torch
print(f'  torch version  : {torch.__version__}')
print(f'  CUDA available : {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU name       : {torch.cuda.get_device_name(0)}')
    print(f'  VRAM total     : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
"

log "Testing peft..."
"$VENV_PY" -c "
from peft import LoraConfig, AdaLoraConfig
print('  LoraConfig    : ok')
print('  AdaLoraConfig : ok')
"

log "Testing trl..."
"$VENV_PY" -c "
from trl import SFTTrainer
print('  SFTTrainer    : ok')
"

log "Testing evaluate.py sanity (gold-label dry run)..."
"$VENV_PY" offline/training/evaluate.py --max-samples 20

# ── 6. Quick Commands Reference ──────────────────────────────────────────────
banner "Setup Complete ✅"

echo -e "
${GREEN}You can now run fine-tuning with:${NC}

  # ── Smoke test (10 gradient steps on 0.5B — checks everything is wired up):
  .venv312/bin/python offline/training/train_engine.py \\
      --peft qlora \\
      --model offline/models/qwen2.5-coder-0.5b-instruct \\
      --max-steps 10 \\
      --max-samples 128 \\
      --output-dir offline/checkpoints/smoke-test-qlora

  # ── QLoRA: 3-epoch full run on 0.5B baseline:
  .venv312/bin/python offline/training/train_engine.py \\
      --peft qlora \\
      --model offline/models/qwen2.5-coder-0.5b-instruct \\
      --epochs 3 \\
      --output-dir offline/checkpoints/nl2sql-qlora-0.5b

  # ── AdaLoRA: 3-epoch full run on 0.5B (compare against QLoRA above):
  .venv312/bin/python offline/training/train_engine.py \\
      --peft adalora \\
      --model offline/models/qwen2.5-coder-0.5b-instruct \\
      --epochs 3 \\
      --output-dir offline/checkpoints/nl2sql-adalora-0.5b

  # ── Evaluate either checkpoint:
  .venv312/bin/python offline/training/evaluate.py \\
      --base-model offline/models/qwen2.5-coder-0.5b-instruct \\
      --adapter    offline/checkpoints/nl2sql-adalora-0.5b \\
      --max-samples 200 \\
      --report     offline/checkpoints/nl2sql-adalora-0.5b/eval_report.json

  # ── When you want to train the full 7B production model:
  .venv312/bin/python offline/training/train_engine.py \\
      --peft qlora \\
      --model Qwen/Qwen2.5-Coder-7B-Instruct \\
      --epochs 3 \\
      --output-dir offline/checkpoints/nl2sql-qlora-7b
"
