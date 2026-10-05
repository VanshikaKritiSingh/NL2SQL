<div align="center">

# NL2SQL Production Pipeline

**Universal Natural Language to Multi-Paradigm Database Compiler**

`[Project Status: Phase 1 & 2 Complete]` &nbsp;|&nbsp; `[Build: Passing]` &nbsp;|&nbsp; `[Version: 0.2.0]`

---

**Engineering Team**

| Member | Department / Role | Focus Modules |
| :--- | :--- | :--- |
| **Anunay Sharma** | AI & Machine Learning | Schema Linker (M1), Paradigm Router (M3), Offline QLoRA (M0) |
| **Sarthak Singh** | Software Dev & Security | Static Validator (M9), Cost Estimator (M10), Dialect Converter (M2) |
| **Vanshika Kriti Singh** | GUI & Systems Observability | Desktop & Web Studio Shell (M1, M14), Approval Gate |

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
|  M1: Query Intake     | --> |  M3: Paradigm Router  | --> |  M1: Schema Linker & Context Grounding|
|  (Natural Language)   |     |  (SQL / Graph / MQL)  |     |  (BM25 + Semantic RRF + Steiner Tree) |
+-----------------------+     +-----------------------+     +---------------------------------------+
                                                                                |
                                                                                v
+-----------------------+     +-----------------------+     +---------------------------------------+
|  M2: Dialect Transpile| <-- |  M6: Foundation Model | <-- |  M5: Context & Prompt Builder         |
|  (20+ SQL, Cypher, MQL|     |  (Qwen2.5 / DeepSeek) |     |  (Table DDL + Value Grounding)        |
+-----------------------+     +-----------------------+     +---------------------------------------+
            |
            v
+-----------------------+     +-----------------------+     +---------------------------------------+
|  M9: Static Validator | --> |  M10: Cost Estimator  | --> |  M12: Dual-Path Execution Router      |
|  (AST & Anti-Patterns)|     |  (EXPLAIN & Row Limits|     +---------------------------------------+
+-----------------------+     +-----------------------+              |                    |
                                                                     | (Read-Only)        | (Mutating / DDL)
                                                                     v                    v
                                                        +-----------------------+  +----------------+
                                                        |  M13: Sandbox Exec    |  |  M14: Approval |
                                                        |  (Direct DB Dispatch) |  |  Gate & Visual |
                                                        +-----------------------+  +----------------+
```

---

<div align="center">

### Repository Structure & Domain Separation

</div>

```
NL2SQL/
|-- core/                            # Core Runtime Engine (Zero Heavy ML Dependencies)
|   |-- paradigm_suggestor.py        # [Status: Complete] CLEF intent drafter & auto-router
|   |-- schema_linker.py             # [Status: Complete] Hybrid RRF table ranking & Steiner join builder
|   |-- dialect_converter.py         # [Status: Complete] Deterministic AST transpiler (20+ SQL dialects)
|   `-- __init__.py
|
|-- m09_validator/                   # [Status: Complete] Static AST Validator & Policy Guardrails
|   |-- contracts.py                 # Immutable validation issue models & status contracts
|   |-- engine.py                    # Multi-layer rule execution engine
|   `-- rules/                       # Parse, policy, schema, and semantic rule sets
|
|-- m10_cost/                        # [Status: Complete] Query Cost & Blast-Radius Estimator
|   |-- contracts.py                 # Cost report structures & threshold definitions
|   |-- thresholds.py                # Configurable row scan and execution limits
|   `-- adapters/postgres.py         # EXPLAIN plan parser & replica row estimator
|
|-- GUI/                             # [Status: Complete] Native Desktop & Web Interface Studio
|   |-- src/                         # React 18, TypeScript, Monaco Editor, React Flow ER Diagrams
|   |-- electron/                    # Electron container & native OS lifecycle bridge
|   `-- server/                      # FastAPI bridge stubs for pipeline integration
|
|-- offline/                         # [Status: Complete] AI/ML Offline Suite (Isolated)
|   |-- training/train_qlora.py      # 4-bit NF4 QLoRA fine-tuning script (< 7.5GB VRAM)
|   |-- training/export_gguf.py      # LoRA merge, GGUF quantizer & Ollama Modelfile exporter
|   |-- training/evaluate.py         # AST Exact Match & Execution Accuracy benchmark runner
|   `-- training/requirements-train.txt # Isolated ML dependencies (PyTorch, PEFT, TRL, etc.)
|
`-- tests/                           # Unit and integration test suite (12/12 passing)
```

---

<div align="center">

### Module Implementation Matrix

</div>

| Module | Name | Scope / Responsibility | Owner | Work Status |
| :--- | :--- | :--- | :--- | :--- |
| **M0** | Model Suite | QLoRA fine-tuning & GGUF CPU export | Anunay | `[Status: Complete]` |
| **M1** | Schema Linker | Hybrid RRF retrieval & Steiner join injection | Anunay | `[Status: Complete]` |
| **M2** | Dialect Transpiler | SQL AST conversion (20+ dialects, Cypher, MQL) | Sarthak / Anunay | `[Status: Complete]` |
| **M3** | Paradigm Router | Intent classification & auto-routing | Anunay | `[Status: Complete]` |
| **M9** | Static Validator | AST verification & anti-pattern detection | Sarthak | `[Status: Complete]` |
| **M10** | Cost Estimator | EXPLAIN plan cost & blast radius checks | Sarthak | `[Status: Complete]` |
| **M14** | Approval Gate & GUI | Desktop & Web Studio with ER diff visualization | Vanshika | `[Status: Complete]` |

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

# Install core runtime packages (No heavy GPU/Torch packages required)
pip install -r requirements.txt

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
============================== 12 passed in 0.12s ==============================
- CLEF Drafter Intent Routing (Graph, Document, KV, OLAP): PASSED
- Paradigm Suggestor Auto Mode & Manual Guardrails: PASSED
- Dialect Transpilation (PostgreSQL, MySQL, SQLite, Cypher, MQL): PASSED
- Categorical Value Trie Grounding: PASSED
- Steiner Tree FK Bridge Join Injection: PASSED
```

---

<div align="center">

*NL2SQL Project: Phase 1 & 2 Evaluation Milestone*

</div>
