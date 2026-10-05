<div align="center">

# Environment Bootstrap & Setup Scripts

### Cross-Platform Environment Setup & Volume Protection Automation

[![Script Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=flat-square)](https://github.com/VanshikaKritiSingh/NL2SQL)
[![Platforms](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square)](https://github.com/VanshikaKritiSingh/NL2SQL)
[![Shell](https://img.shields.io/badge/Shell-Bash%20%7C%20PowerShell%20%7C%20Batch-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/VanshikaKritiSingh/NL2SQL)
[![Volume Protection](https://img.shields.io/badge/Repo%20Volume-Protected%20%28%3C%2015MB%29-blue?style=flat-square)](https://github.com/VanshikaKritiSingh/NL2SQL)

</div>

<br />

---

## Setup Workflow & Volume Protection

The setup automation is structured to keep the Git repository lightweight (< 15MB) by dynamically creating virtual environments, generating fine-tuning data on demand, and cleanly ignoring heavy artifacts via `.gitignore`:

```mermaid
flowchart TD
    START([Lightweight Git Clone]) --> TARGET{Operating System}
    TARGET -->|Linux / macOS| BASH[scripts/setup_linux.sh]
    TARGET -->|Windows PowerShell| PS[scripts/setup_windows.ps1]
    TARGET -->|Windows Command Prompt| BAT[scripts/setup_windows.bat]

    BASH --> STEP1
    PS --> STEP1
    BAT --> STEP1

    subgraph Bootstrap_Sequence [One-Command Environment Setup]
        STEP1[1. Initialize .venv Python Environment]
        STEP2[2. Install Lightweight Core Packages<br/>requirements.txt]
        STEP3[3. Install GUI Packages<br/>cd GUI && npm install]
        STEP4[4. Synthesize Local Fine-Tuning Dataset<br/>offline/datasets/*.json]
        STEP5[5. Run 13/13 Test Suite Verification]
        
        STEP1 --> STEP2 --> STEP3 --> STEP4 --> STEP5
    end

    STEP5 --> READY([Ready for Core & GUI Development])
```

---

## Script Options & Commands

### 1. Linux & macOS (`scripts/setup_linux.sh`)

```bash
# Make script executable
chmod +x scripts/setup_linux.sh

# Standard Setup: Core Python runtime + GUI npm packages + Local fine-tuning dataset
./scripts/setup_linux.sh

# Full AI/ML Setup: Installs heavy PyTorch, Transformers, PEFT, and TRL
./scripts/setup_linux.sh --ml

# Headless Setup: Skip Node/NPM GUI setup (CI/CD or backend development)
./scripts/setup_linux.sh --skip-gui

# Skip Dataset Generation: Use existing dataset
./scripts/setup_linux.sh --no-data
```

### 2. Windows PowerShell (`scripts/setup_windows.ps1`)

```powershell
# Standard Setup: Core Python runtime + GUI npm packages + Local fine-tuning dataset
.\scripts\setup_windows.ps1

# Full AI/ML Setup: Installs heavy PyTorch, Transformers, PEFT, and TRL
.\scripts\setup_windows.ps1 -InstallML

# Headless Setup: Skip GUI npm install
.\scripts\setup_windows.ps1 -SkipGUI

# Skip Dataset Generation
.\scripts\setup_windows.ps1 -SkipData
```

### 3. Windows Batch Launcher (`scripts/setup_windows.bat`)
Double-click `scripts\setup_windows.bat` in Windows Explorer or run from CMD:
```cmd
scripts\setup_windows.bat
```

---

## Dataset Generation Utility (`scripts/generate_dataset.py`)

Synthesize multi-schema fine-tuning data on demand without storing bulky JSON files in git:

```bash
# Run CLI generator (outputs to offline/datasets/)
python scripts/generate_dataset.py --sample-count 250 --output-dir offline/datasets

# Output files generated (Strictly git-ignored):
# - offline/datasets/train.json   (Raw pair format)
# - offline/datasets/eval.json    (Evaluation split)
# - offline/datasets/train.jsonl  (ChatML SFT format for Qwen2.5-Coder)
# - offline/datasets/eval.jsonl   (ChatML evaluation format)
```

---

<div align="center">

*NL2SQL Environment Scripts: Technical Specification & Usage*

</div>
