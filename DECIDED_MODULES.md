# DECIDED_MODULES.md: NL2SQL Project Architecture Registry

Status: Implemented & Verified (Collaborative Design)
Owner: Anunay Sharma & Team
Last Updated: Phase 1 & 2 Implementation (Core & Offline Suites Complete)

---

## 1. Model Foundation & Offline Training Suite (`offline/training/`)
- **Status:** Implemented & Verified.
- **Components:**
  - `offline/training/train_qlora.py`: 4-bit NF4 QLoRA fine-tuning script with gradient checkpointing and cosine decay. Fits < 7.5GB VRAM on consumer GPUs (RTX 4060 8GB / RTX 3060 12GB).
  - `offline/training/export_gguf.py`: LoRA adapter merging into full 16-bit safetensors, GGUF conversion instructions, and Ollama Modelfile generation for CPU inference (~4.3GB RAM at Q4_K_M).
  - `offline/training/evaluate.py`: AST Exact Match (EM) via `sqlglot` and in-memory execution accuracy (EX) benchmark evaluator.
- **Core Policy:** Zero training from scratch. Use battle-tested pre-trained coder foundations (`Qwen2.5-Coder-7B-Instruct` or `DeepSeek-Coder-V2-Lite`).
- **Adaptation Strategy:**
  - Format: QLoRA (4-bit NF4, rank r=16, alpha=32, target all linear modules).
  - Loss Masking: Masked cross-entropy on SQL tokens only (`labels = -100` on prompt).
  - Splitting: Database-level holdout (unseen database schemas in eval, 70/15/15).
  - Validation Metric: Execution Accuracy (EX) + AST Exact Match (EM).
  - Decoding Strategy: Greedy (`temperature = 0.0`) for deterministic production inference.

---

## 2. Schema Linker & Context Retrieval (`core/schema_linker.py`)
- **Status:** Implemented & Verified (Stage 4: Anunay).
- **Pipeline Role:** Sub-selects relevant tables, columns, foreign keys, and categorical values without dumping full catalogs.
- **Retrieval Architecture:**
  - **Table Selection:** Hybrid BM25 (snake_case and camelCase tokenizer) + Dense Semantic retrieval combined via Reciprocal Rank Fusion (RRF).
  - **Column Pruning:** Two-stage ranking. Preserves all PKs, FKs, and high-relevance filter columns. Drops descriptions first under token budget pressure.
  - **Relational Integrity:** Schema represented as an undirected graph (V=tables, E=FK constraints). Steiner Minimal Tree / shortest path auto-injects necessary bridge tables to prevent broken joins.
  - **Cell Value Grounding:** Pre-built offline `CategoricalValueTrie` for low-cardinality categorical values and aliases; zero runtime DB scanning.
  - **Output Contract:** `LinkedSchemaContext` containing table-qualified DDL fragment (`table.column`) + explicit FK constraints passed to prompt builder.

---

## 3. Deterministic Dialect Transpiler (`core/dialect_converter.py`)
- **Status:** Implemented & Verified (Stage 7: Systems/Transpiler).
- **Pipeline Role:** Converts generic ANSI/Postgres SQL AST into target engine dialect deterministically without LLM calls.
- **Engine:** `sqlglot` AST transpiler + Custom Non-Relational AST Visitors (`OpenCypherVisitor`, `MongoMQLVisitor`).
- **Supported Targets:**
  - **Relational & OLAP SQL (20+ Dialects):** PostgreSQL, MySQL, SQLite, DuckDB, ClickHouse, Snowflake, BigQuery, Oracle, T-SQL / SQL Server, Redshift, StarRocks, Trino, Presto, Spark, Databricks.
  - **Graph Paradigm (openCypher):** Neo4j, AWS Neptune (openCypher endpoint), Kùzu.
  - **Document NoSQL Paradigm (MQL):** MongoDB, Amazon DocumentDB (Aggregation Pipelines: `$match`, `$group`, `$sort`, `$limit`, `$project`).
- **Capabilities:**
  - Sub-5ms execution time, zero token spend.
  - Deterministic function and operator re-writing (`CONCAT`, `INTERVAL`, string slicing).
  - Target dialect identifier case-normalization.
  - **Unsupported Feature Protocol:** Raises typed `DialectFeatureUnsupportedError` containing the AST failure node to feed the Stage 8 retry gate.

---

## 4. Paradigm Suggestor & Intent Router (`core/paradigm_suggestor.py`)
- **Status:** Implemented & Verified (Stage 0: Auto Mode & Guardrails).
- **Pipeline Role:** Speculatively classifies user intent into database paradigms (Relational SQL, Graph openCypher, Document NoSQL, Key-Value, Column-Family OLAP, Time-Series) and routes Auto Mode.
- **Architecture:**
  - **CLEF Discourse & Structural Drafter:** CPU-efficient regex pattern mining (< 2ms latency).
  - **Confidence-Scheduled Speculative Verification:** High confidence drafts (>0.85) route immediately; ambiguous queries trigger lightweight LLM verification.
  - **Auto Mode Routing:** Recommends optimal storage engines with educational trade-off explanations.
  - **Manual Divergence Guardrail:** When a user manually selects an engine that differs from the optimal paradigm (e.g. asking for multi-hop graph traversals on PostgreSQL), generates a structured `Paradigm Divergence Warning` while strictly executing the user's explicit choice.

---

## 5. Pipeline Orchestrator (`core/orchestrator.py`)
- **Status:** Implemented & Verified (Stage 12: Dual-Path Router).
- **Pipeline Role:** End-to-end execution loop coordinating AI/ML parsing, static validation, cost checks, and execution gating.
- **Dual-Path Routing:**
  - **Read-Only queries (`SELECT`):** Dispatched automatically to `SANDBOX_REPLICA`.
  - **Mutating & DDL queries (`INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`):** Directed to `APPROVAL_GATE` for human sign-off with visual schema diffs.
