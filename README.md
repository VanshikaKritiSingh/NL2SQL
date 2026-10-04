# NL2SQL Pipeline — Desktop & Web GUI (Module 1 & Module 14)

**PBL Project Deliverable:** B.Tech CSE (3rd Year)  
**Lead Developer (GUI):** Vanshika Kriti Singh  
**Teammates:** Anunay Sharma (ML / DL), Sarthak Singh (Software Dev & Security)

---

## 🌟 Executive Summary

This repository contains the complete **User Interface & Observability Shell** for the **NL2SQL Production Pipeline**, packaged as both a **standalone native desktop application** and a responsive web application. The GUI provides human-supervised control over AI-generated database queries and schema modifications, ensuring zero unsupervised writes to production databases.

The GUI covers two core stages in the 16-stage pipeline:
1. **Module 1 (M1) — Natural Language Query Intake:** Interactive workspace for natural language prompt submission, target DBMS dialect selection, live 16-stage pipeline progress tracking, Monaco-based SQL AST inspection, and query execution result rendering.
2. **Module 14 (M14) — ER Diagram Visualizer & Human Approval Gate:** Safety guardrail activated when mutating (DML) or schema-altering (DDL) queries are submitted. Features interactive React Flow ER graph with red/yellow table highlight borders, Monaco side-by-side DDL diffs, tabular DML data diffs, M10 EXPLAIN cost estimates, and M11 deadlock/concurrency flags.

---

## 🖥️ Standalone Desktop Application Quick Start

The entire GUI is consolidated inside the `GUI/` directory and can run out-of-the-box as a native desktop application with zero backend configuration needed (built-in simulation engine included).

### 1. Launch in Desktop Mode (Live Dev / Test)
```powershell
cd D:\NL2SQL\GUI
npm run desktop:dev
```
*This starts the background Vite server and automatically opens the native NL2SQL Studio desktop window.*

### 2. Run Direct Executable
```powershell
.\dist-electron\win-unpacked\"NL2SQL Studio.exe"
# OR
npm run desktop
```

### 3. Build Windows Executable Installer / Portable Binary
```powershell
npm run desktop:build
```

---

## 🌐 Web Mode (Browser)

If you prefer to run inside a standard web browser:

```powershell
cd D:\NL2SQL\GUI
npm run dev
```
Navigate to: **`http://localhost:5173`**

---

## 📋 Interactive Demo Scenarios (Built-in Standalone Engine)

Try these pre-configured prompts in the UI to see the complete pipeline in action:

| Query Type | Prompt Suggestion | Expected Pipeline Behavior |
|---|---|---|
| **Read-Only (SELECT)** | `"Show me all orders from last month..."` | Passes through stages 1–13. Returns 5-row table from M13 Sandbox. Monaco inspector shows formatted SQL with `DATE_SUB` and `JOIN`. |
| **Mutating (DML UPDATE)** | `"Increase all product prices by 10%..."` | Dual-path router (M12) trips approval gate (M14). ER diagram highlights `products` table in **red** (`[UPDATE]`) and `order_items` in **yellow**. Data diff shows before ($49.99) vs after ($54.99). Cost & Security cards display telemetry. |
| **Schema DDL (ALTER)** | `"Add a discount_code column to orders table"` | Approval gate (M14) activates with **CRITICAL** risk tier. Monaco side-by-side Diff editor displays schema before vs after. Exclusive schema lock warning displayed. |

---

## 📁 Repository Structure

```
D:\NL2SQL\
├── GUI\                            # Consolidated Desktop & Web deliverable
│   ├── electron\                   # Native desktop container & lifecycle
│   │   ├── main.cjs                # Electron window, IPC, security sandbox
│   │   └── preload.cjs             # Safe context bridge
│   ├── src\
│   │   ├── api\                    # Fetch and WebSocket clients (with auto mock fallback)
│   │   ├── mock\                   # Full client-side simulation engine
│   │   ├── modules\
│   │   │   ├── m1\                 # Module 1 UI: Query Intake, Monaco SQL, Progress, Results
│   │   │   └── m14\                # Module 14 UI: React Flow ER Graph, Monaco Diff, Telemetry, Approvals
│   │   ├── shared\                 # Reusable components (TopBar, DialectSelector, RiskBadge)
│   │   ├── store\                  # Zustand stores (useAppStore, useQueryStore, usePipelineStore)
│   │   └── types\                  # TypeScript contracts
│   ├── server\                     # FastAPI backend bridge stubs (for Anunay & Sarthak)
│   ├── package.json                # Desktop & web scripts, electron-builder config
│   └── vite.config.ts              # Vite configuration (relative desktop paths)
├── GUI_INTEGRATION_GUIDE.md        # Complete API and teammate integration contract
├── README.md                       # Main project documentation
└── skill.md                        # Team operational handbook & coding standards
```

---

## 🔌 Teammate Integration Guide

All API contracts, Pydantic schemas, and TypeScript interfaces are formally documented in [`GUI_INTEGRATION_GUIDE.md`](./GUI_INTEGRATION_GUIDE.md).

- **Anunay (ML Team — M4, M5, M6):** Connect your model inference to `GUI/server/routers/query.py` and emit Steiner Minimal Tree schema linkage events to `GUI/server/services/pipeline_stub.py`.
- **Sarthak (Software Dev & Security — M8, M9, M10, M11, M12, M15, M16):** Plug your `sqlglot` converter, EXPLAIN cost estimator, and Dolt CAS commit wrapper into `GUI/server/routers/analysis.py` and `GUI/server/routers/approval.py`.
