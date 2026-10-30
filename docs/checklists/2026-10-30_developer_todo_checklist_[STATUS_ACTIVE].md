# Developer Action Plan & Implementation Checklist: NL2SQL Production Hardening

**Document Name:** `2026-10-30_developer_todo_checklist_[STATUS_ACTIVE].md`  
**Created:** 2026-10-30  
**Source Baseline:** Adversarial Audit & Ponytail Review (`docs/reviews/2026-10-29_adversarial_and_ponytail_audit_[STATUS_OPEN].md`)  
**Status:** **ACTIVE / PENDING IMPLEMENTATION**  
**Estimated Savings:** -4,495 custom Python LOC, -52,604 vendored LOC (-211 MB disk footprint), -6 external dependencies, 29 critical/major flaws remediated  

---

## Quick Reference Summary

| Category | Item Count | Core Goal | Primary Files Impacted |
|---|---|---|---|
| **1. Fix That** | 15 Tasks | Critical bug fixes, race conditions, lock leaks, inverted execution order | `core/orchestrator.py`, `core/os_engine/`, `core/validator/engine.py`, `GUI/server/routers/` |
| **2. Implement This** | 5 Tasks | Build missing reliability, security, and transaction rollback layers | `core/sanitizer.py`, `core/orchestrator.py`, `GUI/server/routers/approval.py` |
| **3. There is No This, Must Find Alternative** | 6 Tasks | Replace architectural illusions and fake stubs with real systems | `GUI/server/routers/approval.py` (Dolt), `core/os_engine/` (WFQ), `core/cost_estimator/` |
| **4. Delete / Strip This (Bloat)** | 15 Tasks | Eliminate over-engineering, dead vendored code, speculative connectors | `offline/llama_cpp/`, `core/connectors/`, `core/semantic_decomposer.py`, `cost_estimator/` |

---

## 1. "Fix That" (Critical Bugs, Broken Ordering & Concurrency Leaks)

### [ ] FIX-01 — Inverted Validation Ordering: Validate AFTER Transpilation, Not Before
- **Priority:** **P0 (Critical Blocker)**
- **Where:** `core/orchestrator.py:767-791`
- **What's Broken:** Stage 7 transpiles PostgreSQL SQL to target dialect (e.g., Snowflake, BigQuery, SQLite, Mongo), but Stage 9 validates the *original* PostgreSQL AST. Dialect-specific syntax errors reach production DBMSs unvalidated. Furthermore, when transpilation throws an exception (L772-780), raw PostgreSQL SQL is forwarded to non-Postgres engines!
- **Concrete Fix:**
  1. Move Stage 9 validation to execute *after* dialect transpilation on the transpiled query.
  2. If target is relational SQL, validate using `sqlglot.parse_one(transpiled_sql, read=target_dialect)`.
  3. If transpilation raises `DialectFeatureUnsupportedError`, fail immediately with a typed error; NEVER forward raw PostgreSQL SQL.

---

### [ ] FIX-02 — Premature Lock Release: Writes Executing Unlocked After Approval
- **Priority:** **P0 (Critical Blocker)**
- **Where:** `core/orchestrator.py:573-585` & `GUI/server/routers/approval.py:44-86`
- **What's Broken:** `orchestrator.execute_pipeline()` releases all locks and increments the MVCC write version in its `finally` block during plan creation — *before* human approval is given. When human later approves in `approval.py`, the query executes against production DBMS completely outside the lock protocol and scheduler!
- **Concrete Fix:**
  1. For mutating queries (`StatementType.WRITE` / `DDL`), keep the transaction intent in a `PENDING_APPROVAL` state without releasing locks or incrementing MVCC write counters.
  2. Inside `GUI/server/routers/approval.py`, acquire the target database transaction and lock *inside the approval handler* immediately before dispatching execution.
  3. If user rejects approval, rollback and discard cleanly without advancing commit counters.

---

