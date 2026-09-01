# DOCUMENTATION.md — project handbook

Hybrid: machine-readable first (a structured block agents and tools can parse), human-readable second (prose for evaluators, onboarding, and team review). Documentation is a field of digital labour — the human's job is to review, correct, modify, not to re-derive from prose.

The anti-slop rules in `rules/anti-slop-craft-SKILL.md` apply to the prose sections. No slop in this file.

---

## Machine-readable block (do not edit casually)

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
  - path: Projects.pdf
    kind: pdf
    status: uninspected
architecture_docs:
  - NL2SQL-Pipeline-Architecture.md
  - NL2SQL-Pipeline-Architecture (1).md  # duplicate (3s gap), kept for review
context_index: context.md
agent_profile: AGENT.md
skill_profile: SKILL.md
devlog_rules: rules/devlog-rules.md
anti_slop_rules: rules/anti-slop-craft-SKILL.md
out_of_pipeline_scope:
  - schema-design-phase tools
  - ops tools
```

---

## Human-readable walkthrough

### What this project is

A pipeline that takes a natural-language question, produces a parameterized SQL query, validates it, estimates its cost, routes it by risk, optionally asks a human to approve, and executes it inside a transaction against the user's DBMS. The full 16-stage flow and the four side-channels (audit, index advisor, fuzz harness, anti-pattern detector) are documented in `nl2sql.html` and `SVG_DIAGRAM.svg`.

### Who built it

Three third-year B.Tech CSE students working on a PBL deliverable. Roles above. The split is by craft, not by seniority — Vanshika owns visual + QA, Anunay owns model + system, Sarthak owns algo + software. The agent (`AGENT.md`) maps each pipeline stage to whichever teammate's craft it touches.

### How to read this repo

1. `context.md` — start here. Index of every file, exact positions of the SVG and the rendered PNG, color/shape legend semantics.
2. `nl2sql.html` — the pipeline as a self-contained webpage (light theme, inline SVG, embedded legend).
3. `SVG_DIAGRAM.svg` — the master diagram (dark theme, Miro-exported, 1600×3560). Use this in tools that can't render Mermaid (Confluence, PDF, email).
4. `pipeline_v2_check.png` — rendered check of the SVG. Same dark theme, 1400×2045. Filename confirms it was a pre-embed verification.
5. `template.html` — the renderer template for future docs; defines the legend semantics used everywhere.
6. `NL2SQL-Pipeline-Architecture.md` (and its `(1).md` near-duplicate) — the prose architecture spec with the mermaid flowchart.
7. `Projects.pdf` — uninspected; likely the PDF counterpart to the architecture doc.
8. `AGENT.md` / `SKILL.md` — what the agent does here and what skills it uses.
9. `rules/` — anti-slop craft + devlog rules. The agent reads these before producing anything.
10. `devlogs.md` — the team's running log, one file, one shape, three-member view per entry.

### What is and is not in scope

In scope: stages 1–16 + the four side-channels. Out of scope (deliberately excluded in the architecture doc): schema-design-phase tools, ops tools. If a proposed feature fits "design a new table" or "run the production deploy," it does not belong in this project.

### One honest remaining weakness

`Projects.pdf` has not been inspected. If it carries material not duplicated in the `.md` files, the index in `context.md` is incomplete. The fix is a 5-minute read pass, not a redesign — and it should happen before the next evaluator review.
