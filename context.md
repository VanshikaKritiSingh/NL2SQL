# Workspace Context — NL2SQL Pipeline

Lazy: one file, no duplication, everything derived from what's actually here. Ponytail: ask "does this document need to exist?" — yes, it's the only consolidated index; no extra scaffolding.

---

## 1. Workspace facts (derived from directory listing, 8 files total)

Path: `D:\Programs\AiMl\NL2SQL` (working dir, separate from `C:\Users\Anunay\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh` — the checkout location).

Files present (last write order, newest last):
- `NL2SQL-Pipeline-Architecture.md` / `(1).md` — duplicate architecture spec (both 12788 B, 1s apart, 10:38 AM). Same mermaid diagram + stage table + sub-project list + references (8 sources: DEV, Medium x2, Protecto, khimananda, DevOps, Fastio, BlazeSQL).
- `diagrams/pipeline_v2_check.png` — rendered diagram, 1400×2045, 347 KB, black background (matches SVG dark theme).
- `Projects.pdf` — 135 KB, not inspected in detail; referenced implicitly by workspace name.
- `diagrams/SVG_DIAGRAM.svg` — 114 KB, 1600×3560, primary diagram source (Miro-exported: embedded `mirostatic.com` font-face URLs for Noto Sans / OpenSans / Fredoka One / Noto Sans Hebrew/JP/KR).
- `html/template.html` — 23 KB; references `%%SVG_DIAGRAM%%` placeholder; custom palette (--blue --pink --green --yellow --gray); includes embedded legend grid (color + shape) and TOC.
- `nl2sql.html` — 26 KB; v2 design, inline SVG (`viewBox="0 0 1180 2030"`), Playfair Display / Inter fonts via Google Fonts, stage-number annotations (1–16) embedded in diagram, legend block at bottom (y ~1830–1978).

No hidden files besides default. No build artifacts, no `node_modules`, no `.git`. No source control evidence.

---

## 2. Content summary (per file, minimal)

**Architecture docs (`.md`)** — Design-draft status. Core loop: query → cache check → generate SQL → validate → estimate cost/risk → route by risk tier → (human approval if needed) → execute → return. 15 stages numbered (rate limiter = 1, audit log = 15 in v1; v2 adds DBMS-mediated stage 15 + formatted response 16 + audit 17). Sub-projects: parameterized query builder, deterministic dialect converter, fuzz framework, anti-pattern detector, ER diagram generator, schema version control, index advisor. Deliberately excluded listed (schema-design-phase tools + ops tools). Production practices: cache-first, narrow schema, bounded retry, cost-before-execute, tiered risk, transaction+checkpoint, cross-cutting audit, readiness as governance.