### [ ] FIX-03 — Global Orchestrator Singleton: Multi-Tenant Schema Corruption
- **Priority:** **P0 (Critical Blocker)**
- **Where:** `GUI/server/routers/query.py:73, 185-209, 218-245`
- **What's Broken:** `orchestrator = EndToEndNL2SQLOrchestrator(DEFAULT_SCHEMA)` is instantiated as a module-level global singleton. When User A updates schema via `/api/query/schema/upload` or switches database context, `orchestrator.update_schema()` overwrites the schema globally for all concurrent users!
- **Concrete Fix:**
  1. Remove global `orchestrator` singleton.
  2. Scope orchestrator instances per user session (e.g. `session_id -> orchestrator` registry with LRU eviction) or pass `SchemaMetadata` as a request-scoped parameter into `execute_pipeline(query, schema=...)`.

---

### [ ] FIX-04 — Permanent Lock Table Starvation upon Contention
- **Priority:** **P0 (Critical Blocker)**
- **Where:** `core/os_engine/lock_manager.py:73-115, 136-163, 173-192`
- **What's Broken:** When a lock is granted to queued waiters in `_grant_waiters()`, it forgets to record the granted resource in `_txn_locks[txn_id]`. When transaction settlements run `release_all()`, it pops an empty set, leaving the resource permanently locked in `_resource_locks`. Any contention event deadlocks the server permanently. Waiters also enqueue duplicate entries on each retry loop.
- **Concrete Fix:**
  1. In `_grant_waiters()`, record `self._txn_locks[waiter.txn_id].add(resource)` when granting locks.
  2. Deduplicate waiter queues before re-enqueuing.
  3. *(Recommended Ponytail Alternative)*: Deprecate `core/os_engine/` entirely and use native database transactions (`BEGIN`, `COMMIT`, `SAVEPOINT`).

---

### [ ] FIX-05 — Lock Mode Scanning Raw Natural Language Substrings
- **Priority:** **P0 (Critical Blocker)**
- **Where:** `core/orchestrator.py:493-502`
- **What's Broken:** Lock mode (SHARED vs EXCLUSIVE) is determined by scanning raw NL text substrings (`"insert"`, `"update"`, `"delete"`, `"drop"`). Conversational queries like `"drop me an email with employee salaries"` trigger exclusive table write locks!
- **Concrete Fix:**
  1. Determine lock mode strictly from validated AST statement type (`exp.Select` -> Shared, `exp.Insert/Update/Delete/Create/Drop` -> Exclusive) *after* parsing and validation.

---

### [ ] FIX-06 — Arbitrary Bridge Table Truncation Breaking Steiner Tree Joins
- **Priority:** **P1 (Major Risk)**
- **Where:** `core/schema_linker.py:257-261`
- **What's Broken:** `final_tables = ordered_final[:max_tables + 2]` truncates table lists by arbitrary slice length, often dropping bridge tables at the tail of the Steiner path that are strictly required to complete foreign key joins.
- **Concrete Fix:**
  1. Prune candidate non-bridge tables before Steiner path expansion.
  2. Never truncate tables that form intermediate nodes in shortest FK join paths.

---

### [ ] FIX-07 — Layer 3 Validator False Positives on Aliased JOIN Queries
- **Priority:** **P1 (Major Risk)**
- **Where:** `core/validator/engine.py:233-237, 272-287`
- **What's Broken:** Both alias (e.g. `o`) and table name (`orders`) are inserted into `all_known_cols`. Unqualified columns in JOIN queries match 2+ entries and trigger `SCHEMA_03: Ambiguous column` error falsely on perfectly valid SQL.
- **Concrete Fix:**
  1. Deduplicate `all_known_cols` by physical table identity; do not count aliases as duplicate table references.

---

### [ ] FIX-08 — Naive Semicolon Splitting Truncating String Literals
- **Priority:** **P1 (Major Risk)**
- **Where:** `core/validator/engine.py:58-65` & `core/sanitizer.py:146`
- **What's Broken:** Raw `stripped.split(";")` truncates queries with semicolons in string values (e.g. `WHERE message = 'error; retry'`), rejecting valid queries as multi-statement attacks.
- **Concrete Fix:**
  1. Replace raw `split(";")` with `split_sql_script()` from `core/sanitizer.py:32-137`, which is quote-, escape-, and comment-aware.

