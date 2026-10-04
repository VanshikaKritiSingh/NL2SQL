# CONTEXT.md — workspace index

Consolidated reference index for all pipeline specifications and documentation assets in this repository.

---

## 1. Workspace facts

Repo: `https://github.com/VanshikaKritiSingh/NL2SQL` (main).

Files present (root):
- `NL2SQL-Pipeline-Architecture.md` — pipeline specification, 16 stages, mermaid diagram + prose walkthrough.
- `DECIDED_MODULES.md` — technical architecture specifications for Module 0 (Model foundation/eval), Module 1 (Schema linker), and Module 2 (Dialect converter).
- `DOCUMENTATION.md` — documentation handbook (machine-readable YAML + human-readable walkthrough).
- `diagrams/` — `SVG_DIAGRAM.svg` (primary dark source, 1600×3560) + `pipeline_v2_check.png` (render check).
- `html/` — `nl2sql.html` (v2, light theme, inline SVG) + `template.html` (render template, `%%SVG_DIAGRAM%%` placeholder).

---

## 2. Content summary

**`NL2SQL-Pipeline-Architecture.md`** — Design specification. Core loop: query → cache check → generate SQL → validate → estimate cost/risk → route by risk tier → (human approval if needed) → execute → return. 16 stages numbered. Sub-projects: parameterized query builder, deterministic dialect converter, fuzz framework, anti-pattern detector, ER diagram generator, schema version control, index advisor. Deliberately excluded: schema-design-phase tools + ops tools. Production practices: cache-first, narrow schema, bounded retry, cost-before-execute, tiered risk, transaction+checkpoint, cross-cutting audit.

**`DECIDED_MODULES.md`** — Module design registry. Details specifications for:
- Module 0: Model Foundation & Offline Training/Eval Suite (`Qwen2.5-Coder` / `DeepSeek-Coder-V2-Lite`, QLoRA, TS-EX metrics).
- Module 1: Schema Linker / Context Retrieval (Hybrid BM25 + Dense vector retrieval via RRF, Steiner Minimal Tree relational integrity, pre-built categorical value trie).
- Module 2: Deterministic Dialect Converter (`sqlglot` AST transpiler, sub-5ms execution, deterministic rewriting).

**`diagrams/SVG_DIAGRAM.svg`** — 1600×3560, dark `#2e2e2e` background. Miro-exported master; legend at right (translate 1104.5, 105); red-X markers near "Production database" node (rejection exit indicators); red note icons near audit/index nodes. Color coding: pink = security/cost gates, blue = pre-flight, green = human/write-path, yellow dashed = offline, gray dashed = audit.

**`diagrams/pipeline_v2_check.png`** — 1400×2045, render check of SVG; dark bg, same node layout; used to verify before embedding.

**`html/nl2sql.html`** — Light theme, inline SVG (`viewBox="0 0 1180 2030"`), Playfair Display + Inter, stage numbers 1–16 on nodes, legend embedded at bottom (~y 1830–1978). Self-contained; opens in any browser.

**`html/template.html`** — Template for future renders; `%%SVG_DIAGRAM%%` insertion point; defines color/shape semantics (blue=get ready, pink=safety, green=human/write, yellow=helper, gray=record; oval=start/end, rectangle=action, diamond=decision, slanted=data, cylinder=store).

---

## 3. SVG / image — exact position + reason

| Asset | Position / dims | Why it's there |
|---|---|---|
| `diagrams/SVG_DIAGRAM.svg` | diagrams/; 1600×3560; body translate(60,40), legend translate(1104.5,105) | Miro-exported master; dark canvas for presentation; legend separated for Confluence/PDF/email embedding; red-X near DB node for rejection exit |
| `diagrams/pipeline_v2_check.png` | diagrams/; 1400×2045 | Render verification of SVG; dark bg; verifies before embedding |
| `html/nl2sql.html` inline | figure y~47; viewBox 0 0 1180 2030; legend y~1830 | Self-contained web document; light theme for readability; legend embedded bottom for narrow viewports |
| `html/template.html` | html/; `%%SVG_DIAGRAM%%` at section 2 | Future renders; defines color/shape semantics for HTML versions |

---

## 4. Relationships / lineage

- `.md` (v1, mermaid) ↔ `nl2sql.html` (v2, inline SVG): same pipeline, v2 adds DBMS-mediated execution (stage 15) and splits audit into #17.
- `diagrams/SVG_DIAGRAM.svg` ↔ `diagrams/pipeline_v2_check.png`: PNG is rendered sibling of SVG (same dark theme, same node layout; 1600×3560 vs 1400×2045).
- `html/template.html` ↔ `nl2sql.html`: template/renderer pair for v2-style output.

---

## 5. Team roles

Three third-year B.Tech CSE students on a ProjectBasedLearning (PBL) deliverable:
- **Vanshika Kriti Singh** — creative, documentation, graphic design, QA testing.
- **Anunay Sharma** — backbone, AI, LLM, ML, tech support, system design.
- **Sarthak Singh** — software, algorithmic design, validation.
