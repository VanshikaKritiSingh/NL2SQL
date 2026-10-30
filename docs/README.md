# docs/ — Documentation Index

> Auto-generated index. All renamed files follow the convention:
> `YYYY-MM-DD_<title>_[STATUS_<DONE|ACTIVE|IN_PROGRESS|PARTIAL|OPEN|SUPERSEDED>].<ext>`

---

## Checklists

| File | Created | Status | Purpose |
|---|---|---|---|
| [`checklists/2026-10-30_developer_todo_checklist_[STATUS_ACTIVE].md`](checklists/2026-10-30_developer_todo_checklist_[STATUS_ACTIVE].md) | 2026-10-30 | **ACTIVE** | Developer action plan derived from adversarial & ponytail audits. 41 tasks across Fix, Implement, Alternative, and Delete categories. |

**Quick alias:** [`DEVELOPER_CHECKLIST.md`](DEVELOPER_CHECKLIST.md)

---

## Reviews / Audits

| File | Created | Status | Purpose |
|---|---|---|---|
| [`reviews/2026-10-29_adversarial_and_ponytail_audit_[STATUS_OPEN].md`](reviews/2026-10-29_adversarial_and_ponytail_audit_[STATUS_OPEN].md) | 2026-10-29 | **OPEN** | Complete Devil's Advocate + Ponytail audit. 29 correctness flaws + 15 over-engineering targets. All findings must be resolved before production. |
| [`reviews/2026-10-12_pipeline_design_analysis_[STATUS_SUPERSEDED].md`](reviews/2026-10-12_pipeline_design_analysis_[STATUS_SUPERSEDED].md) | 2026-10-12 | **SUPERSEDED** | Early pipeline design analysis (superseded by the 2026-10-29 adversarial audit). |

**Quick aliases:** [`reviews/audit.md`](reviews/audit.md) · [`reviews/devils_advocate_audit.md`](reviews/devils_advocate_audit.md)

---

## Implementation Plans

| File | Created | Status | Purpose |
|---|---|---|---|
| [`plans/2026-10-04_decided_modules_and_implementation_plan_[STATUS_PARTIAL].md`](plans/2026-10-04_decided_modules_and_implementation_plan_[STATUS_PARTIAL].md) | 2026-10-04 | **PARTIAL** | Module decision records and initial implementation plan. Sections for fine-tuning and cost estimation still pending. |

**Quick alias:** [`DECIDED_MODULES.md`](DECIDED_MODULES.md)

---

## Guides

| File | Created | Status | Purpose |
|---|---|---|---|
| [`guides/2026-10-04_gui_integration_guide_[STATUS_DONE].md`](guides/2026-10-04_gui_integration_guide_[STATUS_DONE].md) | 2026-10-04 | **DONE** | Frontend/Backend WebSocket and REST integration guide for the React/Vite GUI. |
| [`guides/2026-10-12_connectors_quickstart_guide_[STATUS_DONE].md`](guides/2026-10-12_connectors_quickstart_guide_[STATUS_DONE].md) | 2026-10-12 | **DONE** | Quickstart for connecting to supported relational databases. |
| [`guides/2026-10-12_model_fine_tuning_guide_[STATUS_IN_PROGRESS].md`](guides/2026-10-12_model_fine_tuning_guide_[STATUS_IN_PROGRESS].md) | 2026-10-12 | **IN_PROGRESS** | Full QLoRA fine-tuning walkthrough. Loss masking still incomplete — see FIX-10 in checklist. |

**Quick aliases:** [`GUI_INTEGRATION_GUIDE.md`](GUI_INTEGRATION_GUIDE.md) · [`CONNECTORS_QUICKSTART.md`](CONNECTORS_QUICKSTART.md) · [`FINE_TUNE_GUIDE.md`](FINE_TUNE_GUIDE.md)

---

## Reports

| File | Created | Status | Purpose |
|---|---|---|---|
| [`reports/2026-10-05_phase-1_pbl_evaluation_report_[STATUS_DONE].pdf`](reports/2026-10-05_phase-1_pbl_evaluation_report_[STATUS_DONE].pdf) | 2026-10-05 | **DONE** | Phase I PBL evaluation slideshow PDF. |

**Quick alias:** [`Phase-I_PBL_Evaluation.pptx.pdf`](Phase-I_PBL_Evaluation.pptx.pdf)

---

## Architecture References (Unversioned, Living Documents)

| File | Description |
|---|---|
| [`NL2SQL-Pipeline-Architecture.md`](NL2SQL-Pipeline-Architecture.md) | Stage-by-stage pipeline text specification. Companion to SVG diagram below. Created: 2026-09-01 |
| [`DOCUMENTATION.md`](DOCUMENTATION.md) | Registry of all documentation files with paths and descriptions. |
| [`context.md`](context.md) | Team context notes and consolidated file list. |
| [`skill.md`](skill.md) | Devil's Advocate review skill configuration. |

---

## Diagrams & Visuals

| File | Description |
|---|---|
| [`diagrams/SVG_DIAGRAM.svg`](diagrams/SVG_DIAGRAM.svg) | 1600×3560 master architecture blueprint (vector). Created: 2026-09-01, Updated: 2026-10-16 |
| [`diagrams/pipeline_v2_check.png`](diagrams/pipeline_v2_check.png) | High-res PNG raster render for markdown/previews. Created: 2026-09-01 |
| [`diagrams/compressed_overview.html`](diagrams/compressed_overview.html) | Compressed interactive pipeline overview. Created: 2026-10-16 |

---

## HTML Specs

| File | Description |
|---|---|
| [`html/nl2sql.html`](html/nl2sql.html) | Interactive 16-stage pipeline HTML spec. Created: 2026-09-01 |
| [`html/template.html`](html/template.html) | Design system typography and layout tokens. Created: 2026-09-01 |
| [`html/DesignWorkbench.html`](html/DesignWorkbench.html) | Design workbench prototype. Created: 2026-10-12 |

---

## Status Legend

| Badge | Meaning |
|---|---|
| `[STATUS_ACTIVE]` | Currently being worked on — tasks pending |
| `[STATUS_OPEN]` | Findings exist, remediation not yet started |
| `[STATUS_IN_PROGRESS]` | Partially complete, active development |
| `[STATUS_PARTIAL]` | Some sections done, others deferred |
| `[STATUS_DONE]` | Fully complete, no follow-up needed |
| `[STATUS_SUPERSEDED]` | Replaced by a newer document; kept for historical reference |