---

### [ ] FIX-09 — Silent Frontend Fallback Masking Server Failures
- **Priority:** **P1 (Major Risk)**
- **Where:** `GUI/src/api/approvalApi.ts:12-14` & `GUI/src/api/queryApi.ts:16-33`
- **What's Broken:** HTTP failures and server 500 errors silently trigger `mockService.ts`, hiding backend crashes from developers and operators.
- **Concrete Fix:**
  1. Remove mock service fallbacks in non-development builds.
  2. Surface explicit toast/banner error notifications with HTTP status and server error message.

---

### [ ] FIX-10 — Fine-Tuning Script Missing Loss Masking & Chat Formatting
- **Priority:** **P1 (Major Risk)**
- **Where:** `offline/training/train_qlora.py:30-46, 132-140`
- **What's Broken:** `format_chat_prompt` is defined but never mapped over dataset; `dataset_text_field="text"` key is missing; prompt tokens are not masked (`labels=-100`), causing adapter to overfit on prompt templates rather than SQL AST output.
- **Concrete Fix:**
  1. Map `format_chat_prompt` over HuggingFace dataset before training.
  2. Implement `DataCollatorForCompletionOnlyLM` to mask prompt instruction tokens so loss is computed solely on generated SQL tokens.

---

### [ ] FIX-11 — PostgreSQL Connector Leaving psycopg v3 in Manual Commit
- **Priority:** **P1 (Major Risk)**
- **Where:** `core/connectors/postgres.py:57-61`
- **What's Broken:** Sets autocommit only for psycopg2; psycopg v3 stays in manual commit mode without ever calling `self._conn.commit()`. Mutating queries silently rollback on connection close.
- **Concrete Fix:**
  1. Call `self._conn.commit()` after mutating query execution for psycopg v3 connections.

---

### [ ] FIX-12 — MySQL Connector Mutating Shared Config State In-Place
- **Priority:** **P2 (Minor Issue)**
- **Where:** `core/connectors/mysql.py:249, 254`
- **What's Broken:** Mutates `self.config.database` in-place when processing `USE <db>` or `CREATE DATABASE`, corrupting connection config for subsequent queries.
- **Concrete Fix:**
  1. Store active database as an ephemeral connection state property instead of mutating `self.config`.

---

### [ ] FIX-13 — Schema Mismatch Guard Bypassing Unqualified Columns
- **Priority:** **P2 (Minor Issue)**
- **Where:** `core/semantic_decomposer.py:309-316`
- **What's Broken:** Column existence check is skipped when `col.table` is None. Hallucinated unqualified columns slip past the guard.
- **Concrete Fix:**
  1. Resolve unqualified columns against all tables referenced in the query; raise error if column exists in none.

---

### [ ] FIX-14 — Refusal Comments Validated as READ Statements
- **Priority:** **P2 (Minor Issue)**
- **Where:** `core/validator/engine.py:470-482`
- **What's Broken:** Returns `Status.VALID, StatementType.READ` for `-- REFUSAL:` comment strings.
- **Concrete Fix:**
  1. Add dedicated `StatementType.REFUSAL` enum; handle refusals without executing read logic.

---

### [ ] FIX-15 — Unbounded In-Memory Response Cache Memory Leak
- **Priority:** **P2 (Minor Issue)**
- **Where:** `GUI/server/routers/query.py:76-77`
- **What's Broken:** `stored_responses = {}` dictionary grows unbounded with every user query, causing memory leaks over long server uptime.
- **Concrete Fix:**
  1. Replace with `collections.OrderedDict` or `cachetools.LRUCache(maxsize=100)`.

---

## 2. "There is No This, Must Find an Alternative" (Illusions & Mock Stubs)

