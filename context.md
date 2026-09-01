# CONTEXT.md — workspace index for the agent

Lazy: one file, no duplication, everything derived from what's actually here. Ponytail: ask "does this document need to exist?" — yes, it's the only consolidated index; no extra scaffolding.

---

## 1. Workspace facts

Path: `D:\Programs\AiMl\NL2SQL` (local working dir). Repo: `https://github.com/VanshikaKritiSingh/NL2SQL` (main). Auth: `gh auth` done, `Bhuknuu` account, `WRITE` permission. Author: Anunay Sharma (`anunaysharma88@gmail.com`).

Files present (root):
- `NL2SQL-Pipeline-Architecture.md` — pipeline specification, 16 stages, mermaid diagram + prose.
- `AGENT.md` — what the agent does, owner mapping, hard rules.
- `SKILL.md` — three skills (anti-slop, NL→SQL craft, algorithmic craft), load order.
- `TEAM.md` — team structure, persona agents, 6-agent architecture, round-robin rotation, module division, shadow→cross phases.
- `DESIGN.md` — text anti-slop (Part 1), design anti-slop (Part 2), HTML spec (Part 3), Devil's Advocate (Part 4), devlog rules. Source of `rules/anti-slop-craft-SKILL.md` and `rules/devlog-rules.md` (now merged).
- `DOCUMENTATION.md` — documentation format rules (YAML front matter + prose walk).
- `devlogs.md` — bullet-journal devlog, one file, append-only.
- `diagrams/` — `SVG_DIAGRAM.svg` (primary dark source, 1600×3560) + `pipeline_v2_check.png` (render check).
- `html/` — `nl2sql.html` (v2, light theme, inline SVG) + `template.html` (future renders, `%%SVG_DIAGRAM%%` placeholder).

Gitignored: `persona-*.md` (personal agent memory files, one per teammate, auto-created on clone + harness attach).

---

## 2. Content summary

**`NL2SQL-Pipeline-Architecture.md`** — Design-draft status. Core loop: query → cache check → generate SQL → validate → estimate cost/risk → route by risk tier → (human approval if needed) → execute → return. 16 stages numbered. Sub-projects: parameterized query builder, deterministic dialect converter, fuzz framework, anti-pattern detector, ER diagram generator, schema version control, index advisor. Deliberately excluded: schema-design-phase tools + ops tools. Production practices: cache-first, narrow schema, bounded retry, cost-before-execute, tiered risk, transaction+checkpoint, cross-cutting audit, readiness as governance.

**`diagrams/SVG_DIAGRAM.svg`** — 1600×3560, black `#2e2e2e` background. Miro-exported master; legend at right (translate 1104.5, 105); red-X markers near "Production database" node (rejection exit indicators); red note icons near audit/index nodes. Color coding: pink = security/cost gates, blue = pre-flight, green = human/write-path, yellow dashed = offline, gray dashed = audit.

**`diagrams/pipeline_v2_check.png`** — 1400×2045, render check of SVG (filename confirms); black bg, same node layout; used to verify before embedding.

**`html/nl2sql.html`** — Light theme, inline SVG (`viewBox="0 0 1180 2030"`), Playfair Display + Inter, stage numbers 1–16 on nodes, legend embedded at bottom (~y 1830–1978). Self-contained; opens in any browser.

**`html/template.html`** — Template for future renders; `%%SVG_DIAGRAM%%` insertion point; legend defines color/shape semantics (blue=get ready, pink=safety, green=human/write, yellow=helper, gray=record; oval=start/end, rectangle=action, diamond=decision, slanted=data, cylinder=store).

---

## 3. SVG / image — exact position + reason (required attention)

| Asset | Position / dims | Why it's there |
|---|---|---|
| `diagrams/SVG_DIAGRAM.svg` | diagrams/; 1600×3560; body translate(60,40), legend translate(1104.5,105) | Miro-exported master; dark canvas for presentation; legend separated for Confluence/PDF/email embedding; red-X near DB node for rejection exit |
| `diagrams/pipeline_v2_check.png` | diagrams/; 1400×2045 | Render verification of SVG (filename confirms); black bg; verifies before embedding |
| `html/nl2sql.html` inline | figure y~47; viewBox 0 0 1180 2030; legend y~1830 | Self-contained web document; light theme for readability; legend embedded bottom for narrow viewports |
| `html/template.html` | html/; `%%SVG_DIAGRAM%%` at section 2 | Future renders; defines color/shape semantics for both HTML versions |

---

## 4. Relationships / lineage

- `.md` (v1, mermaid) ↔ `nl2sql.html` (v2, inline SVG): same pipeline, v2 adds DBMS-mediated execution (stage 15) and splits audit into #17.
- `diagrams/SVG_DIAGRAM.svg` ↔ `diagrams/pipeline_v2_check.png`: PNG is rendered sibling of SVG (same black-theme, same node layout; 1600×3560 vs 1400×2045, aspect ~0.45).
- `html/template.html` ↔ `nl2sql.html`: template/renderer pair for v2-style output.

---

## 5. Skill context

- `ponytail` (full): ladder (YAGNI, reuse, stdlib, native, one line).
- `ponytail-audit` / `ponytail-review`: not executed on this doc (scope = over-engineering of code, not a context file); ladder applied.
- Approval policy: "never" (no escalation permitted).

---

## 6. Key exact-position takeaways (for any future edit / render)

| Asset | Exact position / dims | Reason it's at that spot |
|---|---|---|
| `diagrams/SVG_DIAGRAM.svg` | diagrams/; 1600×3560; body translate(60,40), legend translate(1104.5,105) | Miro-exported master; dark canvas for presentation; legend separated so it can be cropped; red-X markers bottom-right to indicate rejection exit from DB node |
| `diagrams/pipeline_v2_check.png` | diagrams/; 1400×2045 | Render check of SVG (filename confirms); black bg confirms same theme; used to verify before embedding |
| `html/nl2sql.html` inline | figure y~47; viewBox 0 0 1180 2030; legend y~1830 | Self-contained web document; light theme for readability; legend embedded bottom rather than side so it doesn't break narrow viewports |
| `html/template.html` | html/; `%%SVG_DIAGRAM%%` at section 2 | Template for future renders; defines color/shape semantics used by both HTML versions |

---

## 7. Team context (for `AGENT.md` / `TEAM.md` to reference)

Three third-year B.Tech CSE students on a ProjectBasedLearning (PBL) deliverable:
- **Vanshika Kriti Singh** — creative, documentation, graphic design, QA testing. Memory: `persona-vanshika.md`.
- **Anunay Sharma** — backbone, AI, LLM, ML, tech support, system design. Memory: `persona-anunay.md`.
- **Sarthak Singh** — software, algo design, socratic questioner, eager learner. Memory: `persona-sarthak.md`.

Full team structure, rotation, module division, shadow→cross phases: see `TEAM.md`. Pipeline stages mapped to teammates: see `AGENT.md`.

---

*File written: `context.md`. Rules directory (`rules/`) merged into `DESIGN.md`, `SKILL.md`, `TEAM.md`, `DOCUMENTATION.md`, and `devlogs.md`. `the-architect-agent.md` preserved as archive only (excluded from active agent governance per user correction).*
