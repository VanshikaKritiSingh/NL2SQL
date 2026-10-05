<div align="center">

# NL2SQL Desktop & Web Studio Shell

**Modules 1 & 14: User Interface, Monaco SQL Inspector, and Human Approval Gate**

`[Work Status: Implemented & Verified]` &nbsp;|&nbsp; `[Framework: React 18 + Electron + FastAPI]`

---

</div>

<br />

---

<div align="center">

### Module Interface Architecture

</div>

```
+-----------------------------------------------------------------------------------------+
|                                    GUI STUDIO SHELL                                     |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +---------------------------------------+   +-------------------------------------+   |
|   |  Module 1: Natural Language Intake    |   |  Module 14: Approval & Guardrails   |   |
|   |---------------------------------------|   |-------------------------------------|   |
|   |  * Prompt submission & history        |   |  * React Flow ER diagram viewer     |   |
|   |  * 16-Stage live pipeline tracking    |   |  * Monaco side-by-side DDL diffs    |   |
|   |  * Monaco SQL AST syntax inspector    |   |  * Tabular DML before/after diffs   |   |
|   |  * Sandbox query result table         |   |  * M10 EXPLAIN & M11 safety telemetry| |
|   +---------------------------------------+   +-------------------------------------+   |
|                                       \           /                                     |
|                                        v         v                                      |
|   +---------------------------------------------------------------------------------+   |
|   |                          Dual-Mode Client-Side Engine                           |   |
|   |  * Standalone Simulated Mode: Zero-backend instant demo & local mock state      |   |
|   |  * Live Bridge Mode: WebSocket & REST integration with FastAPI backend (port 8000)| |
|   +---------------------------------------------------------------------------------+   |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

<div align="center">

### Execution Modes & Launch Commands

</div>

```
                        [Launch Target Selection]
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v                                                   v
   [Native Desktop App]                              [Web Browser Client]
          |                                                   |
  npm run desktop:dev                                     npm run dev
          |                                                   |
(Electron container with HMR)                         (Vite server at port 5173)
```

#### 1. Native Desktop Application
Runs in an isolated Electron container with desktop window controls:

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

#### 2. Web Browser Application
Runs in any modern web browser:

```bash
cd GUI
npm run dev
```
Access URL: `http://localhost:5173`

---

<div align="center">

### Directory Layout

</div>

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

<div align="center">

### Backend Bridge Integration

</div>

To connect the GUI shell to the live Python pipeline:

```bash
# 1. Start FastAPI pipeline bridge (from repository root)
cd GUI/server
python main.py

# 2. Launch GUI Studio
cd ..
npm run desktop:dev
```

---

<div align="center">

*NL2SQL GUI Module: Technical Documentation & Implementation Reference*

</div>