### [ ] ALT-01 — There is No Dolt CAS Checkpoint (Stage 15)
- **Where:** `GUI/server/routers/approval.py:31-41` & `docs/NL2SQL-Pipeline-Architecture.md` Stage 15
- **Reality:** Broadcasts `"Dolt commit created: 9e4f2a (checkpoint secured)"` with a hardcoded hash. There is zero Dolt binary, no CAS git tree, and no rollback engine.
- **Alternative:**
  - Remove all fake Dolt claims from documentation and UI.
  - Implement real relational savepoints: `SAVEPOINT nl2sql_approval;` before mutation execution, and `ROLLBACK TO SAVEPOINT nl2sql_approval;` if approval is revoked or execution fails.

---

### [ ] ALT-02 — There is No Concurrency in WFQScheduler (Stage 11)
- **Where:** `core/os_engine/scheduler.py:77, 170-199`
- **Reality:** Instantiated with a single daemon thread running a sequential while loop. `max_inflight_reads=8` is impossible to reach; all queries are serialized.
- **Alternative:**
  - Delete `core/os_engine/scheduler.py`.
  - Use Python standard library `concurrent.futures.ThreadPoolExecutor(max_workers=8)` or FastAPI's native async worker thread pool.
  - Let the underlying DBMS connection pool handle transaction concurrency.

---

### [ ] ALT-03 — There is No Neural Model Generation in SemanticSQLSynthesizer Fallback
- **Where:** `core/orchestrator.py:46-183` & `core/pipeline_trace.py:121-140`
- **Reality:** When Ollama/local model daemon is unattached, synthesis silently uses hardcoded regex keywords (`"salary"` -> `AVG(salary)`, `"top"` -> `ORDER BY total_amount DESC`). Telemetry reports "Qwen2.5-Coder + LoRA" while executing deterministic regex heuristics.
- **Alternative:**
  - Remove regex keyword synthesizer completely.
  - When model daemon is unavailable, fail fast and loudly: `raise ModelInferenceUnavailableError("Ollama/local model daemon is offline at http://localhost:11434")`.
  - For offline unit testing, inject explicit mock SQL strings into the test fixtures.

---

### [ ] ALT-04 — There are No EXPLAIN JSON Test Fixtures
- **Where:** `core/cost_estimator/adapters/postgres.py:23-62`
- **Reality:** `FakePlanRunner` hashes SQL strings to look for files in `tests/fixtures/explain_json/postgres/`. That directory does not exist in the repository!
- **Alternative:**
  - Delete `core/cost_estimator/adapters/postgres.py`.
  - `HeuristicCostEngine` in `core/cost_estimator/engine.py` already evaluates AST cost metrics and blast radius without needing uncreated fixture files.

---

### [ ] ALT-05 — There is No 16-Stage WebSocket Pipeline Simulation
- **Where:** `GUI/server/services/pipeline_stub.py:49-136`
- **Reality:** `simulate_pipeline_run()` loops through stages 1 to 16, sleeping 0.2s at each stage emitting fake WebSocket status events. It is imported in `query.py:12` but never called.
- **Alternative:**
  - Delete `simulate_pipeline_run()`.
  - Hook WebSocket event broadcasting directly into real `EndToEndNL2SQLOrchestrator` stage completion callbacks.

---

### [ ] ALT-06 — There is No LLM Verifier in Paradigm Suggestor
- **Where:** `core/paradigm_suggestor.py:179` & `core/orchestrator.py:619`
- **Reality:** Documents claim a "DSpark confidence-scheduled LLM verification gate", but `llm_verifier=` is never supplied. It is 220 lines of keyword regexes on words like `"fraud ring"`.
- **Alternative:**
  - Delete `core/paradigm_suggestor.py`.
  - Replace with a 20-line dictionary mapping target connection type directly to dialect.

---

## 3. "Implement This" (Missing Reliability, Sanitization & Rollback Layers)

