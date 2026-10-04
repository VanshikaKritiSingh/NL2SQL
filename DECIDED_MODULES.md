# DECIDED_MODULES.md — NL2SQL Project Module Registry

Status: In Progress (Collaborative Design)
Owner: Anunay Sharma & Team
Last Updated: Phase 1 Decisions (Modules 0, 1, 2 Locked)

---

## 1. Module 0: Model Foundation & Offline Training/Eval Suite (`offline/training/`)
- **Status:** Architecture Locked (Utility / Offline Only, not in runtime path).
- **Core Policy:** Zero training from scratch. Use battle-tested pre-trained coder foundations (e.g., `Qwen2.5-Coder-7B-Instruct` or `DeepSeek-Coder-V2-Lite`).
- **Adaptation Strategy:** If dialect/schema fine-tuning is required:
  - Format: QLoRA (4-bit NF4, rank r=32, target all linear modules).
  - Loss Masking: Masked cross-entropy on SQL tokens only (`labels = -100` on prompt).
  - Splitting: Database-level holdout (unseen database schemas in eval, 70/15/15).
  - Validation Metric: Execution Accuracy (EX) + Test-Suite Execution Accuracy (TS-EX) on live sandboxed DB, never string match / BLEU.
  - Decoding Strategy: Greedy (`temperature = 0.0`) for deterministic production inference.
- **Negative Sampling:** Synthetic prompts with unresolvable schema questions map to structured error envelopes (`{"sql": null, "error": "UNMAPPED_COLUMN"}`).

---

## 2. Module 1: Schema Linker / Context Retrieval (`pipeline/schema_linker.py`)
- **Status:** Architecture Locked (Stage 4 - Anunay).
- **Pipeline Role:** Sub-selects relevant tables, columns, foreign keys, and categorical values without dumping full catalogs.
- **Retrieval Architecture:**
  - Table Selection: Hybrid BM25 (snake_case tokenizer) + Dense Vector retrieval combined via Reciprocal Rank Fusion (RRF).
  - Column Pruning: Two-stage ranking. Preserves all PKs, FKs, and high-relevance filter columns. Drops descriptions first under token budget pressure.
  - Relational Integrity: Schema represented as an undirected graph ($V=\text{tables}, E=\text{FK constraints}$). Steiner Minimal Tree / shortest path auto-injects necessary bridge tables to prevent broken joins.
  - Cell Value Grounding: Pre-built offline trie / KV index for low-cardinality categorical values and aliases; zero runtime DB scanning.
  - Output Contract: Table-qualified DDL fragment (`table.column`) + explicit FK constraints passed to prompt builder.

---

## 3. Module 2: Deterministic Dialect Converter (`pipeline/dialect_converter.py`)
- **Status:** Architecture Locked (Stage 7 - Systems/Transpiler).
- **Pipeline Role:** Converts generic ANSI/Postgres SQL AST into target engine dialect deterministically without LLM calls.
- **Engine:** `sqlglot` AST transpiler.
- **Capabilities:**
  - Sub-5ms execution time, zero token spend.
  - Deterministic function and operator re-writing (`CONCAT`, `INTERVAL`, string slicing).
  - Target dialect identifier case-normalization.
  - Unsupported Feature Protocol: Raises typed `DialectFeatureUnsupportedError` containing the AST failure node to feed the Stage 8 retry gate.
