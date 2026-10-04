# Unified GUI Module (Module 1 & Module 14) — Desktop & Web Studio

This folder contains the complete, standalone desktop application and web implementation for the **NL2SQL Pipeline** project:
- **Module 1:** Natural Language Query Intake, SQL Inspector (Monaco Editor), Live 16-Stage Pipeline Tracker, and Tabular Sandbox Results.
- **Module 14:** Interactive ER Diagram Visualizer (React Flow with write-target impact highlighting), Side-by-Side DDL / Tabular DML Diffs, Pre-flight Telemetry (M10 EXPLAIN cost & M11 Deadlock/Security flags), and Human Approval Gate.

---

## 🖥️ How to Run as a Standalone Desktop Application

### Option 1: Live Desktop Mode (Recommended for testing & development)
Starts Vite and automatically launches the native desktop window with live hot-reloading:

```powershell
cd D:\NL2SQL\GUI
npm run desktop:dev
```

### Option 2: Run Packaged Desktop Executable Directly
Launch the pre-built native Windows application executable:

```powershell
# Directly double-click or run from PowerShell:
.\dist-electron\win-unpacked\"NL2SQL Studio.exe"
```
Or use the npm script:
```powershell
npm run desktop
```

### Option 3: Build Standalone Windows Executable (.exe)
To package an updated Windows binary:
```powershell
npm run desktop:build
```
*(Produces a standalone `NL2SQL Studio.exe` inside `dist-electron\win-unpacked\`)*

---

## 🌐 Running in the Web Browser

If you prefer to run it inside Google Chrome / Edge / Firefox:

```powershell
cd D:\NL2SQL\GUI
npm run dev
```
Navigate to: **`http://localhost:5173`**

---

## 📁 Directory Structure

```
D:\NL2SQL\GUI\
├── electron\            # Native desktop container & lifecycle (main.cjs, preload.cjs)
├── src\
│   ├── api\             # Centralized API fetch layer with auto-fallback to mock services
│   ├── hooks\           # WebSocket client and React hooks
│   ├── mock\            # In-memory mock data and pipeline progress simulation (Zero external dependencies)
│   ├── modules\
│   │   ├── m1\          # Module 1 UI components (Input, History, Inspector, Progress, Results)
│   │   └── m14\         # Module 14 UI components (ER Diagram, Monaco Diff, Telemetry, Approvals)
│   ├── shared\          # Reusable UI widgets (TopBar, DialectSelector, RiskBadge, StatusBar)
│   ├── store\           # Zustand state management (App, Query, Pipeline state)
│   ├── types\           # TypeScript contracts and models
│   ├── App.tsx          # Root container shell with view toggling
│   ├── main.tsx         # React root bootstrap
│   └── index.css        # Tailwind CSS and theme styles
├── server\              # FastAPI Python backend bridge stubs (for teammate integration)
├── package.json         # Desktop scripts, Electron config, dependencies
├── vite.config.ts       # Vite bundler configuration (with relative paths for desktop)
└── README.md
```

---

## 🔌 Teammate Integration (FastAPI Bridge)
When Anunay (ML) or Sarthak (Dev/Sec) connect real pipeline endpoints:

1. **Start the backend bridge:**
   ```powershell
   cd D:\NL2SQL\GUI\server
   python main.py
   ```
   *(Runs on `http://127.0.0.1:8000` with docs at `http://127.0.0.1:8000/docs`)*

2. **Launch the Desktop App or Web App:**
   ```powershell
   cd D:\NL2SQL\GUI
   npm run desktop:dev    # for desktop
   # OR
   npm run dev            # for web
   ```