### [ ] IMP-01 — Wire Query Parameterization Sanitizer into Pipeline
- **Where:** `core/sanitizer.py:168-212` & `core/orchestrator.py`
- **What's Missing:** `sanitizeAndExtractParametersFromSqlAst()` is fully implemented in `core/sanitizer.py`, but `core/orchestrator.py` never calls it. Raw interpolated SQL queries are dispatched to database connectors, creating injection exposure.
- **Implementation Steps:**
  1. Call `sanitizeAndExtractParametersFromSqlAst(ast)` in Stage 7 before dispatch.
  2. Pass extracted parameters dictionary/tuple to `connector.execute_query(sql, params)`.

---

### [ ] IMP-02 — Implement Missing Production Reliability Layers (Cache, Rate Limiter, Retry Loop)
- **Where:** `core/orchestrator.py` (promised in `docs/NL2SQL-Pipeline-Architecture.md:87-94`)
- **What's Missing:** Stages 2 (Rate Limiter), 4 (Semantic Cache), and the feedback retry loop are absent. Pipeline terminates at `BLOCKED` on first error.
- **Implementation Steps:**
  1. **Rate Limiter:** Add token-bucket or fixed-window rate limiter in `GUI/server/routers/query.py` per client IP / API key.
  2. **Cache:** Add in-memory LRU or Redis semantic query cache before Stage 6 generation.
  3. **Feedback Retry Loop:** When Stage 9 validation fails, append `validation_res.issues` to LLM prompt context and retry synthesis up to 2 times before rejecting.

---

### [ ] IMP-03 — Implement True Database Transaction Savepoints for Mutation Rollback
- **Where:** `GUI/server/routers/approval.py:44-86` & `core/connectors/base.py`
- **What's Missing:** Real checkpoint rollback mechanism for human-approved mutating writes.
- **Implementation Steps:**
  1. Add `begin_transaction()`, `create_savepoint(name)`, and `rollback_to_savepoint(name)` to `BaseDBConnector`.
  2. When executing mutating queries via approval gate, open transaction and create savepoint before execution.

---

### [ ] IMP-04 — Implement Real Loss Masking in QLoRA Training Pipeline
- **Where:** `offline/training/train_qlora.py`
- **What's Missing:** SQL token completion-only loss masking.
- **Implementation Steps:**
  1. Use HuggingFace TRL `DataCollatorForCompletionOnlyLM(response_template="<|im_start|>assistant\n", tokenizer=tokenizer)`.
  2. Ensure prompt tokens are masked with `labels = -100`.

---

### [ ] IMP-05 — Implement GGUF Quantization Prerequisite Checks
- **Where:** `offline/training/export_gguf.py`
- **What's Missing:** Real GGUF quantization execution.
- **Implementation Steps:**
  1. Check for `llama-quantize` or use `llama-cpp-python` API to produce `.gguf` files instead of printing shell text instructions.

---

## 4. "Delete / Strip This" (Bloat & Over-Engineering Elimination)

### [ ] DEL-01 — Delete Vendored `offline/llama_cpp/` (-52,604 LOC, -211 MB disk)
- **Where:** `offline/llama_cpp/`
- **Why:** Entire upstream C++ and Svelte UI tree vendored directly. Zero imports exist anywhere in `core/`, `GUI/`, or `tests/`.
- **Command:** `rm -rf offline/llama_cpp/`

---

### [ ] DEL-02 — Delete 6 Speculative Non-Relational Connectors (-1,146 LOC, -5 deps)
- **Where:** `core/connectors/`
  - `mongodb_conn.py` (261 LOC)
  - `clickhouse_conn.py` (199 LOC)
  - `redis_conn.py` (178 LOC)
  - `neo4j_conn.py` (176 LOC)
  - `cassandra_conn.py` (167 LOC)
  - `dynamodb_conn.py` (165 LOC)
- **Why:** NL2SQL is for relational SQL. These non-relational connectors fail on mutations and require uninstalled cloud drivers (`boto3`, `cassandra-driver`, `redis`, `neo4j`, `pymongo`).
- **Action:** Delete files; keep relational connectors (`postgres.py`, `mysql.py`, `sqlite.py`, `duckdb_conn.py`).

