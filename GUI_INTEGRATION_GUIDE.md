# GUI Integration Guide — Module 1 & Module 14

**Owner:** Vanshika Kriti Singh (GUI Team Lead)  
**Status:** Implemented (V1 Complete)  
**Deliverable:** `D:\NL2SQL\GUI\` (Desktop & Web Studio + FastAPI bridge stubs)

---

## 1. Overview for Teammates

This document defines the **typed contracts** and **open integration strings** for the NL2SQL GUI. 

The GUI covers two critical human touchpoints in the pipeline:
- **Module 1 (M1):** Natural Language Query Intake — where the user types questions, chooses their DBMS dialect, views the generated SQL, and inspects results.
- **Module 14 (M14):** ER Diagram Visualizer & Human Approval Gate — activates automatically when a mutating/DDL query requires human review before touching the database.

All other modules (M2–M13, M15–M16) are currently served by **mock stubs** in `backend/routers/` and `backend/mock_data/`. When you are ready to plug in your real implementations, you only need to update the stub functions in the backend without touching the frontend.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Desktop & Web UI (D:\NL2SQL\GUI\)                          │
│  - Electron Native Desktop Shell / Vite React Web App       │
│  - M1: Query intake, history sidebar, Monaco SQL inspector  │
│  - M14: xyflow ER diagram, Monaco diff, telemetry panel     │
└──────────────┬──────────────────────────────▲───────────────┘
               │ REST (submit/approve)         │ WebSocket
               ▼                              │ (stage stream)
┌─────────────────────────────────────────────┴───────────────┐
│  FastAPI Backend Bridge (D:\NL2SQL\GUI\server\)             │
│                                                             │
│  [M1 Router]  ───► [Pipeline Stub] ───► [M14 Approval Router]│
│       │                    │                    │           │
│       ▼                    ▼                    ▼           │
│  M2, M3, M4          M5, M6, M7, M8,       M10 (EXPLAIN)    │
│  (Rate, Audit,       M9, M11, M12, M13     M11 (Security)   │
│   Cache)             (ML + Sec + Dev)      M15 (Dolt Diff)  │
│   [STUBS]               [STUBS]               [STUBS]       │
└─────────────────────────────────────────────────────────────┘
```
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Integration Points by Teammate / Module

### 🤖 ML Team (Anunay — M4, M5, M6)

#### Module 4: Semantic Cache
- **Where to plug in:** `GUI/server/services/pipeline_stub.py` (Stage 4) or `GUI/server/routers/query.py`
- **Expected behavior:** On cache hit, return `{ "cache_hit": true, "generated_sql": "...", "result_data": {...} }`. The UI will display a green `⚡ Cache Hit` badge and skip subsequent stages.
- **Payload model:**
  ```python
  class QueryResponse(BaseModel):
      cache_hit: bool = True
      generated_sql: str
      result_data: dict  # {"columns": [...], "rows": [...], "row_count": N}
  ```

#### Module 5: RAG-Based Schema Linker
- **Where to plug in:** `GUI/server/services/pipeline_stub.py` (Stage 5)
- **What to emit via WebSocket:**
  ```python
  PipelineStageEvent(
      stage_number=5,
      stage_name="RAG Schema Linker",
      status="completed",
      message="Selected 3 tables, 14 columns, 2 FKs (Steiner Minimal Tree)"
  )
  ```

#### Module 6: Deep Learning SQL Generator
- **Where to plug in:** `GUI/server/routers/query.py` (call your model inference)
- **Input:** `{ "user_id": str, "query_text": str, "target_dialect": str }`
- **Output:** The raw candidate SQL string passed to `QueryResponse.generated_sql`
- **Retry feedback:** If a human rejects a query in M14 with feedback, the backend calls your M6 endpoint with:
  ```python
  { "original_query": str, "rejected_sql": str, "feedback": str }
  ```

---

### 🛡️ Security Team (M2, M3, M7, M11, M13)

#### Module 2: Per-User Rate Limiter
- **Where to plug in:** `GUI/server/routers/query.py` (before processing)
- **Contract:** If rate limit exceeded, return HTTP 429 or:
  ```python
  QueryResponse(status="rate_limited", error_message="Budget exceeded. Try again in 60s.")
  ```
- **Input:** Every request includes `user_id: str`.

#### Module 3: Independent Observability Store & Audit Logger
- **Where to plug in:** Middleware or dependency on all endpoints in `GUI/server/main.py`
- **What to log:** Every incoming `QueryRequest`, `ApprovalRequest`, and stage transition.

#### Module 7: Parameterized Query Sanitizer
- **Where to plug in:** `GUI/server/services/pipeline_stub.py` (Stage 7)
- **Output:** Replaces `generated_sql` with parameterized form + params dict.

#### Module 11: Deadlock, Concurrency & Security Checker
- **Where to plug in:** `GUI/server/routers/analysis.py` → `GET /api/security-check/{query_id}`
- **Payload model expected by M14 Telemetry Panel:**
  ```python
  class SecurityCheck(BaseModel):
      deadlock_risk: Literal["none", "low", "medium", "high"]
      lock_level: str          # "row" | "table" | "schema"
      privilege_ok: bool       # True if current user has required DBMS role
      flags: List[str]         # e.g., ["FK_CASCADE_DELETE", "UNINDEXED_FILTER"]
  ```

