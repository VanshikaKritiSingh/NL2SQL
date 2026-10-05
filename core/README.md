<div align="center">

# NL2SQL Core Engine & AI/ML Architecture

**Intent Classification, Context Pruning, and Deterministic Multi-Paradigm Transpilation**

`[Work Status: Complete]` &nbsp;|&nbsp; `[Test Suite: 13/13 Passing]` &nbsp;|&nbsp; `[Latency: < 5ms]`

---

**Lead AI/ML Engineer:** Anunay Sharma &nbsp;|&nbsp; **Package:** `core/` & `offline/`

</div>

<br />

---

<div align="center">

### Core Architecture & Component Flow

</div>

```
+----------------------------------------------------------------------------------------------------+
|                                      CORE RUNTIME ARCHITECTURE                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    [Natural Language Prompt]                                                                       |
|                |                                                                                   |
|                v                                                                                   |
|   +--------------------------+                                                                     |
|   |  paradigm_suggestor.py   |  --> CLEF Pattern Intent Mining (< 2ms on CPU)                      |
|   |  (Stage 0 Intent Router) |  --> Auto Mode Recommendation + Divergence Guardrails               |
|   +--------------------------+                                                                     |
|                |                                                                                   |
|                v                                                                                   |
|   +--------------------------+                                                                     |
|   |  schema_linker.py        |  --> Offline CategoricalValueTrie Cell Grounding                   |
|   |  (Stage 4 Context RAG)   |  --> BM25 + Semantic Reciprocal Rank Fusion (RRF)                   |
|   |                          |  --> Steiner Minimal Tree FK Bridge Join Injection                 |
|   +--------------------------+                                                                     |
|                |                                                                                   |
|                v                                                                                   |
|   +--------------------------+                                                                     |
|   |  dialect_converter.py    |  --> 20+ Relational SQL Dialects (Postgres, MySQL, DuckDB, etc.)    |
|   |  (Stage 7 Transpiler)    |  --> OpenCypherVisitor (Neo4j, Neptune, Kuzu)                       |
|   |                          |  --> MongoMQLVisitor (MongoDB Aggregation Pipelines)                |
|   +--------------------------+                                                                     |
|                |                                                                                   |
|                v                                                                                   |
|   +--------------------------+                                                                     |
|   |  orchestrator.py         |  --> Static Validation (validator) & Cost Estimation (cost_estimator)|
|   |  (Pipeline Orchestrator) |  --> Dual-Path Dispatch: Safe Sandbox vs M14 Human Approval Gate    |
|   +--------------------------+                                                                     |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

<div align="center">

### Supported Paradigms & 20+ Dialects Matrix

</div>

| Paradigm | Underlying Mechanism | Supported Dialects & Engines | Workload Focus |
| :--- | :--- | :--- | :--- |
| **1. Relational (RDBMS)** | ANSI SQL & Relational Algebra | PostgreSQL, MySQL, SQLite, Oracle, T-SQL / SQL Server, MariaDB | Normalized transactional records |
| **2. Column-Family / OLAP** | Vectorized Columnar Scanning | Snowflake, Google BigQuery, ClickHouse, DuckDB, Redshift, StarRocks, Trino, Presto, Spark SQL, Databricks | Analytical aggregations, time-series cubes |
| **3. Graph Database** | Declarative Graph Traversal | Neo4j, AWS Neptune (openCypher endpoint), Kuzu | Multi-hop paths, shortest path, fraud rings |
| **4. Document NoSQL** | JSON MQL Aggregation Pipelines | MongoDB, Amazon DocumentDB, CouchDB | Dynamic schemas, nested JSON sub-documents |
| **5. Key-Value (KV)** | Hash Map Lookups & Mutations | Redis, Amazon DynamoDB (KV mode), Memcached | Sub-millisecond point lookups, token store |
| **6. Time-Series** | Timestamp Bucket Aggregations | TimescaleDB, InfluxDB | Telemetry rollups, sensor streaming |

---

<div align="center">

### Core Module Layout

</div>

```
core/
|-- paradigm_suggestor.py    # [Status: Complete] Speculative Query Intent Classifier & Auto Mode Router
|-- schema_linker.py         # [Status: Complete] BM25 + Semantic RRF Pruner & Steiner Tree Join Injector
|-- dialect_converter.py     # [Status: Complete] Deterministic AST Transpiler & Graph/MQL Visitors
|-- orchestrator.py          # [Status: Complete] Unified Pipeline Dispatcher & Dual-Path Router
`-- __init__.py
```

---

<div align="center">

### AI/ML Offline Suite (Isolated)

</div>

```
offline/
|-- training/
|   |-- train_qlora.py       # 4-bit NF4 QLoRA fine-tuning (< 7.5GB VRAM on RTX 4060 / 3060)
|   |-- export_gguf.py       # LoRA merge & GGUF Q4_K_M quantization + Ollama Modelfile
|   |-- evaluate.py          # AST Exact Match (EM) & in-memory SQLite Execution Accuracy (EX)
|   `-- requirements-train.txt # Isolated ML dependencies (PyTorch, Transformers, PEFT, TRL)
|-- datasets/
|   |-- prepare_dataset.py   # Multi-schema synthetic fine-tuning dataset generator
|   `-- .gitkeep             # Generated datasets strictly git-ignored
`-- checkpoints/             # Checkpoint weights strictly git-ignored
```

---

<div align="center">

### Verification & Testing

</div>

```bash
# Run core test suite
PYTHONPATH=. ./.venv/bin/pytest tests/ -v
```

```
============================== 13 passed in 0.13s ==============================
- CLEF Drafter Intent Routing (Graph, Document, KV, OLAP): PASSED
- Paradigm Suggestor Auto Mode & Manual Guardrails: PASSED
- Dialect Transpilation (PostgreSQL, MySQL, SQLite, Cypher, MQL): PASSED
- Categorical Value Trie Grounding: PASSED
- Steiner Tree FK Bridge Join Injection: PASSED
- End-to-End Pipeline Orchestration & Dual-Path Routing: PASSED
```

---

<div align="center">

*NL2SQL Core Package: Technical Documentation & Implementation Reference*

</div>