---

### [ ] DEL-03 — Delete User-Space OS Concurrency Engine (-777 LOC)
- **Where:** `core/os_engine/`
  - `scheduler.py` (201 LOC)
  - `lock_manager.py` (194 LOC)
  - `deadlock.py` (174 LOC)
  - `context_pager.py` (103 LOC)
  - `audit_log.py` (86 LOC)
- **Why:** Reinventing database transaction managers and operating systems in Python user space. Database already provides ACID transactions and row-level locks natively.
- **Replacement:** Use native DBMS transactions & `concurrent.futures.ThreadPoolExecutor`.

---

### [ ] DEL-04 — Delete Static Domain DDL Dictionaries & Duplicate Mismatch Guard (-490 LOC)
- **Where:** `core/semantic_decomposer.py:278-767`
- **Why:** 432 lines of hardcoded static dictionaries for "ecommerce", "hospital", "crm" generating canned DDL strings, and 58 lines of `SchemaMismatchGuard` duplicating Layer 3 of `core/validator/engine.py`.
- **Action:** Delete dictionaries and duplicate guard; let Layer 3 validator handle schema checks and LLM generate DDL.

---

### [ ] DEL-05 — Delete Hand-Rolled openCypher & Mongo MQL AST Visitors (-459 LOC)
- **Where:** `core/dialect_converter.py:61-520`
- **Why:** 459 lines attempting to convert SQL AST into openCypher (via a hardcoded 12-pair dictionary) and Mongo aggregation pipelines. Fails on non-SELECT and mutations.
- **Action:** Delete `OpenCypherVisitor` and `MongoMQLVisitor`. Focus `DeterministicDialectConverter` on SQL dialects natively supported by `sqlglot.transpile()`.

---

### [ ] DEL-06 — Delete Dead `FakePlanRunner` & `PostgresAdapter` (-268 LOC)
- **Where:** `core/cost_estimator/adapters/postgres.py`
- **Why:** Dead code hashing SQL to search for nonexistent JSON fixture files. Never called in runtime or tests.
- **Command:** `rm core/cost_estimator/adapters/postgres.py`

---

### [ ] DEL-07 — Delete Duplicate Sequential Pipeline Trace Runner (-246 LOC)
- **Where:** `core/pipeline_trace.py`
- **Why:** Standalone duplicate runner re-running orchestrator with fabricated model telemetry.
- **Action:** Replace with lightweight `trace=True` callback on `EndToEndNL2SQLOrchestrator`.

---

### [ ] DEL-08 — Replace `networkx` and Hand-Rolled Trie with Standard Library (-134 LOC, -1 dep)
- **Where:** `requirements.txt:6` & `core/schema_linker.py`
- **Why:** 15 MB `networkx` package imported solely for 4 lines of BFS (`has_path`, `shortest_path`). Hand-rolls a 50-line character Trie.
- **Action:** Replace `networkx` with an 8-line BFS using `collections.deque` on `Dict[str, Set[str]]`. Replace Trie with Python `set` / compiled regex. Drop `networkx` from `requirements.txt`.

---

### [ ] DEL-09 — Shrink Pseudo-Academic Paradigm Suggestor (-200 LOC)
- **Where:** `core/paradigm_suggestor.py`
- **Why:** 220 lines of keyword regexes claiming to be "CLEF discourse" and "DSpark".
- **Action:** Replace with a 20-line dictionary mapping target connection type to dialect.

---

### [ ] DEL-10 — Delete Regex Fallback Synthesizer (-138 LOC)
- **Where:** `core/orchestrator.py:46-183`
- **Why:** Guessing SQL from raw words silently produces bad queries when model is down.
- **Action:** Delete `SemanticSQLSynthesizer`; fail fast with `ModelInferenceUnavailableError`.

---

