# DOCUMENTATION.md — Project Handbook

Hybrid: machine-readable first (a structured block for tools and scripts to parse), human-readable second (prose for evaluators, onboarding, and team review).

---

## Machine-readable block

```yaml
project: NL2SQL Pipeline
course: ProjectBasedLearning (PBL)
institution: B.Tech CSE, 3rd year
team_size: 3
team:
  - name: Vanshika Kriti Singh
    short: Vanshika
    role: creative, documentation, graphic design, QA testing
  - name: Anunay Sharma
    short: Anunay
    role: backbone, AI, LLM, ML, tech support, system design
  - name: Sarthak Singh
    short: Sarthak
    role: software, algo design, socratic questioner, eager learner
pipeline_version: v2
pipeline_source_of_truth: nl2sql.html
stages: 16
side_channels: 4
assets:
  - path: diagrams/SVG_DIAGRAM.svg
    kind: svg-master
    dims: 1600x3560
    theme: dark
    origin: miro-export
  - path: diagrams/pipeline_v2_check.png
    kind: png-render
    dims: 1400x2045
    theme: dark
    purpose: render-check
  - path: html/nl2sql.html
    kind: html-self-contained
    theme: light
    inline_svg: true
  - path: html/template.html
    kind: html-template
    placeholder: "%%SVG_DIAGRAM%%"
architecture_docs:
  - NL2SQL-Pipeline-Architecture.md
  - DECIDED_MODULES.md
context_index: context.md
out_of_pipeline_scope:
  - schema-design-phase tools
  - ops tools
```

---

## Human-readable Walkthrough

### What this project is

A pipeline that takes a natural-language question, produces a parameterized SQL query, validates it, estimates its cost, routes it by risk, optionally asks a human to approve, and executes it inside a transaction against the user's DBMS. The full 16-stage flow and the four side-channels (audit, index advisor, fuzz harness, anti-pattern detector) are documented in `nl2sql.html` and `SVG_DIAGRAM.svg`.

### Who built it

Three third-year B.Tech CSE students working on a PBL deliverable:
- **Vanshika Kriti Singh** — creative, documentation, graphic design, QA testing.
- **Anunay Sharma** — backbone, AI, LLM, ML, tech support, system design.
- **Sarthak Singh** — software, algorithmic design, validation.

### How to read this repo

1. `context.md` — Workspace index of assets, exact positions, and color/shape legend semantics.
2. `NL2SQL-Pipeline-Architecture.md` — Core architecture specification, 16 stages walkthrough, production practices, and references.
3. `DECIDED_MODULES.md` — Technical module specifications for model foundation, schema linking, and dialect conversion.
4. `nl2sql.html` — The pipeline as a self-contained webpage (light theme, inline SVG, embedded legend).
5. `SVG_DIAGRAM.svg` — The master diagram (dark theme, Miro-exported, 1600×3560). Use this in tools that cannot render Mermaid (Confluence, PDF, email).
6. `diagrams/pipeline_v2_check.png` — Rendered check of the SVG (dark theme, 1400×2045).
7. `html/template.html` — The renderer template for future docs; defines the legend semantics used across HTML versions.

### What is and is not in scope

- **In scope:** Stages 1–16 (Rate limiting, Semantic cache, Schema linking/RAG, Model generation, Query parameterization, Dialect conversion, Static validation, Retry gate, Cost estimation, Risk tiering, Impact visualizer, Human approval, Transaction wrapper, Schema version control, DBMS execution, Response formatting) + the four side-channels (Audit log, Index advisor, Fuzz harness, Anti-pattern detector).
- **Out of scope:** Schema-design-phase tools (automated relational design, denormalization advisor) and generic infrastructure/ops tools (workload replayer, warehouse dashboards).
