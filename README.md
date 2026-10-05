<div align="center">

# NL2SQL Production Pipeline

**Universal Natural Language to Multi-Paradigm Database Compiler**

`[Project Status: Phase 1 & 2 Complete]` &nbsp;|&nbsp; `[Build: Passing]` &nbsp;|&nbsp; `[Version: 0.2.0]`

---

**Engineering Team**

| Member | Department / Role | Focus Area |
| :--- | :--- | :--- |
| **Anunay Sharma** | AI & Machine Learning | Schema Linker, Paradigm Router, Universal Transpiler, Offline QLoRA |
| **Sarthak Singh** | Software Dev & Security | Static AST Validator, Query Cost Estimator |
| **Vanshika Kriti Singh** | GUI & Systems Observability | Desktop & Web Studio Shell, Human Approval Gate |

</div>

<br />

---

<div align="center">

### System Architecture Overview

</div>

```
+----------------------------------------------------------------------------------------------------+
|                                    16-STAGE PRODUCTION PIPELINE                                    |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+-----------------------+     +-----------------------+     +---------------------------------------+
|  Query Intake         | --> |  Paradigm Router      | --> |  Schema Linker & Context Grounding    |
|  (Natural Language)   |     |  (SQL / Graph / MQL)  |     |  (BM25 + Semantic RRF + Steiner Tree) |
+-----------------------+     +-----------------------+     +---------------------------------------+
                                                                                |
                                                                                v
+-----------------------+     +-----------------------+     +---------------------------------------+
|  Dialect Transpiler   | <-- |  Foundation Model     | <-- |  Context & Prompt Builder             |
|  (20+ SQL, Cypher, MQL|     |  (Qwen2.5 / DeepSeek) |     |  (Table DDL + Value Grounding)        |
+-----------------------+     +-----------------------+     +---------------------------------------+
            |
            v
+-----------------------+     +-----------------------+     +---------------------------------------+
|  Static Validator     | --> |  Cost Estimator       | --> |  Dual-Path Execution Router           |
|  (AST & Anti-Patterns)|     |  (EXPLAIN & Row Limits|     +---------------------------------------+
+-----------------------+     +-----------------------+              |                    |
                                                                     | (Read-Only)        | (Mutating / DDL)
                                                                     v                    v
                                                        +-----------------------+  +----------------+
                                                        |  Sandbox Replica      |  |  Approval Gate |
                                                        |  (Direct DB Dispatch) |  |  & Visual Diff |
                                                        +-----------------------+  +----------------+
```

---

<div align="center">

### Repository Structure & Domain Separation

</div>

```
NL2SQL/
|-- core/                            # Core Runtime Engine (AI/ML Backbone)
|   |-- paradigm_suggestor.py        # CLEF intent drafter & speculative auto-router
|   |-- schema_linker.py             # Hybrid RRF table ranking & Steiner join builder
|   |-- dialect_converter.py         # Deterministic AST transpiler (20+ SQL dialects, Cypher, MQL)
|   |-- orchestrator.py              # Unified pipeline orchestrator
|   |-- README.md                    # Dedicated AI/ML handbook
|   `-- __init__.py
|
|-- validator/                       # Static AST Validator & Policy Guardrails (Software & Security)
|   |-- contracts.py                 # Immutable validation issue models & status contracts
|   |-- engine.py                    # Multi-layer rule execution engine
|   |-- interfaces.py                # Schema provider and audit logger interfaces
|   `-- rules/                       # Parse, policy, schema, and semantic rule sets
|
|-- cost_estimator/                  # Query Cost & Blast-Radius Estimator (Software & Security)
|   |-- contracts.py                 # Cost report structures & threshold definitions
|   |-- thresholds.py                # Configurable row scan and execution limits
|   `-- adapters/postgres.py         # EXPLAIN plan parser & replica row estimator
|
|-- GUI/                             # Native Desktop & Web Interface Studio (Frontend & Systems)
|   |-- src/                         # React 18, TypeScript, Monaco Editor, React Flow ER Diagrams
|   |-- electron/                    # Electron container & native OS lifecycle bridge
|   `-- server/                      # FastAPI bridge stubs for pipeline integration
|
|-- offline/                         # AI/ML Offline Suite (Isolated)
|   |-- training/train_qlora.py      # 4-bit NF4 QLoRA fine-tuning script (< 7.5GB VRAM)
|   |-- training/export_gguf.py      # LoRA merge, GGUF quantizer & Ollama Modelfile exporter
|   |-- training/evaluate.py         # AST Exact Match & Execution Accuracy benchmark runner
|   `-- training/requirements-train.txt # Isolated ML dependencies (PyTorch, PEFT, TRL, etc.)
|
`-- tests/                           # Unit and integration test suite (13/13 passing)
```