### [ ] DEL-11 — Delete Artificial WebSocket Sleep Loop (-88 LOC)
- **Where:** `GUI/server/services/pipeline_stub.py:49-136`
- **Why:** Unused mock sleep loop emitting fake stage completion events.
- **Action:** Delete `simulate_pipeline_run()`.

---

### [ ] DEL-12 — Consolidate Speculative Cost Protocols into Single Dataclass (-130 LOC)
- **Where:** `core/cost_estimator/contracts.py` & `thresholds.py`
- **Why:** Elaborate protocol interfaces with zero real implementations.
- **Action:** Replace with single dataclass `CostReport(est_rows, join_depth, warnings, is_blocked)`.

---

### [ ] DEL-13 — Unify Triplicated Demo Schema Definitions (-118 LOC)
- **Where:** `core/pipeline_trace.py`, `core/orchestrator.py`, `GUI/server/mock_data/schemas.py`
- **Why:** Exact same 5 tables copy-pasted across 3 files.
- **Action:** Define once in `data/demo_schema.json` and load via `json.load()`.

---

### [ ] DEL-14 — Delete Root-Level Backward Compatibility Package Shims (-46 LOC, 10 files)
- **Where:** Root `cost_estimator/` and `validator/` directories.
- **Why:** Stale shims doing `from core... import *`.
- **Command:** `rm -rf cost_estimator/ validator/`

---

### [ ] DEL-15 — Delete Dead Concurrency Flags & Cap Memory Dictionaries (-25 LOC)
- **Where:** `core/os_engine/scheduler.py:69` & `GUI/server/routers/query.py:76-77`
- **Action:** Remove dead `max_inflight_reads=8`; cap `stored_responses` to 100 items.

---

## Sequenced Execution Order for Developers

```
[Phase 1: Pure Deletions — Zero Breakage Risk]
  1. DEL-01: rm -rf offline/llama_cpp/ (-52,604 vendored lines, -211 MB)
  2. DEL-06: rm core/cost_estimator/adapters/postgres.py (-268 lines)
  3. DEL-11: Delete simulate_pipeline_run in pipeline_stub.py (-88 lines)
  4. DEL-14: rm -rf validator/ cost_estimator/ root shims (-46 lines)
  5. DEL-10: Remove regex fallback synthesizer from orchestrator.py (-138 lines)

[Phase 2: Core Correctness & Security Fixes]
  6. FIX-03: Per-session orchestrator scoping in query.py (stops multi-tenant corruption)
  7. FIX-02 & FIX-05: Defer lock release until approval; AST-based lock mode classification
  8. FIX-01: Invert validation order: transpile FIRST, then validate target dialect AST
  9. IMP-01: Wire sanitizer.py parameterization into orchestrator dispatch
  10. FIX-07 & FIX-08: Fix aliased JOIN ambiguity & quote-aware semicolon splitting

[Phase 3: Speculative Connector & Dialect Pruning]
  11. DEL-02: Prune 6 non-relational connectors (-1,146 lines, -5 driver deps)
  12. DEL-05: Remove openCypher & Mongo MQL AST visitors (-459 lines)
  13. DEL-04: Remove static domain dictionaries from semantic_decomposer.py (-490 lines)
  14. DEL-09: Replace paradigm_suggestor with static connection-type dictionary (-200 lines)

[Phase 4: Concurrency Engine & Stdlib Conversions]
  15. DEL-03: Replace core/os_engine/ with native DBMS transactions & ThreadPoolExecutor (-777 lines)
  16. DEL-08: Replace networkx with collections.deque BFS; drop networkx from requirements.txt (-134 lines, -1 dep)
  17. DEL-07: Replace pipeline_trace.py with orchestrator callback (-246 lines)
  18. DEL-12: Consolidate cost_estimator contracts into single CostReport (-130 lines)
  19. DEL-13: Unify triplicated demo schemas into data/demo_schema.json (-118 lines)
  20. IMP-02 & IMP-03: Implement rate limiter, semantic cache, and real DBMS savepoint rollback
```