#### Module 13: Read-Only Sandbox Replica
- **Where to plug in:** `GUI/server/routers/query.py` for read-only SELECT queries.
- **Output:** `{ "columns": [...], "rows": [...], "row_count": N }`

---

### 💻 Software Development Team (Sarthak — M8, M9, M10, M12, M15, M16)

#### Module 8: Multi-Dialect Converter & Normalizer
- **Where to plug in:** `GUI/server/services/pipeline_stub.py` (Stage 8)
- **Engine:** `sqlglot` AST transpiler
- **Input:** Generic ANSI SQL + `target_dialect: "mysql" | "oracle" | "sqlserver" | "access" | "postgres"`
- **Output:** Dialect-normalized SQL string displayed in Monaco inspector

#### Module 9: Static Validator & Anti-Pattern Detector
- **Where to plug in:** `GUI/server/services/pipeline_stub.py` (Stage 9)
- **If invalid:** Emit error event and route to retry gate (Stage 8 in pipeline).

#### Module 10: EXPLAIN-Style Cost Estimator
- **Where to plug in:** `GUI/server/routers/analysis.py` → `GET /api/explain/{query_id}`
- **Payload model expected by M14 Telemetry Panel:**
  ```python
  class CostEstimate(BaseModel):
      estimated_rows: int
      estimated_cost: float
      scan_type: str       # "full_table_scan" | "index_scan" | "index_only"
      warnings: List[str]  # e.g., ["Full table scan on orders (1.2M rows)"]
  ```

#### Module 12: Dual-Path Execution Router
- **Where to plug in:** `GUI/server/routers/query.py`
- **Routing logic:**
  - Read-only (SELECT) → route to M13 (Sandbox) → return `QueryResponse(status="completed")`
  - Mutating (INSERT/UPDATE/DELETE/ALTER/DROP) → route to M14 → return `QueryResponse(status="approval_required", approval_payload=...)`

#### Module 15: Transaction Wrapper & CAS Checkpoint (Dolt)
- **Where to plug in:** 
  1. `GUI/server/routers/analysis.py` → `GET /api/diff/{query_id}` to provide DDL/DML diffs for M14 preview
  2. `GUI/server/routers/approval.py` on approval to execute inside Dolt commit
- **Diff payload model expected by M14 Diff Panel:**
  ```python
  class DiffData(BaseModel):
      diff_type: Literal["ddl", "dml", "none"]
      ddl_before: Optional[str]  # Original schema DDL
      ddl_after: Optional[str]   # Schema DDL with changes applied
      dml_rows: Optional[List[DmlRowDiff]]  # Tabular before/after rows
  ```

#### Module 16: Connected DBMS Dispatcher & Response Formatter
- **Where to plug in:** `GUI/server/routers/approval.py` (after M15 commit)
- **Output:** Formatted status message returned to the user.

---

## 4. How to Run the GUI Locally

### Option A: Standalone Desktop Application (Zero Setup Required)
```bash
cd D:\NL2SQL\GUI

# Live desktop development / test window
npm run desktop:dev

# Run packaged executable directly
npm run desktop
```

### Option B: Web Browser Mode
```bash
cd D:\NL2SQL\GUI
npm run dev
# Running on http://localhost:5173
```

### Option C: With FastAPI Backend Bridge (For Teammate Testing)
1. **Start the FastAPI Backend:**
   ```bash
   cd D:\NL2SQL\GUI\server
   python main.py
   # Running on http://127.0.0.1:8000 (Swagger docs at /docs)
   ```
2. **Start the GUI (Desktop or Web):**
   ```bash
   cd D:\NL2SQL\GUI
   npm run desktop:dev   # Desktop
   # OR
   npm run dev           # Web
   ```

The Vite dev server automatically proxies `/api/*` and `/ws/*` to the FastAPI backend on port 8000.

---

## 5. UI Demo Scenarios (Built into Stubs)

The mock backend includes 3 pre-built scenarios to demonstrate the full pipeline:

1. **Read-only query (Auto-executes):**
   - Type: `"Show me all orders from last month"`
   - Result: Pipeline runs stages 1–13, returns a 5-row table in the Result Panel, Monaco shows formatted SELECT SQL.

2. **Mutating UPDATE query (Triggers M14 Approval Gate):**
   - Type: `"Increase all product prices by 10%"`
   - Result: Pipeline halts at Stage 14, UI transitions to Approval Gate:
     - React Flow ER diagram shows `products` table highlighted with **red border** (direct impact)
     - Monaco SQL panel shows `UPDATE products SET price = price * 1.10`
     - Tabular DML diff shows before ($49.99) → after ($54.99) prices
     - Pre-flight telemetry shows EXPLAIN cost ($42.50) + Security flags
     - Approve / Reject buttons with feedback input

3. **DDL Schema Change query (Triggers M14 Approval Gate with Monaco DDL Diff):**
   - Type: `"Add a discount_code column to orders table"`
   - Result: UI transitions to Approval Gate:
     - React Flow ER diagram shows `orders` table highlighted in red with `[ALTER]` badge
     - Monaco side-by-side DDL Diff shows original `CREATE TABLE` vs modified `CREATE TABLE`
     - Pre-flight telemetry shows lock level = `table` and risk tier = `HIGH`
