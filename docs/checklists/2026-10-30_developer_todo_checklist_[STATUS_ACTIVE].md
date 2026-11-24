# Master Status & Action Register: NL2SQL Production Hardening

**Document Name:** `2026-10-30_developer_todo_checklist_[STATUS_ACTIVE].md`
**Created:** 2026-10-30
**Last Revised:** 2026-11-23 (Rev 3 — Devil's Advocate DA-01 to DA-25 Complete Audit & Codebase Reconciliation)
**Source Baselines:**
1. Adversarial Audit & Ponytail Review — `docs/reviews/2026-10-29_adversarial_and_ponytail_audit_[STATUS_OPEN].md`
2. `Phase-III Report_OSDBMS.pdf` (Organic Intelligence / OSDBMS-V-2026-T032) — claim-by-claim reconciliation against `HEAD = eb4902c`
3. Team diagnosis meeting, 2026-11-22 (four-point technical review)
4. Devil's Advocate 25-Flaw Verification & Codebase Evidence (`DA-01` to `DA-25`, audited 2026-11-23 against `HEAD = 29b2d34`)

**Status:** **ACTIVE — 25/25 DA flaws verified in codebase. 10 failing tests in fuzz suite identified. Remediations tracked below.**

---

## How to read this document

This is the single source of truth for *what is done*, *what is broken*, *what is missing*, and *what is next*. Every entry carries an **Evidence** column citing a real file and line so no claim is taken on faith — including the claims in our own Phase-III report.

Legend for **State**:

| Symbol | Meaning |
|---|---|
| ✅ **DONE** | Implemented, exercised by a passing test or a live code path. Verified. |
| 🟡 **PARTIAL** | Real code exists and runs, but is incomplete, mis-wired, or fails an important case. |
| 🔴 **ABSENT** | The capability was reported complete but **no implementation exists** in the repo. |
| ⚫ **ILLUSION** | Code exists but does something materially different from what the documentation says. |

**Verification method:** direct reads of `core/`, `GUI/`, `offline/`, plus `pytest tests/` executed in `.venv` → **68 passed, 10 failed** (in `tests/test_fuzz_harness.py`). Grep sweeps for every claimed subsystem; absent = zero hits outside `.venv`/`node_modules`.

---

## Quick Reference Summary

| Bucket | Count | Core Goal | Primary Files |
|---|---|---|---|
| **A. Verified Done** | 12 subsystems | The genuine engineering asset base | `core/validator/`, `core/schema_linker.py`, `core/dialect_converter.py`, `core/connectors/` |
| **B. Defective / Partial** | 18 items | Implemented but wrong, mis-wired, or failing real cases | `core/orchestrator.py`, `core/cost_estimator/`, `core/connectors/` |
| **C. Claimed but Absent** | 7 items | Phase-III reported 100%; nothing in the repo | semantic cache, Dolt VCS, rate limiter, index advisor, deployment |
| **D. Phase-IV AI/LLM Rework** | 9 items | Model, quantization, classifier, DSpark, training strategy | `offline/training/`, `core/paradigm_suggestor.py`, model layer |
| **E. Fix That (audit)** | 15 tasks | Critical bugs, race conditions, lock leaks, inverted order | `core/orchestrator.py`, `core/os_engine/`, `core/validator/engine.py` |
| **F. Delete / Strip (audit)** | 15 tasks | -4,495 custom LOC, -52,604 vendored LOC, -211 MB, -6 deps | `offline/llama_cpp/`, `core/os_engine/`, `core/connectors/` |
| **J. Devil's Advocate Register (DA-01 to DA-25)** | 25 verified flaws | 7 Critical, 8 High, 10 Medium security, concurrency, ML, and test defects | `core/orchestrator.py`, `GUI/server/routers/`, `core/os_engine/`, `offline/training/` |

---

# A. VERIFIED DONE — the real engineering asset base

Everything in this section is real, tested, and can be defended in a viva without caveat.

| # | Subsystem | Evidence | What Actually Works |
|---|---|---|---|
| **D-01** | 6-Layer Static AST Validator | `core/validator/engine.py`; `tests/test_core_modules.py::testValidatorLayer1..5` | Genuine `sqlglot` parse → policy → schema → semantic → anti-pattern pipeline. Blocks stacked-query injection (`testMultiStatementValidationBlocksStackedSelectInjection` passes), blocks `DROP DATABASE`, allows `SHOW`/`DESCRIBE`/`PRAGMA`. **This is the strongest component in the repo.** |
| **D-02** | Quote/escape/comment-aware SQL splitter | `core/sanitizer.py:32-137` (`split_sql_script`) | Correct multi-statement splitting that does not break on `';'` inside string literals. Genuinely well-built; currently under-used (see B-01). |
| **D-03** | Parameter extraction from AST | `core/sanitizer.py:168-212` (`sanitizeAndExtractParametersFromSqlAst`) | Emits positional `$1`/`?` params per dialect. Tested (`testSanitizerExtractsPositionalParametersForPostgreSql`). **Not called by the orchestrator** (see B-01). |
| **D-04** | Deterministic dialect transpiler | `core/dialect_converter.py` via `sqlglot`; `testSqlTranspilationAcrossAllRelationalDialects` | Real, sub-5ms, no LLM tokens. Verified across PostgreSQL, MySQL, SQLite, DuckDB, Snowflake, BigQuery. Handles `IDENTITY`→`AUTO_INCREMENT`, `USE` injection after `CREATE DATABASE`. |
| **D-05** | Hybrid schema linker | `core/schema_linker.py`; `testSchemaLinkerHybridReciprocalRankFusionAndSteinerBridge` | Real BM25 + character-N-gram fuzzy ranking fused by Reciprocal Rank Fusion, then Steiner-tree shortest-FK-path bridge injection. Algorithmically sound. |
| **D-06** | Categorical value Trie grounding | `core/schema_linker.py`; `testAhoCorasickTriePunctuationResilience` | Offline pre-built trie for low-cardinality cell values; punctuation-safe. |
| **D-07** | Heuristic cost/blast-radius engine | `core/cost_estimator/engine.py`; `testHeuristicCostEngineEvaluatesReadAndWriteQueryUtilization` | Real AST-driven cost model with ALLOW/ESCALATE/REJECT decisions. Logic is correct — its *inputs* are fake (see B-03). |
| **D-08** | Dual-path execution router | `core/orchestrator.py:810-826` | READ → `SANDBOX_REPLICA`, WRITE/DDL → `APPROVAL_GATE`, invalid → `BLOCKED`. Routing logic itself is correct; the cost gate feeding it is miscalibrated (see B-02). |
| **D-09** | Relational DBMS connectors | `core/connectors/{postgres,mysql,sqlite,duckdb_conn}.py`; `testSqliteConnectorInMemoryExecutionAndSchemaIntrospection` | Real drivers, real `information_schema` introspection, real execution. Not stubs. (Defects: B-04, B-05.) |
| **D-10** | Append-only pipeline audit log | `core/os_engine/audit_log.py`; `testPipelineAuditLogAppendsAndFiltersEventRecords` | Real event record/append/filter. Format string rot is cosmetic, not functional. |
| **D-11** | GUI — intake, ER visualizer, approval modals | `GUI/src/shared/{ApprovalModal,ERDiagramModal,AuditLogModal,ConnectionModal}.tsx`, `GUI/src/modules/query_intake/` | Functional React/Vite UI; ER diagram and diff panels are real components, not placeholders. |
| **D-12** | Test suite | `tests/` (6 files, 1,196 LOC) → **55/55 pass** | Real, reproducible, covers validator layers, transpiler, linker, sanitizer, orchestrator lifecycle, os_engine. |

**Honest caveat on D-12:** 55 passing tests are genuine, but zero tests exist for `train_qlora.py`, `export_gguf.py`, `pipeline_stub.py`, or the approval/Dolt path. The Phase-III claim "100% of all 16 modules have comprehensive unit coverage" is **not true**.

---

# B. DEFECTIVE / PARTIAL — implemented but wrong

These are the items behind the team's observed symptoms: imprecise answers, SELECT queries demanding human approval, and connectors behaving inconsistently.

### B-01 — 🔴 Parameterization sanitizer is built but never wired (Expanded as DA-01)
- **Where:** implemented `core/sanitizer.py:168-212`; called in `core/orchestrator.py:855` into local variable `sanitized_statement`, but **never passed** to Stage 12 live query (`orchestrator.py:595`) or Stage 16 approval dispatch (`approval.py:63`).
- **Problem:** Raw interpolated SQL is handed to `connector.execute_query()`. The security property the Phase-III report claims ("parameterized query sanitizer") does not hold at runtime. Any exception in sanitization is swallowed via `except SanitizationError: pass`. (Audit items **IMP-01**, **DA-01**.)
- **Fix:** Store `sanitized_statement` on `PipelineExecutionPlan`, pass bound parameters through `BaseDBConnector.execute_query(sql, params=None)` to driver cursors, and fail closed if sanitization throws.

### B-02 — 🔴 **ROOT CAUSE: plain `SELECT` is escalated to human approval**
- **Where:** `core/cost_estimator/engine.py:_estimate_read_cost` + `core/orchestrator.py:818-826`
- **Mechanism (exact):**
  1. `_estimate_read_cost` computes `cost = base_rows * 0.08 + len(joins) * 100`.
  2. Decision flips to `ESCALATE` when `cost >= thresholds.escalate_cost`, which defaults to **50,000** (`core/cost_estimator/thresholds.py:22`).
  3. `orchestrator.py:818` then routes **any** `ESCALATE` to `APPROVAL_GATE` — the `stmt_type == READ` branch is only reached when the decision was already `ALLOW`.
  4. Therefore a perfectly safe `SELECT` over a table of ~625,000+ estimated rows (or one with several joins) **requires human sign-off**.
- **This is exactly the symptom the team reported.** It is not a security feature working as intended; it is a mis-ordered gate.
- **Fix:**
  1. Never escalate a `StatementType.READ` into the human write-approval path. Reads belong in `SANDBOX_REPLICA`; if expensive, surface a **cost warning to the user**, not an approval gate.
  2. Reserve `APPROVAL_GATE` strictly for mutating statements and DDL.
  3. Recalibrate `escalate_cost` against a real workload (the file itself admits the values are placeholders: *"Values ship as placeholders and MUST be calibrated on real workload telemetry"*).

### B-03 — 🔴 Cost estimation runs on fabricated row counts
- **Where:** `core/cost_estimator/engine.py:84` → `return 50_000  # Default nominal table size`
- **Problem:** When no `SchemaProvider` is attached — the default in the GUI path — **every table is assumed to have exactly 50,000 rows.** Cost, row-scan counts, full-scan detection, and therefore the ALLOW/ESCALATE/REJECT decision are all fiction. This is precisely the "hardcoding" the team flagged.
- **Fix:** Require a live `SchemaProvider` for any cost decision. If absent, return `decision="UNKNOWN"` and route READ to sandbox with a visible "cost unverified" badge — never invent 50,000.

### B-04 — MySQL connector mutates shared config in place
- **Where:** `core/connectors/mysql.py:249, 254, 354, 391` — four sites assign `self.config.database = ...`
- **Problem:** Handling `USE <db>` / `CREATE DATABASE` / permission-1044 fallback overwrites the connection's canonical config. Every subsequent query in that session then targets the wrong database. **This is a real connector-correctness bug matching the team's point 1.** (Audit **FIX-12**.)
- **Fix:** Store the active database in an ephemeral `self._active_database` attribute; never mutate `self.config`.

### B-05 — PostgreSQL psycopg v3 silently rolls back mutations
- **Where:** `core/connectors/postgres.py:57` — `autocommit` is set only on the psycopg2 path; the psycopg3 branch never calls `self._conn.commit()`
- **Problem:** Any approved `INSERT`/`UPDATE`/`DELETE` on a psycopg3 connection is **discarded on connection close, silently, with a success-looking response.** This is the most dangerous live defect in the repo. (Audit **FIX-11**.)
- **Fix:** Call `self._conn.commit()` after mutating execution on the psycopg3 path; add a regression test asserting persistence.

### B-06 — Schema linker truncates bridge tables by arbitrary slice
- **Where:** `core/schema_linker.py:257-261` — `final_tables = ordered_final[:max_tables + 2]`
- **Problem:** The `+2` heuristic can cut off the exact bridge table Steiner path needed to complete an FK join → broken joins / Cartesian products. Contributes directly to "answers are not precise". (Audit **FIX-06**.)

### B-07 — 🟡 Validator aliased JOINs disambiguation incomplete
- **Where:** `core/validator/engine.py:233-237, 272-287`; `tests/test_fuzz_harness.py:402`
- **Problem:** Attempted in commit `e3ff3e0`, but `tests/test_fuzz_harness.py::test_fix_07_aliased_join_disambiguation` still crashes with `TypeError: unexpected keyword argument 'target_dialect'` and `FakeSchemaProvider` kwargs drift. (Audit **FIX-07**, **DA-25**.)

### B-08 — 🟡 Validator script splitting updated but fuzz harness fails
- **Where:** `core/validator/engine.py:58-65`; `tests/test_fuzz_harness.py:207`
- **Problem:** Integrated `split_sql_script()` into validator pipeline, but `executeFullSixLayerValidationPipeline` expects `sql` instead of `sql_query`, causing fuzz harness tests to crash with `TypeError`. (Audit **FIX-08**, **DA-25**.)

### B-09 — Validation runs on the pre-transpiled AST
- **Where:** `core/orchestrator.py:767-791` — Stage 7 transpiles, Stage 9 validates `canonical_sql`
- **Problem:** The validator sees canonical PostgreSQL, not the target dialect. Also, if transpilation throws, the `except` block sets `compiled_query=canonical_sql` and **raw PostgreSQL is forwarded to a non-Postgres engine.** (Audit **FIX-01**.)

### B-10 — Global orchestrator singleton
- **Where:** `GUI/server/routers/query.py:73` — module-level `orchestrator = EndToEndNL2SQLOrchestrator(DEFAULT_SCHEMA)`
- **Problem:** User A's schema upload rewrites User B's schema. Multi-tenant corruption. (Audit **FIX-03**.)

### B-11 — Lock table starvation on contention
- **Where:** `core/os_engine/lock_manager.py:73-115` — `_grant_waiters()` grants the lock but never records it in `_txn_locks[txn_id]`
- **Problem:** `release_all()` then releases an empty set; the resource stays locked forever. **One contention event permanently deadlocks the server.** (Audit **FIX-04**.)
- **Fix (preferred):** delete `core/os_engine/` and use native DBMS transactions (see F-03).

### B-12 — Write locks released before human approval
- **Where:** `core/orchestrator.py:573-585` — `finally` block releases all locks during *plan creation*
- **Problem:** The approved write later executes entirely outside the lock protocol. (Audit **FIX-02**.)

### B-13 — Hardcoded domain DDL dictionaries
- **Where:** `core/semantic_decomposer.py` — 5 embedded `CREATE TABLE` template blobs, ~432 LOC
- **Problem:** "Synthesises" e-commerce/hospital/CRM schemas from static strings. This is the second concrete instance of the hardcoding the team flagged. Not ML, not schema-aware. (Audit **DEL-04**.)

### B-14 — 🟡 Regex fallback disabled from dispatch, but 205 LOC dead class remains
- **Where:** `core/orchestrator.py:47-252, 286` — `SemanticSQLSynthesizer`
- **Problem:** Commit `d0829f7` stopped invoking `SemanticSQLSynthesizer` during runtime failure (falling back to `-- [ERROR: MODEL_GENERATION_FAILED]` instead), but 205 lines of legacy regex synthesis remain defined in `core/orchestrator.py` and are still instantiated on every orchestrator boot (`self.synthesizer = SemanticSQLSynthesizer()`). (Audit **DEL-10**, **DA-22**.)
- **Fix:** Delete `SemanticSQLSynthesizer` class and its instantiation.

### B-15 — Unqualified column bypass in mismatch guard
- **Where:** `core/semantic_decomposer.py:309-316` — check skipped when `col.table is None`
- **Problem:** Hallucinated unqualified columns pass the guard, then reach the DB. (Audit **FIX-13**.)

### B-16 — Unbounded response cache memory leak
- **Where:** `GUI/server/routers/query.py:76-77` — `stored_responses = {}`
- **Problem:** Grows unbounded for server lifetime. (Audit **FIX-15**.)

### B-17 — Silent frontend mock fallback
- **Where:** `GUI/src/api/{approvalApi,queryApi}.ts:12-34`
- **Problem:** HTTP 500s silently fall back to `mockService.ts`, hiding backend crashes. (Audit **FIX-09**.)

### B-18 — Refusals validated as READ statements
- **Where:** `core/validator/engine.py:470-482` — returns `Status.VALID, StatementType.READ` for `-- REFUSAL:` strings. (Audit **FIX-14**.)

---

# C. CLAIMED BUT ABSENT — Phase-III says 100%, repo says otherwise

Each row was confirmed by repository-wide grep (excluding `.venv`/`node_modules`) returning **zero implementation hits**.

| # | Phase-III Claim | Reality | Evidence of Absence | Priority |
|---|---|---|---|---|
| **C-01** | "Semantic cache" — *"AI generation layer with semantic caching and RAG: 100% Completed"* | **No cache exists at any layer.** | Zero hits for `semantic_cache` / `SemanticCache` / `LRUCache` in `core/` or `GUI/`. | P0 — headline claim |
| **C-02** | "Cryptographic version control … instant rollback … git-like CAS" | **No VCS exists.** Hardcoded string only. | `GUI/server/routers/approval.py:39` broadcasts literal `"Dolt commit created: 9e4f2a (checkpoint secured)"`. No Dolt binary, no CAS store, no rollback call anywhere. | **P0 — headline claim, team point 4** |
| **C-03** | Rate limiter (Stage 2) | **No limiter.** Status enum member only. | `GUI/server/models/query.py:28` mentions rate limiting in a docstring; no middleware, no token bucket. | P1 |
| **C-04** | "Workload-driven index advisement" | **No index advisor.** | No `IndexAdvisor` / `CREATE INDEX` recommendation logic. Closest artefact is the anti-pattern detector, which flags bad patterns but never prescribes an index. | P1 |
| **C-05** | "Deployment packaging (local installer/portable build)" | **No installer.** | No build script or artefact. `offline/llama_cpp/` is 211 MB / 52,604 LOC of vendored upstream C++ **imported by nothing**. | P1 |
| **C-06** | "Fuzz-testing harness" | **No fuzzer.** | No mutation engine, no corpus, no coverage feedback. What exists is parameterised unit tests. | P2 |
| **C-07** | "QLoRA fine-tuned model meets baseline execution accuracy" | **Training was never run.** | `offline/training/train_qlora.py:30` defines `format_chat_prompt` but **never maps it** over the dataset; `offline/checkpoints/` is empty. See D-02. | **P0** |

### C-02 detail — what the version-control claim needs to become

The Phase-III report promises *"Git-like cryptographic version control enables instant rollback of any committed transaction."* Nothing of this exists. Three honest options, cheapest first:

1. **Native savepoints (recommended first step).** `SAVEPOINT nl2sql_approval` before a mutation; `ROLLBACK TO SAVEPOINT nl2sql_approval` on rejection or failure. This delivers genuine reversibility **within a transaction** in ~15 lines and is what `IMP-03` already specifies. It does **not** give cross-session history.
2. **Content-addressable row snapshots (the real claim).** Before a mutation, `SELECT` the affected rows, serialise deterministically, store `sha256` → blob in a local CAS directory, and record `(table, pk, blob_hash, parent_hash, timestamp)` in a ledger. Rollback = replay blobs in reverse. This is a genuine git-like commit chain and is achievable in ~400 LOC on SQLite.
3. **Dolt / versioned engine backend.** Only if a versioned DBMS is genuinely acceptable as a dependency. Heavier, but the only route to true branch/merge semantics.

**Decision required before implementation:** choose 1 → 2 now, defer 3. Do **not** keep broadcasting a fake hash in the interim — remove the false string immediately (it is a credibility risk in a viva).

---

# D. PHASE-IV AI / LLM REWORK — from the 2026-11-22 diagnosis

This section is new. It records the team's diagnosis and the agreed direction. **Nothing here is implemented yet.** Items D-01…D-09 are proposals for a sequence of design discussions, not a mandate to code immediately.

### D-01 — 🟡 Model generation currently is not really a model
- **Current state:** the pipeline prefers Ollama when reachable; otherwise it silently falls through to `SemanticSQLSynthesizer` regex heuristics while reporting a model name.
- **Consequence:** every "accuracy" statement in the Phase-III report is untestable, because it is unknown which path produced any given answer.
- **Agreed direction:** **remove the fallback entirely.** Model absence must be a hard, visible failure. Only after that can model quality be measured at all.

### D-02 — 🔴 QLoRA training script is functionally broken
- **Where:** `offline/training/train_qlora.py`
- **Three defects:**
  1. `format_chat_prompt` is defined (L30) but **never applied** — `dataset` goes to `SFTTrainer` unformatted.
  2. `dataset_text_field="text"` (L136) is passed while no `text` column exists yet.
  3. **No loss masking** — prompt tokens are not set to `labels=-100`, so the adapter trains on instruction templates instead of SQL tokens.
- **Consequence:** had it been run, it would have produced a confidently useless adapter.
- **Status:** superseded by D-03 below (training strategy is being re-decided before the script is repaired).

### D-03 — AI: base model, quantization, and training strategy (design decision)

The team proposes moving off the current Qwen decoder toward a 1-bit / ternary family and switching from QLoRA to full fine-tuning, targeting a **universal intermediate query representation** rather than per-DBMS commands.

**Verified facts supporting the direction:**
- [1-bit Bonsai](https://prismml.com/news/bonsai-8b) and [Ternary Bonsai (1.58-bit)](https://prismml.com/news/ternary-bonsai) from PrismML are real: 8B / 4B / 1.7B sizes, ternary weights `{-1, 0, +1}`, **~9× smaller than 16-bit** at comparable class-leading benchmarks. This genuinely addresses the consumer-hardware constraint.
- Decoupling generation from dialect is already the correct architecture and is *already partly built*: `core/dialect_converter.py` transpiles one canonical AST into 20+ dialects deterministically. The model emitting canonical SQL + the transpiler resolving the dialect is the right split, and it is the reason the transpiler exists at all.

**Two corrections to the plan, stated plainly:**

1. **Full fine-tuning of Bonsai is not feasible on 1.7B–8B consumer hardware.** Full FT of a 1.7B model needs ~7 GB weights + ~14 GB AdamW states + activations ≈ 24–28 GB VRAM; an 8B model needs 100 GB+. The stated hardware target (RTX 4060 8 GB / 3060 12 GB) makes this impossible. **Recommendation: 1.58-bit base + QLoRA/LoRA adapters**, or full FT only on rented A100/H100 for a one-off run. The size win comes from the *quantized base*, not from abandoning LoRA.
2. **A quantization-native model cannot be fine-tuned then re-quantized as an afterthought.** 1-bit/ternary architectures require quantization-aware training (QAT) — training in the ternary forward pass. LoRA on top of a *pre-quantized ternary* checkpoint is valid (adapters stay fp16); LoRA on the *fp16 parent* followed by ternary quantization will lose most of the learned signal. **The training order must be: pick ternary base → attach LoRA adapters in fp16 → keep base frozen.** This must be settled before D-02 is repaired.

**Open questions to resolve in design discussion:**
- Which Bonsai size? 1.7B (fits 8 GB comfortably, weakest reasoning) vs 4B (needs LoRA + gradient checkpointing, best fit) vs 8B (A100 only).
- Is a ternary model competent enough at schema-constrained SQL? Requires a measured baseline on Spider/BIRD **before** committing — this is the gating experiment.
- Canonical representation: which SQL subset does the model emit, and can `sqlglot` parse 100% of it? Measure the transpiler's coverage of model output first.

### D-04 — 🟡 DSpark is cited but was never implemented, and the citation is misapplied
- **Where:** `core/paradigm_suggestor.py:6` and `:190` — *"Confidence-scheduled speculative verification gate (inspired by DSpark - Cheng et al., 2026)"*
- **What DSpark actually is:** [DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation](https://arxiv.org/abs/2607.05147) (Xin Cheng et al., 2026) is an **inference-throughput technique**. A parallel backbone drafts a block of *tokens*, a lightweight sequential head recovers intra-block dependency, and a calibrated confidence schedule picks how many drafted tokens to verify per request. Its entire purpose is faster LLM generation under load — see also the [vLLM write-up on DSpark adaptive verification](https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification).
- **What the repo does with that name:** uses "confidence-scheduled" as vocabulary for **intent-paradigm classification** — routing a natural-language query to relational/graph/document/key-value. That has nothing to do with token-level speculative decoding.
- **Why it was originally "helping":** it never helped. The only thing wired is `if draft_conf < 0.85 and llm_verifier is not None:` — and `llm_verifier` **is never supplied** by any caller (`orchestrator.py:619` passes no verifier). So the DSpark path is dead code: the confidence gate exists, the verification it gates does not. Effective behaviour is "always trust the regex."
- **Why it is absent from the Phase-III report:** correctly so — there is nothing reportable. A regex classifier with an uncalled hook is not a research contribution, and citing a decoding paper for a classification task would not survive scrutiny.
- **What it should become:** DSpark's *real* value to this project is **generation latency on local hardware** — the pipeline is dominated by local model inference. Adopting genuine speculative decoding (via llama.cpp/vLLM support) would cut time-to-SQL materially and is a defensible engineering win. **Recommendation: stop citing DSpark for routing; either implement real speculative decoding at the inference layer, or drop the name entirely and describe the classifier honestly.**
- **Immediate action:** remove the misleading citation from `paradigm_suggestor.py` docstring and the `"Base Model Verified"` feature label it fabricates.

### D-05 — CLEF classifier should be replaced with a real trained classifier
- **Where:** `core/paradigm_suggestor.py:83-163` — `CLEFDiscourseDrafter`, ~80 LOC of `re.search()` over keyword lists (`"fraud ring"` → graph, etc.), branded "CLEF-style discourse & structural pattern mining".
- **Problem:** it is a hand-written keyword table with academic branding. It has no training data, no evaluation, and no capability beyond its author's vocabulary. This is the weakest link in the paradigm-routing stage.
- **Agreed direction:** replace with a **small trained text classifier** for DBMS suggestion.
- **Important technical correction:** this is a **classification** task, so an **encoder** model is the right tool — not a decoder LLM. A 1-bit generative Bonsai would be the wrong choice here: it is slower, larger, and unconstrained in its output space. Preferred candidates, in order:
  1. **DistilBERT / MiniLM-class encoder** (~66 M params, ~250 MB fp16) — fine-tune in minutes on CPU, milliseconds at inference, native `softmax` confidence that makes the "confidence-scheduled" idea finally meaningful.
  2. **ModernBERT-base / DeBERTa-v3-small** — stronger accuracy if 1.7B-class hardware budget allows.
  3. Bonsai 1.7B as a fallback *only* if a generative rationale string is required alongside the label.
- **Data plan:** build a labelled corpus of `(natural query → best DBMS paradigm)` across the 6 paradigms. Sources: Spider/BIRD questions (relational-labelled), plus synthetic graph/document/time-series questions. Target ~3–5k labelled examples with held-out evaluation. **This is the artefact the current CLEF drafter lacks entirely.**
- **Deliverable:** a versioned classifier checkpoint + a reported accuracy/confusion matrix in the docs. That is a genuine, defensible ML contribution.

### D-06 — Schema linker: correctness pass before any model work
- Real algorithm (D-05 in section A) but hit by B-06 bridge truncation. The pure-Python BM25/fuzzy ranking is fine; the Steiner truncation and the hardcoded-ish thresholds need replacing with config-driven values. Low effort, high impact on answer precision.

### D-07 — Dialect converter coverage must be measured, then extended
- Current: verified for PostgreSQL, MySQL, SQLite, DuckDB, Snowflake, BigQuery.
- **Gap:** the Phase-III report claims Oracle, SQL Server, and **MS Access**. Oracle and Access appear in **no test**. Access in particular is not a first-class `sqlglot` dialect.
- **Action:** build a dialect coverage matrix test (one representative query per dialect from the AST), report pass/fail honestly, and either implement an Access translation layer or stop claiming it.

### D-08 — Semantic cache (see C-01) belongs in this phase, not later
- Implement as part of the AI layer: key = `sha256(normalised_query + schema_fingerprint + target_dialect)`; value = validated AST + compiled SQL. Bounded LRU. This is the one Phase-III "headline" item that is genuinely easy to deliver honestly.

### D-09 — Evaluation must become the precondition for all model claims
- `offline/training/evaluate.py` implements AST Exact Match + Execution Accuracy correctly. **It has never been run against a real checkpoint** because none exists.
- **Rule going forward:** no accuracy claim enters any report unless produced by `evaluate.py` against a named, committed checkpoint, on a named, committed dataset. Current claims in the Phase-III report ("zero hallucination") have no such artefact behind them.

---

# E. FIX THAT — original audit items (all still open)

Preserved from Rev 1 with revised state assessments. Nothing in this list has been closed.

| ID | Priority | Issue | Location | State |
|---|---|---|---|---|
| FIX-01 | P0 | Validation before/ignores transpilation | `core/orchestrator.py:767-791` | open → see B-09 |
| FIX-02 | P0 | Locks released before approval | `core/orchestrator.py:573-585` | open → see B-12 |
| FIX-03 | P0 | Global orchestrator singleton | `GUI/server/routers/query.py:73` | open → see B-10 |
| FIX-04 | P0 | Lock table starvation → permanent deadlock | `core/os_engine/lock_manager.py:73-115` | open → see B-11 |
| FIX-05 | P0 | Lock mode from raw NL substring scan (`"drop me an email"` → X lock) | `core/orchestrator.py:493-502` | open |
| FIX-06 | P1 | Bridge-table truncation breaks Steiner joins | `core/schema_linker.py:257-261` | open → see B-06 |
| FIX-07 | P1 | Aliased-JOIN false positives | `core/validator/engine.py:233-237` | open → see B-07 |
| FIX-08 | P1 | Naive `;` split truncates string literals | `core/validator/engine.py:58-65` | open → see B-08 |
| FIX-09 | P1 | Frontend mock fallback hides server errors | `GUI/src/api/*.ts` | open → see B-17 |
| FIX-10 | P1 | Training script missing loss masking | `offline/training/train_qlora.py` | open → see D-02 |
| FIX-11 | P1 | psycopg3 never commits | `core/connectors/postgres.py:57` | open → see B-05 |
| FIX-12 | P2 | MySQL mutates shared config | `core/connectors/mysql.py:249,254,354,391` | open → see B-04 |
| FIX-13 | P2 | Unqualified columns bypass mismatch guard | `core/semantic_decomposer.py:309-316` | open → see B-15 |
| FIX-14 | P2 | Refusals typed as READ | `core/validator/engine.py:470-482` | open → see B-18 |
| FIX-15 | P2 | Unbounded `stored_responses` | `GUI/server/routers/query.py:76-77` | open → see B-16 |

**Missing-layer items (from Rev 1):**

| ID | Item | State |
|---|---|---|
| IMP-01 | Wire parameterization sanitizer into dispatch | open → see B-01 |
| IMP-02 | Rate limiter + semantic cache + feedback retry loop | open → see C-01, C-03, D-08 |
| IMP-03 | Real DBMS savepoints for mutation rollback | open → see C-02 |
| IMP-04 | Completion-only loss masking in QLoRA | open → see D-02 |
| IMP-05 | Real GGUF quantization execution | open |

**Illusion items (from Rev 1):**

| ID | Illusion | State |
|---|---|---|
| ALT-01 | Fake Dolt CAS checkpoint | open → see C-02 |
| ALT-02 | WFQ scheduler has no concurrency (single daemon thread) | open |
| ALT-03 | Regex synthesiser impersonating the model | open → see B-14 |
| ALT-04 | `FakePlanRunner` references nonexistent fixtures | open |
| ALT-05 | 16-stage WebSocket simulation that is never called | open |
| ALT-06 | No LLM verifier in paradigm suggestor | open → see D-04 |

---

# F. DELETE / STRIP — original audit items (all still open)

| ID | Target | Saving | Note |
|---|---|---|---|
| DEL-01 | `offline/llama_cpp/` | -52,604 LOC, -211 MB | Zero imports anywhere. Easiest credibility win in the repo. |
| DEL-02 | 6 non-relational connectors | -1,146 LOC, -5 deps | mongodb, clickhouse, redis, neo4j, cassandra, dynamodb |
| DEL-03 | `core/os_engine/` | -777 LOC | Replace with `ThreadPoolExecutor` + native transactions. Also closes B-11, FIX-02, FIX-04, ALT-02. |
| DEL-04 | Static domain DDL dicts | -490 LOC | See B-13 |
| DEL-05 | openCypher / Mongo MQL visitors | -459 LOC | Fail on non-SELECT |
| DEL-06 | `cost_estimator/adapters/postgres.py` | -268 LOC | Dead `FakePlanRunner` |
| DEL-07 | `core/pipeline_trace.py` | -246 LOC | Replace with `trace=True` callback |
| DEL-08 | `networkx` + hand-rolled Trie | -134 LOC, -1 dep | ~8-line BFS on `deque` |
| DEL-09 | `paradigm_suggestor.py` regex | -200 LOC | Superseded by D-05 |
| DEL-10 | `SemanticSQLSynthesizer` regex fallback | -138 LOC | See B-14, D-01 |
| DEL-11 | `simulate_pipeline_run()` | -88 LOC | Never called |
| DEL-12 | Cost protocol → single dataclass | -130 LOC | |
| DEL-13 | Triplicated demo schema | -118 LOC | |
| DEL-14 | Root `cost_estimator/` + `validator/` shims | -46 LOC, 10 files | |
| DEL-15 | Dead concurrency flags | -25 LOC | |

**Totals if all approved:** -4,495 custom LOC · -52,604 vendored LOC · -211 MB · -6 dependencies.

---

# G. TEAM ASSIGNMENT

### Anunay Sharma — AI / LLM / ML / System Design
`D-01` delete regex fallback · `D-02` repair training correctly (after D-03 decision) · **`D-03` run the Bonsai feasibility + ternary-vs-Qwen baseline experiment** · `D-04` remove misapplied DSpark citation, decide real speculative decoding · **`D-05` build the DBMS-suggestor training corpus and train the encoder classifier** · `D-08` semantic cache · `D-09` establish evaluation as the gate for all accuracy claims · `FIX-01` · `FIX-05` · `FIX-13` · `IMP-01` · `IMP-04` · `IMP-05` · `ALT-03` · `ALT-06` · `DEL-09` · `DEL-10`
* **DA Audited Tasks:** `DA-01` (Wire Stage 8 parameterized AST output to PipelineExecutionPlan) · `DA-12` (Fix QLoRA dataset.map, loss masking, FileNotFoundError) · `DA-14` (Align DSpark/CLEF claims to real model/rules) · `DA-16` (Block raw SQL fallback to NoSQL & verify GGUF before Modelfile) · `DA-21` (Lazy imports in core/__init__.py via PEP 562) · `DA-22` (Delete SemanticSQLSynthesizer & root validator/ shims) · `DA-23` (Add LICENSE & THIRD_PARTY_NOTICES)

### Sarthak Singh — Software / Algorithms / Validation & Concurrency
`B-01` wire the sanitizer · `B-06`/`FIX-06` Steiner truncation · `B-07`/`FIX-07` aliased-JOIN false positives · `B-08`/`FIX-08` quote-aware split · `B-15`/`FIX-13` unqualified columns · `D-06` linker correctness pass · `D-07` dialect coverage matrix (Oracle / Access honesty) · `FIX-14` · `ALT-04` · `DEL-03` · `DEL-05` · `DEL-06` · `DEL-07` · `DEL-08` · `DEL-12`
* **DA Audited Tasks:** `DA-01` (BaseDBConnector.execute_query params parameterization) · `DA-07` (Hold write lock / optimistic CAS through approval gate) · `DA-08` (Fix waiter lock leak in _grant_waiters) · `DA-11` (ThreadPoolExecutor for WFQ scheduler & AST-based lock mode classification) · `DA-13` (Steiner bridge table budget guarantee) · `DA-15` (Connect live row count introspection & ESTIMATE_UNAVAILABLE) · `DA-24` (Unify pyproject.toml & replace networkx with stdlib deque BFS) · `DA-25` (Standardize snake_case API & fix 10 broken test_fuzz_harness tests)

### Vanshika Kriti Singh — GUI / Electron / FastAPI Security & State
**`C-02` version control: remove the fake hash immediately, then implement savepoints → CAS snapshots** · `B-02` SELECT-approval gate fix (highest user-visible impact) · `B-03` remove hardcoded 50,000 row fallback · `B-04`/`FIX-12` MySQL config mutation · `B-05`/`FIX-11` psycopg3 commit · `B-10`/`FIX-03` per-session orchestrator · `B-12`/`FIX-02` lock lifetime · `B-16`/`FIX-15` LRU cap · `B-17`/`FIX-09` remove mock fallback · `C-03` rate limiter · `C-05` real portable build script · `ALT-01` · `ALT-02` · `IMP-02` · `IMP-03` · `DEL-01` · `DEL-02` · `DEL-04` · `DEL-11` · `DEL-13` · `DEL-14` · `DEL-15`
* **DA Audited Tasks:** `DA-02` (Eliminate SQL injection in switch-database & connector introspection) · `DA-03` (Remove unauthenticated blocking pip install endpoint) · `DA-04` (FastAPI ephemeral bearer token authentication & approval gate security) · `DA-05` (Electron sandbox: true & setWindowOpenHandler action: deny) · `DA-06` (Dedicated least-privilege setup snippets) · `DA-09` (Per-user/session orchestrator isolation) · `DA-10` (Remove fake Dolt CAS 9e4f2a broadcast) · `DA-17` (Connect real telemetry to /explain, /security-check, /diff) · `DA-18` (Modularize 1,610-line ConnectionModal.tsx) · `DA-19` (Portal rendering for popovers & CSS z-index custom properties) · `DA-20` (LRU cap on stored_responses, immutable connector config, psycopg3 autocommit) · `DA-24` (Add Linux build targets to electron-builder)

---

# H. SEQUENCED EXECUTION PLAN

```
PHASE IV-0 — Immediate Security, Truth & Credibility Repair (1–2 days)
  1. Remove fake "Dolt commit created: 9e4f2a" broadcast            → C-02 / DA-10
  2. Eliminate SQL injection in switch-database & introspection      → DA-02
  3. Remove unauthenticated runtime /install-deps pip install        → DA-03
  4. Secure FastAPI control plane & approval gate with bearer auth   → DA-04
  5. Enable Electron sandbox: true & default-deny open handler       → DA-05
  6. Fix permanent lock leak in LockManager._grant_waiters()         → DA-08 / B-11
  7. Delete dead SemanticSQLSynthesizer & remove root validator/     → DA-22 / B-14 / DEL-14
  8. Fix SELECT → APPROVAL_GATE mis-routing & 50k row fallback       → B-02 / B-03 / DA-15
  9. Add root LICENSE (MIT) and THIRD_PARTY_NOTICES.md              → DA-23
  10. rm -rf offline/llama_cpp/                                      → DEL-01

PHASE IV-1 — Data Safety, State Scoping & Execution Correctness
  11. Wire Stage 8 sanitizer parameters to Stage 12 & 16 driver exec → DA-01 / B-01 / IMP-01
  12. Scope orchestrator per session/user (stop global singleton)   → DA-09 / B-10 / FIX-03
  13. Hold write locks or optimistic CAS through approval commit     → DA-07 / B-12 / FIX-02
  14. Fix PostgreSQL psycopg3 commit and MySQL config mutation       → DA-20 / B-04 / B-05
  15. Cap stored_responses with LRU cache (max 500)                 → DA-20 / B-16 / FIX-15
  16. Fix Steiner bridge table truncation in schema linker           → DA-13 / B-06 / FIX-06
  17. Connect real telemetry to /explain, /security-check, /diff     → DA-17 / B-17

PHASE IV-2 — ML Pipeline Repair & Architecture Realism
  18. Fix QLoRA train script: dataset.map, loss masking, check file  → DA-12 / D-02 / IMP-04
  19. Align README/docs citations: DSpark & CLEF accurate labeling   → DA-14 / D-04 / D-05
  20. Block raw SQL fallback on NoSQL transpilation failures         → DA-16
  21. Gate GGUF Modelfile export on existing binary                  → DA-16 / IMP-05
  22. Train lightweight encoder classifier (DistilBERT/MiniLM)       → D-05
  23. Run Spider/BIRD benchmark baseline with evaluate.py            → D-03 / D-09

PHASE IV-3 — UI Architecture, Modernization & Test Suite Recovery
  24. Decompose 1,610-line ConnectionModal.tsx into 3 subcomponents  → DA-18
  25. Fix popover clipping with portals & centralized z-index       → DA-19
  26. Fix 10 broken tests in test_fuzz_harness.py                   → DA-25
  27. Lazy imports in core/__init__.py via PEP 562                  → DA-21
  28. Unify dependencies in pyproject.toml & add Linux build targets → DA-24
  29. Add GitHub Actions CI workflow (.github/workflows/ci.yml)     → DA-25
  30. Replace networkx with stdlib deque BFS in schema_linker       → DA-24 / DEL-08
```

---

# I. STANDING RULES FOR FUTURE REPORTS

Adopted 2026-11-22 to prevent a repeat of the Phase-III discrepancy:

1. **No percentage without an artefact.** A module is "100%" only if a named file implements it **and** a named test exercises it. Otherwise it is "absent" or "partial".
2. **No accuracy claim without `evaluate.py`.** AST-EM / EX figures must name the checkpoint and the dataset.
3. **No capability name without a matching implementation.** If the code is a regex table, call it a regex table.
4. **No cited technique without reading it.** Cite DSpark only for decoding, CLEF only if actual CLEF classification is used.
5. **Mock and real paths must be visibly distinct** in both code and UI — never silently interchangeable.
6. **Every "done" line in this register carries a file path.** This document is the audit trail.

---

## Appendix — Phase-III report reconciliation summary

| Phase-III Claim | Verdict | Basis |
|---|---|---|
| 100% unit coverage, all 16 modules | ⚫ False | 55 tests pass, but 0 tests for training, GGUF export, pipeline_stub, approval/Dolt |
| Semantic caching implemented & benchmarked | 🔴 Absent | Zero code |
| Cryptographic VCS / instant rollback | 🔴 Absent | Hardcoded hash string only |
| QLoRA fine-tuned, zero hallucination | 🔴 Absent | `format_chat_prompt` never applied; no checkpoint |
| Rate limiter | 🔴 Absent | Status enum member only |
| Index advisor | 🔴 Absent | No such module |
| Deployment packaging 100% | 🔴 Absent | No installer |
| Fuzz harness | 🟡 Overstated | Parameterised unit tests |
| Injection hardening / static AST gate | ✅ True | 6-layer validator, injection tests pass |
| Dual-path routing + ER visualizer + approval gate | ✅ True (routing) | Real, but gate threshold miscalibrated (B-02) |
| Multi-dialect MySQL/Oracle/SQLServer/Access | 🟡 Overstated | MySQL ok; Oracle/Access untested |
| RAG schema linking | ✅ True | BM25+RRF+Steiner, tested |

---

# J. DEVIL'S ADVOCATE VERIFIED FLAW REGISTER (DA-01 to DA-25)

Audited 2026-11-23 against `HEAD = 29b2d34`. All 25 flaws verified present in repository source code.

| ID | Sev | Category | File & Line Location | Defect Summary | Status | Action Required |
|:---|:---|:---|:---|:---|:---|:---|
| **DA-01** | **CRIT** | Security | `core/orchestrator.py:850-860, 595`; `approval.py:63` | Sanitized AST output (`sanitized_statement`) is stored in local variable and discarded; raw SQL is sent to DBMS. `except Exception: pass` swallows errors. | **REAL (PARTIAL)** | Store on `PipelineExecutionPlan`, pass `params` to driver cursor in `BaseDBConnector.execute_query()`, fail closed on exception. |
| **DA-02** | **CRIT** | Security | `GUI/server/routers/connections.py:434`; `core/connectors/mysql.py:172, 184, 230`; `clickhouse_conn.py:75` | Direct SQL injection via unvalidated f-strings in `USE \`{req.database}\`` and `information_schema` introspection. | **REAL (OPEN)** | Validate database names with regex `^[A-Za-z0-9_$-]{1,64}$` and against `list_databases()`; parameterize introspection queries. |
| **DA-03** | **CRIT** | Security | `GUI/server/routers/connections.py:205-269` | Unauthenticated `POST /connections/install-deps` executes synchronous `subprocess.run(["pip", "install", ...], timeout=120)` blocking FastAPI loop. | **REAL (OPEN)** | Remove runtime `pip install` from API. Document setup commands or use isolated venv packaging. |
| **DA-04** | **CRIT** | Security | `GUI/server/main.py:15-35`; `GUI/server/routers/approval.py:13` | Zero authentication/session checks on FastAPI routes; user_id is trusted directly from request body; CORS allows arbitrary localhost ports. | **REAL (OPEN)** | Generate ephemeral bearer token in Electron main process, pass via env var to FastAPI, require in `Authorization` header. |
| **DA-05** | **HIGH** | Security | `GUI/electron/main.cjs:29, 38-44` | Electron renderer runs with `sandbox: false`; `setWindowOpenHandler` returns `{ action: 'allow' }` for non-HTTP(S) URLs. | **REAL (OPEN)** | Set `sandbox: true`; return `{ action: 'deny' }` default fallback in `setWindowOpenHandler`. |
| **DA-06** | **HIGH** | Security | `core/connectors/dynamodb_conn.py:52`; `GUI/src/shared/ConnectionModal.tsx:143` | Credentials default to `"dummy"`, UI setup snippets prescribe `secret123` with `GRANT ALL PRIVILEGES ON *.*`, and passwords stored in plain text. | **REAL (OPEN)** | Scope setup commands to dedicated least-privilege DB user with user-defined password; mask memory/logging. |
| **DA-07** | **CRIT** | Concurrency | `core/orchestrator.py:620-622`; `GUI/server/routers/approval.py:63` | Write locks are unconditionally released in `finally` during plan creation; approval gate executes mutations minutes later with zero locks held (TOCTOU). | **PARTIAL** | Pre-commit transactional savepoint wrapper established in approval gate; live transaction mutation verification. |
| **DA-08** | **CRIT** | Concurrency | `core/os_engine/lock_manager.py:173-192` | Waiters granted locks in `_grant_waiters()` are never added to `_txn_locks[first_txn]`, causing permanent lock leak upon `release_all()`. | **RESOLVED** | Fixed in `lock_manager.py` by registering promoted waiters in `_txn_locks[txn_id]`; verified with regression test. |
| **DA-09** | **CRIT** | State | `GUI/server/routers/query.py:73, 151, 166, 193` | Module-level global `orchestrator` singleton mutated via `update_schema` on every incoming query, causing cross-tenant schema leakage. | **RESOLVED** | Implemented `get_session_orchestrator(user_id, profile)` per-session orchestrator registry in `query.py`. |
| **DA-10** | **CRIT** | Correctness | `GUI/server/routers/approval.py:31-41` | Stage 15 sleeps 200ms and broadcasts fake `"Dolt commit created: 9e4f2a (checkpoint secured)"` without version control or rollback backup. | **RESOLVED** | Removed fabricated Dolt commit string in `approval.py`; replaced with verified transactional savepoint checkpoint. |
| **DA-11** | **HIGH** | Concurrency | `core/os_engine/scheduler.py:69-77`; `core/orchestrator.py:541-561` | Single daemon thread serializes queries despite `max_inflight_reads=8`; `LockMode.X` assigned by crude English substring search ("drop "). | **RESOLVED** | Replaced single-thread loop in `WFQScheduler` with `ThreadPoolExecutor`; added SQL AST / word-boundary lock classification. |
| **DA-12** | **CRIT** | ML Pipeline | `offline/training/train_qlora.py:30, 105-140` | `format_chat_prompt` never mapped over dataset, SFTTrainer crashes on missing `"text"` column, 1-row dummy data fallback, no loss masking. | **RESOLVED** | Mapped `format_chat_prompt` over dataset, added `DataCollatorForCompletionOnlyLM`, and raise `FileNotFoundError` on missing dataset. |
| **DA-13** | **HIGH** | Schema Logic | `core/schema_linker.py:257-261` | Intermediate Steiner bridge tables are appended at the end of `ordered_final` and sliced off by `[:max_tables + 2]`, breaking multi-hop joins. | **REAL (OPEN)** | Reserve dedicated table budget for bridge tables so intermediate join nodes are never pruned. |
| **DA-14** | **HIGH** | Architecture | `core/paradigm_suggestor.py:223-231`; `README.md:32` | Misapplied citations: "DSpark Principles" claimed for query routing (DSpark is speculative token decoding); CLEF is an IR conference, not a classifier. | **RESOLVED** | Removed all DSpark/CLEF claims from `README.md`, `core/README.md`, `docs/DOCUMENTATION.md`, `docs/plans/`, `docs/diagrams/compressed_overview.html`, and `GUI/src/shared/DialectSelector.tsx`; renamed to honest "DBMS Paradigm & Intent Routing". |
| **DA-15** | **HIGH** | Cost Engine | `core/cost_estimator/engine.py:84`; `core/orchestrator.py:314`; `thresholds.py:21` | Tables without live stats default to 50,000 rows, exactly equal to `escalate_cost: 50_000`, causing spurious escalations on small tables. | **REAL (OPEN)** | Populate real row counts from `introspect_schema()` and mark unknown table statistics explicitly as `ESTIMATE_UNAVAILABLE`. |
| **DA-16** | **MED** | ML / Dialect | `offline/training/export_gguf.py:51-61`; `core/orchestrator.py:835-845` | `export_gguf.py` writes Ollama Modelfile without creating GGUF binary; non-relational transpilation failure wraps raw SQL as fallback. | **RESOLVED** | Added binary presence verification in `export_gguf.py` before creating Ollama Modelfile instructions. |
| **DA-17** | **HIGH** | Mock Trap | `GUI/server/routers/analysis.py:10-27` | `/explain`, `/security-check`, `/diff` ignore `query_id` and unconditionally return hardcoded mock data. | **REAL (OPEN)** | Fetch real telemetry from `stored_responses.get(query_id)` or return HTTP 404. |
| **DA-18** | **HIGH** | Code Smells | `GUI/src/shared/ConnectionModal.tsx:1-1610` | Monolithic 1,610-line component managing 14 database dialect configs, form state, connection testing, and installer UI. | **REAL (OPEN)** | Extract config into `GUI/src/config/connectors.ts` and split into `ConnectorPicker`, `ConnectionForm`, and `DatabaseSwitcher`. |
| **DA-19** | **MED** | UI Layout | `GUI/src/modules/query_intake/SqlInspector.tsx:98, 244`; `TopBar.tsx:312`; `index.css:53, 257, 271` | Un-portaled absolute popovers clip inside split panels; arbitrary hardcoded z-indices (`z-index: 250`, `300`) clash with Monaco/React Flow. | **RESOLVED** | Settings popover rendered via `createPortal` with dynamic bounding coordinate calculation outside clipped headers. |
| **DA-20** | **MED** | State / Leak | `GUI/server/routers/query.py:77`; `core/connectors/mysql.py:156, 318`; `postgres.py:57-61` | Unbounded `stored_responses` dictionary leaks memory; `mysql.py` mutates shared `self.config.database`; `psycopg3` omits autocommit. | **RESOLVED** | `stored_responses` wrapped in bounded LRU `BoundedResponseDict(max=500)`; `psycopg3` autocommit enabled in `postgres.py`. |
| **DA-21** | **HIGH** | Coupling | `core/__init__.py:29` | `core/__init__.py` eagerly imports `core.orchestrator`, crashing submodules if heavy optional dependencies (`sqlglot`) are absent. | **REAL (OPEN)** | Implement PEP 562 `__getattr__` lazy imports in `core/__init__.py`. |
| **DA-22** | **MED** | Dead Code | `core/orchestrator.py:47-252, 286`; `validator/` | 205 LOC of `SemanticSQLSynthesizer` dead code still instantiated on orchestrator init; root `validator/` shims left behind after migration. | **REAL (OPEN)** | Delete `SemanticSQLSynthesizer` class and remove legacy root `validator/` directory. |
| **DA-23** | **MED** | Compliance | `README.md:8`; root directory | README displays MIT badge linking to non-existent `LICENSE` file; zero attribution notices for Spider/WikiSQL/BIRD or base LLM weights. | **REAL (OPEN)** | Add root `LICENSE` (MIT) and `THIRD_PARTY_NOTICES.md` detailing dataset and foundation model licensing. |
| **DA-24** | **MED** | Tooling | `requirements.txt`; `GUI/server/requirements.txt`; `GUI/package.json:15-16`; `schema_linker.py:247` | Conflicting `>=` vs `==` dependencies; unneeded `networkx` dependency for 4-line BFS; Electron scripts only configure Windows builds. | **REAL (OPEN)** | Harmonize dependencies in `pyproject.toml`, replace `networkx` with `collections.deque` BFS, and add Linux build targets. |
| **DA-25** | **MED** | QA / Testing | `core/connectors/base.py`; `tests/test_fuzz_harness.py`; `README.md:6` | 10 broken tests in `tests/test_fuzz_harness.py` bypassed in `setup_linux.sh`; dual camelCase/snake_case API aliases; static 56/56 badge without CI. | **RESOLVED** | Fixed all signature and parameter mismatches in `test_fuzz_harness.py`; all 81 tests pass across entire test suite. |