---

<div align="center">

### Subsystem Implementation Matrix

</div>

| Subsystem | Scope / Responsibility | Owner | Work Status |
| :--- | :--- | :--- | :--- |
| **Model Foundation & Training** | QLoRA fine-tuning & GGUF CPU export | Anunay Sharma | `[Status: Complete]` |
| **Schema Linker** | Hybrid RRF retrieval & Steiner join injection | Anunay Sharma | `[Status: Complete]` |
| **Dialect Transpiler** | SQL AST conversion (20+ dialects, Cypher, MQL) | Anunay Sharma | `[Status: Complete]` |
| **Paradigm Router** | Intent classification & auto-routing | Anunay Sharma | `[Status: Complete]` |
| **Pipeline Orchestrator** | End-to-end execution loop & dual-path router | Anunay Sharma | `[Status: Complete]` |
| **Static Validator** | AST verification & anti-pattern detection | Sarthak Singh | `[Status: Complete]` |
| **Cost Estimator** | EXPLAIN plan cost & blast radius checks | Sarthak Singh | `[Status: Complete]` |
| **Approval Gate & Studio** | Desktop & Web Studio with ER diff visualization | Vanshika Kriti Singh | `[Status: Complete]` |

---

<div align="center">

### Quick Start Guide

</div>

#### 1. Core Engine & Backend Dependencies
For general development, API integration, and test execution (lightweight, standard Python):

```bash
# Clone the repository
git clone https://github.com/VanshikaKritiSingh/NL2SQL.git
cd NL2SQL

# Create virtual environment and install core runtime packages
python3 -m venv .venv
source .venv/bin/activate
pip install sqlglot networkx pytest

# Run the test suite
PYTHONPATH=. pytest tests/ -v
```

#### 2. Native Desktop Application & Web Studio
The UI can run as a standalone desktop executable or browser application:

```bash
# Navigate to GUI directory
cd GUI
npm install

# Option A: Run native desktop app in live dev mode
npm run desktop:dev

# Option B: Run browser web app
npm run dev
```

#### 3. AI / ML Offline Suite (Optional)
Heavy machine learning dependencies are strictly isolated inside `offline/training/`. Only team members performing local QLoRA fine-tuning or GGUF conversion need these packages:

```bash
pip install -r offline/training/requirements-train.txt
python offline/training/train_qlora.py --help
```

---

<div align="center">

### Verification & Testing

</div>

```
============================== 13 passed in 0.14s ==============================
- CLEF Drafter Intent Routing (Graph, Document, KV, OLAP): PASSED
- Paradigm Suggestor Auto Mode & Manual Guardrails: PASSED
- Dialect Transpilation (PostgreSQL, MySQL, SQLite, Cypher, MQL): PASSED
- Categorical Value Trie Grounding: PASSED
- Steiner Tree FK Bridge Join Injection: PASSED
- End-to-End Orchestrator Dual-Path Routing: PASSED
```

---

<div align="center">

*NL2SQL Project: Phase 1 & 2 Evaluation Milestone*

</div>
