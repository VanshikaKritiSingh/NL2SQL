<div align="center">

# Environment Bootstrap & Setup Scripts

**Cross-Platform Automation for Linux and Windows**

`[Work Status: Implemented & Verified]` &nbsp;|&nbsp; `[Platforms: Linux / macOS / Windows]`

---

</div>

<br />

---

<div align="center">

### Setup Workflow & Repository Volume Protection

</div>

```
+-----------------------------------------------------------------------------------------+
|                               REPOSITORY VOLUME PROTECTION                              |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   [Lightweight Git Clone (< 15MB)]                                                      |
|                 |                                                                       |
|                 v                                                                       |
|   +-----------------------------+     +-----------------------------+                   |
|   |  Linux / macOS              |     |  Windows                    |                   |
|   |  ./scripts/setup_linux.sh   |     |  .\scripts\setup_windows.ps1|                   |
|   +-----------------------------+     +-----------------------------+                   |
|                 |                                   |                                   |
|                 +-----------------+-----------------+                                   |
|                                   |                                                     |
|                                   v                                                     |
|   +---------------------------------------------------------------------------------+   |
|   |  1. Creates isolated virtual environment (.venv)                                |   |
|   |  2. Installs lightweight core dependencies (sqlglot, pydantic, fastapi, pytest) |   |
|   |  3. Installs frontend/desktop dependencies (GUI/node_modules)                   |   |
|   |  4. Synthesizes local fine-tuning dataset in offline/datasets/ (Ignored by Git) |   |
|   |  5. Executes test suite (13/13 passing)                                         |   |
|   +---------------------------------------------------------------------------------+   |
|                                   |                                                     |
|                                   v                                                     |
|             [Ready for Development & Pipeline Integration]                              |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

<div align="center">

### Execution Instructions

</div>

#### 1. Linux & macOS
```bash
# Make script executable (if not already set)
chmod +x scripts/setup_linux.sh

# Standard Setup: Core runtime + Desktop/Web GUI + Local dataset
./scripts/setup_linux.sh

# AI/ML Full Setup: Includes heavy PyTorch, Transformers, PEFT, and TRL
./scripts/setup_linux.sh --ml

# Fast Setup: Skip GUI npm install
./scripts/setup_linux.sh --skip-gui
```

#### 2. Windows PowerShell
```powershell
# Standard Setup: Core runtime + Desktop/Web GUI + Local dataset
.\scripts\setup_windows.ps1

# AI/ML Full Setup: Includes heavy PyTorch, Transformers, PEFT, and TRL
.\scripts\setup_windows.ps1 -InstallML

# Fast Setup: Skip GUI npm install
.\scripts\setup_windows.ps1 -SkipGUI
```

---

<div align="center">

### Fine-Tuning Dataset Management

</div>

To regenerate or scale local training datasets without affecting git tracking:

```bash
# Generate 500 synthetic samples across 8 database schemas
python scripts/generate_dataset.py --sample-count 500 --output-dir offline/datasets

# Output files generated (Strictly git-ignored):
# - offline/datasets/train.json
# - offline/datasets/eval.json
# - offline/datasets/train.jsonl
# - offline/datasets/eval.jsonl
```

---

<div align="center">

*NL2SQL Environment Scripts: Technical Specification & Usage*

</div>