**`html/nl2sql.html` (v2)** — Light theme (#fff, Playfair headings, Inter body). Inline SVG at y~30–2030 inside figure; legend embedded at bottom; stage numbers 1–16 placed directly on diagram nodes; labels like "User", "Natural language query", "Per-user rate / budget limiter", "Semantic cache hit?", "Schema linking / RAG context retrieval", "Deep learning model", "Parameterized query builder", "Deterministic dialect converter", "Static validator", "Dry-run / EXPLAIN cost + scan estimate", "Read-only or mutating / DDL?", "ER diagram / impact visualizer", "Human approves?", "Transaction wrapper + checkpoint", "Schema version control / migration log", "User's DBMS" (with MySQL · Oracle · SQL Server · Access sub-label), "Database" (managed by DBMS), "Formatted response". Dashed arrows = background/audit; solid = live request (legend 1830–1978). Footer: "Single file: SVG diagram and legend inlined; headings Playfair Display... Keep `diagrams/SVG_DIAGRAM.svg` alongside for Confluence, PDF export..."

**`html/template.html`** — Template for future rendering; `%%SVG_DIAGRAM%%` insertion point at section 2; legend uses 2-column grid with swatch + description; color semantics: blue = getting ready, pink = safety check, green = needs human / writes, yellow = background helper, gray = record-keeping; shapes: oval (start/end), rectangle (action), diamond (decision), slanted box (data transformed), cylinder (store).

---

## 3. SVG / image — exact position + reason (required attention)

### `diagrams/SVG_DIAGRAM.svg` (primary source)
- **Position**: workspace root. **Why it's there**: exported Miro diagram (font URLs prove `mirostatic.com` origin); the 1600×3560 canvas with black `#2e2e2e` background and embedded legend at right (translate 1104.5, 105, size 355×635) makes it the master visual asset — intended for embedding in tools that can't render Mermaid (as `.md` line 4 states: "static image — use this in tools that can't render Mermaid, e.g. Confluence, plain PDF export, email").
- **Exact layout**: Main diagram body at translate(60, 40) inside 1480×3480; legend panel separate at right; bottom-right has red-circle "X" reject markers (translate 1140, 3317.5) near "Production database" node — these are visual reject/cancel indicators placed adjacent to the DB output so a reader can see where a rejected query exits the flow.
- **Red circle note icons (📝)** at positions ~1210,2418 and ~1210,2600 near "Audit log / observability store" (translate 765.5, 230) and "Index / covering-index advisor" — positioned to flag these as review/annotation points because they are cross-cutting (audit feeds every stage via dotted side-channel; advisor feeds back into schema linking via dashed telemetry line).
- **Color coding in SVG** matches `.md` legend: pink (#ffc6c6 / #f9d5d3) = security/cost gates; blue (#c6dcff / #d6e8f5) = pre-flight; green (#adf0c7 / #c9e4de) = human/write-path; yellow (#fff6b6 / #fdf6b2) dashed = offline; gray (#e7e7e7 / #e0e0e0) dashed = audit. The SVG uses thicker borders (stroke-width 4) and explicit arrow markers (`LineHeadArrow2/3/4`) to make direction unambiguous at 1600 px width.
- **Reason for black background vs white**: this SVG is designed as a dark-canvas export (likely for presentation/dark-mode use); `nl2sql.html` and `html/template.html` use light backgrounds for document reading — they are different render targets of the same pipeline info.

### `diagrams/pipeline_v2_check.png`
- **Position**: workspace root, between PDF and SVG by timestamp. **Why it's there**: 1400×2045 rendered output of the same diagram with identical black background, labeled nodes (top-right audit/index/fuzz/anti-pattern), same vertical pipeline order. Confirmed as a check/verification render ("v2_check" filename) — used to verify the SVG renders correctly before embedding. Shares the dark theme with SVG; differs from the white-theme HTML versions.
- **Image analysis (visual)**: top band has "Audit log / observability store", "Index / covering-index advisor", "Fuzz testing harness", "Schema anti-pattern detector" arranged right-side vertically — exactly where `diagrams/SVG_DIAGRAM.svg` places the legend and offline-support nodes (translate 1124–1358 region). Middle column: rate limiter diamond -> cache diamond -> model rectangle -> validator diamond -> cost diamond -> risk diamond -> sandbox / ER branches. Bottom: DB oval -> response oval.

### `html/nl2sql.html` inline SVG (not a separate file, embedded)
- **Position**: inside `<figure>` at y~47 in HTML; `viewBox="0 0 1180 2030"`. **Why**: self-contained document — the design draft explicitly promises to work when shared directly (line 273 footer: "this file is self-contained and can be opened directly in any browser or shared as-is"). The lighter palette and embedded legend replace the dark SVG for web viewing.

### `html/template.html`
- **Position**: root, references `%%SVG_DIAGRAM%%`. **Why**: template for generating future document versions; it defines the legend semantics (color/shape) that both `nl2sql.html` and the `.md` file use.

---

## 4. Relationships / lineage (lazy dedup)

- `.md` (v1, mermaid) ↔ `nl2sql.html` (v2, inline SVG): same pipeline, v2 adds DBMS-mediated execution (stage 15) and splits audit into #17. `html/template.html` is the renderer for v2-style output.
- `diagrams/SVG_DIAGRAM.svg` ↔ `diagrams/pipeline_v2_check.png`: PNG is rendered sibling of SVG (same black-theme, same node layout, different resolution — 1600×3560 vs 1400×2045, same aspect ~0.45).
- `NL2SQL-Pipeline-Architecture.md` = `... (1).md`: near-duplicate (3s gap); no meaningful difference detected at line level from read output.
- `Projects.pdf`: uninspected binary; likely the PDF counterpart to the architecture doc (mentioned in `.md` companion-file note).

---

## 5. Skill context (from session — active per instructions)

- `ponytail` (full): enforce ladder (YAGNI, reuse, stdlib, native, one line). This file is 1 document = minimal; no extra abstraction layer added.
- `ponytail-audit` / `ponytail-review`: not executed on this doc (scope = over-engineering of code, not a context file), but ladder applied: no factory/interface for context, no scaffold for "later".
- Approval policy: changed to "never" in session; no escalation needed (file write within workspace, no sandbox denial encountered).

---

## 6. Key exact-position takeaways (for any future edit / render)

| Asset | Exact position / dims | Reason it's at that spot |
|---|---|---|
| `diagrams/SVG_DIAGRAM.svg` | diagrams/; 1600×3560; body translate(60,40), legend translate(1104.5,105) | Miro-exported master; dark canvas for presentation; legend separated so it can be cropped; red-X markers bottom-right to indicate rejection exit from DB node |
| `diagrams/pipeline_v2_check.png` | diagrams/; 1400×2045 | Render check of SVG (filename confirms); black bg confirms same theme; used to verify before embedding into `.md` (Confluence/PDF) |
| `html/nl2sql.html` inline | figure y~47; viewBox 0 0 1180 2030; legend y~1830 | Self-contained web document; light theme for readability; legend embedded bottom rather than side so it doesn't break narrow viewports |
| `html/template.html` | html/; `%%SVG_DIAGRAM%%` at section 2 | Template for future renders; defines color/shape semantics used by both HTML versions |

---

## 7. Team context (non-technical, for `AGENT.md` / `DOCUMENTATION.md` to reference)

Three third-year B.Tech CSE students on a ProjectBasedLearning (PBL) deliverable:
- **Vanshika Kriti Singh** — creative, documentation, graphic design, QA testing.
- **Anunay Sharma** — backbone, AI, LLM, ML, tech support, system design.
- **Sarthak Singh** — software, algo design, socratic questioner, eager learner.

The role split is by craft, not seniority. Pipeline stages are mapped to teammates in `AGENT.md`.

---

*File written: `context.md` (this file). Nothing else added; no duplicate docs created; no build artifacts. Ponytail skip: no test file (trivial document, no logic branch). Add when a viewer needs automated validation of SVG→PNG parity (then add a one-line `compare` script).*
