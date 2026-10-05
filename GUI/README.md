<div align="center">

# NL2SQL Desktop & Web Studio Shell

### Native Desktop & Responsive Web Observability Interface

[![Module Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=flat-square)](https://github.com/VanshikaKritiSingh/NL2SQL)
[![Electron](https://img.shields.io/badge/Electron-Desktop%20Runtime-47848F?style=flat-square&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-Bundler-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Bridge%20Server-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

<br />

**Lead UI / Systems Engineer:** Vanshika Kriti Singh &nbsp;|&nbsp; **Package:** `GUI/`

</div>

<br />

---

## Studio Interface Architecture

The Studio Shell unifies **Module 1 (Query Intake)** and **Module 14 (Human Approval Gate)** into a cohesive desktop and web application with dual execution modes:

```mermaid
flowchart TD
    subgraph Client_App [React 18 / Electron Desktop App]
        M1[Module 1: Query Intake]
        M14[Module 14: Approval Gate]
        STORE[Zustand State Store]
        MOCK[Client Simulation Engine]
        API[API & WebSocket Client]
        
        M1 --> STORE
        M14 --> STORE
        STORE <--> API
        STORE <--> MOCK
    end

    subgraph Backend_Bridge [FastAPI Server / Port 8000]
        ROUTER[FastAPI Routers]
        PIPELINE[Pipeline Service Stub]
        ROUTER <--> PIPELINE
    end

    API -->|REST & WS Streaming| ROUTER
    MOCK -.->|Zero-Backend Offline Mode| STORE
```

---

## Key Features

- **Module 1 (M1) - Natural Language Intake & Inspection:**
  - Interactive multi-dialect selector (PostgreSQL, MySQL, SQLite, DuckDB, Snowflake, BigQuery, Neo4j, MongoDB).
  - Live 16-stage pipeline progress indicator with timing and stage event payloads.
  - Monaco SQL code editor with syntax highlighting, AST inspections, and parameter bindings.
  - Paginated sandbox query result table.

- **Module 14 (M14) - Safety Guardrail & Human Approval Gate:**
  - Triggered automatically on mutating (DML) or schema-modifying (DDL) queries.
  - Interactive React Flow ER diagram visualizing write-target impact borders (Red = Primary Target, Yellow = Cascading FK).
  - Side-by-side Monaco DDL schema diff view and tabular before/after DML diffs.
  - Pre-flight EXPLAIN cost telemetry, row scan estimation, and deadlock/security risk badges.

- **Dual Execution Modes:**
  - **Standalone Simulation Mode:** Built-in client-side mock service allowing testing without spinning up Python backends.
  - **Live Bridge Mode:** Proxies requests over HTTP and WebSockets to the Python FastAPI backend on port 8000.

---

## Execution Modes & Launch Commands

```mermaid
flowchart LR
    TARGET{Launch Mode} -->|Desktop Native| DESK[npm run desktop:dev]
    TARGET -->|Browser Web| WEB[npm run dev]
    TARGET -->|FastAPI Bridge| BACK[cd server && python main.py]
```

### 1. Native Desktop Application
Runs in an Electron container with hot-module reloading and native desktop window controls:

```bash
# Navigate to GUI directory
cd GUI

# Run live development desktop mode (Vite + Electron)
npm run desktop:dev

# Run pre-packaged desktop executable
npm run desktop

# Build standalone Windows installer/executable
npm run desktop:build
```

### 2. Web Browser Client
Runs in any modern web browser:

```bash
cd GUI
npm run dev
```
Local URL: `http://localhost:5173`

---

## Directory Structure

```
GUI/
|-- electron/               # Native desktop lifecycle (main.cjs, preload.cjs)
|-- src/
|   |-- api/                # API client layer with automatic mock fallback
|   |-- hooks/              # WebSocket listeners and React state hooks
|   |-- mock/               # Zero-dependency client simulation engine
|   |-- modules/
|   |   |-- m1/             # Query intake, Monaco editor, progress tracker
|   |   `-- m14/            # React Flow ER graph, Monaco diffs, telemetry
|   |-- shared/             # TopBar, DialectSelector, RiskBadge, StatusBar
|   |-- store/              # Zustand state stores (app, query, pipeline)
|   `-- types/              # TypeScript schemas for requests and payloads
|-- server/                 # FastAPI Python backend bridge stubs
|-- package.json            # Desktop & web script definitions
`-- vite.config.ts          # Bundler configuration with relative asset paths
```

---

## Backend Bridge Integration

To connect the GUI shell to the live Python pipeline:

```bash
# 1. Start FastAPI pipeline bridge (from repository root)
cd GUI/server
python main.py

# 2. Launch GUI Studio (in another terminal)
cd ..
npm run desktop:dev
```

---

<div align="center">

*NL2SQL GUI Module: Technical Documentation & Implementation Reference*

</div>
