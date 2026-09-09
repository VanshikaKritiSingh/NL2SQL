# NL2SQL Project — Shared Team Onboarding Document

**Purpose:** Before any teammate starts writing code or docs, everyone reads this once.
**Sharing:** One shared Google Doc (see link below). All three edit their own assigned section.
**Rule:** No teammate changes another teammate's section without asking.

---

## SECTION 1 — Project Overview

*Assigned to: Vanshika Kriti Singh*

### What this project is

NL2SQL is a **natural-language-to-SQL pipeline**: a person types a question in plain English, and the system returns SQL results from a database — without letting an AI agent write to the database unsupervised.

The core loop is simple:

```
query → cache check → generate SQL → validate → 
estimate cost/risk → route by risk tier → 
(human approval if needed) → execute → return results
```

Everything in this project exists to make that loop safe, fast, and auditable.

### What the pipeline does (16 stages)

| # | Stage | Why it exists |
|---|-------|---------------|
| 1 | Per-user rate / budget limiter | Blocks runaway request volume before any cost is incurred. |
| 2 | Semantic cache | Skips the full model path when a semantically equivalent query was already answered. |
| 3 | Schema linking / RAG retrieval | Narrows the schema to only the relevant tables, so the model never sees the whole database. |
| 4 | Deep learning model | Generates the candidate SQL statement. |
| 5 | Injection sanitizer | Forces parameterized queries — no raw string concatenation. |
| 6 | Dialect converter | Normalizes SQL to the target database engine (MySQL, Oracle, SQL Server, Access). |
| 7 | Static validator | Checks syntax, schema validity, and known anti-patterns. |
| 8 | Retry gate | Bounded retry loop — after N failures, escalates instead of looping. |
| 9 | Cost / risk gate | Runs EXPLAIN-style dry run to estimate rows scanned; rejects anything over threshold. |
| 10 | Risk tier router | Splits read-only queries (auto-execute against sandbox) from mutating/DDL (requires human review). |
| 11 | ER diagram / impact visualizer | Shows the reviewer what the query will actually touch before approving. |
| 12 | Human approval gate | Required only for writes/schema changes. |
| 13 | Transaction wrapper + checkpoint | Wraps approved writes in a transaction with a rollback point. |
| 14 | Schema version control | Tracks every schema/data change like a migration log. |
| 15 | Audit log | Cross-cutting log — every stage writes to it, not a pass-through stage. |
| 16 | Formatted response | Returns results to the user. |

### What this project is NOT building

The following were **explicitly excluded** (good tools, wrong pipeline):
- Automated relational schema design from ER diagrams
- Denormalization advisor, normalization pipeline
- Database workload re-player, schema-drift detector
- Vector index extension, warehouse-free analytics dashboard

These are schema-design or ops tools — orthogonal to the NL2SQL agent goal.

### Key constraints every teammate should know

- **Safety gates are non-negotiable.** Stages 1, 5, 7, 8, 9, 10, 12 form layered guardrails — never skip or weaken them to ship faster.
- **No AI ever writes to the database unsupervised.** Human approval (stage 12) is the hard boundary. Stage 10 (risk tier router) enforces it.
- **Cache before you generate.** Stage 2 is the first thing checked on every query.
- **Cost before execution.** Stage 9 estimates before any query runs against a live DB.
- **Audit everything.** The audit log (stage 15) is a side-channel — every stage writes to it, no exceptions.

### What to write in this section

Write 2–3 paragraphs covering: what the system does, who uses it, and the one-sentence version of the core loop above. Use plain language — a new developer reading this should immediately understand what problem we are solving.

**Hint (from context.md):** Production NL2SQL systems succeed or fail less on raw SQL-writing ability and more on business context, query governance, and iterative follow-up support. Emphasize this in your description.

---

## SECTION 2 — Tech Stack

*Assigned to: Anunay Sharma*

### AI / LLM Layer

- **Deep learning model** (stage 4): Generates SQL from natural language. Model selection is not finalized — document the decision criteria here (latency, cost, accuracy, schema coverage).
- **RAG retrieval** (stage 3): Schema linking uses a retrieval-augmented generation approach. Stores database metadata as embeddings to pull only relevant tables into the prompt.
- **Semantic cache** (stage 2): Compares incoming query embeddings against previously answered queries; returns cached response on high-confidence match. Skips the entire model + validation path.
- **Embedding model**: Document which embedding model is used for semantic similarity and schema linking.

### Core Pipeline Components

- **Parameterized query builder / injection sanitizer** (stage 5): Rewrites all generated SQL through a safe query builder — no raw string concatenation. Rejects any attempt to interpolate raw literals.
- **Dialect converter** (stage 6): Parses SQL into an AST, applies deterministic, rule-based transformations to normalize to the target DBMS. Must produce identical output for identical input.
- **Static validator** (stage 7): Runs syntax checks, schema validity checks, and anti-pattern detection before anything is costed.
- **Cost estimator** (stage 9): Uses EXPLAIN-style dry runs to estimate rows scanned and query cost; rejects or escalates anything over the configured threshold.

### Database Layer

- **Target DBMSs**: MySQL, Oracle, SQL Server, Access — the system must work across all four.
- **Read-only sandbox replica** (stage 10): Read-only queries run against a sandboxed replica, never the production DB.
- **Production DB** (stage 15): Only reached after human approval (stage 12) and transaction wrapper (stage 13).
- **Schema version control** (stage 14): Versions schema changes like a VCS, generating migration scripts and enabling rollback.

### Offline / Background Tools (side-channels)

- **Fuzz testing harness**: Grammar-based fuzzer that generates valid, edge-case, and malformed queries against a sandboxed instance to catch validator gaps. Runs continuously offline.
- **Schema anti-pattern detector**: Parses DDL and information_schema metadata, runs rule-based checks against known bad patterns (EAV misuse, generic polymorphic columns, missing FKs).
- **ER diagram generator**: Parses CREATE TABLE statements, builds a table/FK graph, renders it visually. Powers the human review step (stage 11).
- **Index / covering-index advisor**: Reads workload telemetry and execution plans, suggests composite indexes. Feeds tuning hints back into schema linking (stage 3).

### Languages and Frameworks

Document here:
- Primary language(s) used (Python is the likely choice for ML + DB tooling)
- Key libraries (SQL parser, ORM, web framework, embedding/vector library)
- Testing framework
- CI/CD setup (if any)

### Infrastructure

- Audit log / observability store: Every stage writes to it. Document the schema here.
- Rate/budget limiter: Per-user limits on request volume and cost.

### What to write in this section

List every technology used, grouped by layer (AI, core pipeline, database, offline tools, infra). For each item, give: what it is, which pipeline stage it belongs to, and one sentence on why it was chosen. If a decision is not finalized, note it as **open — pending decision** with the alternatives considered.

**Hint (from context.md / AGENT.md):** Anunay owns model selection, RAG design, schema linking, audit-log schema, and stages 1/3/4/5/14/16. Make sure every component he owns is documented here with enough detail for Sarthak to implement the software side without asking questions.

---

## SECTION 3 — Developer Guide

*Assigned to: Sarthak Singh*

### Module ownership map

Each teammate owns specific pipeline stages. Before asking someone a question, check this map — they may already own the answer.

| Teammate | Pipeline stages | Module |
|---|---|---|
| Vanshika | — | Design direction, color/typography, diagram edits, devlog copy, QA pass |
| Anunay | 1, 3, 4, 5, 14, 16 + audit side-channel | Rate limiter, RAG, schema linking, model integration, version control, response formatting, audit schema |
| Sarthak | 6, 7, 8, 9, 10, 11, 13 + offline side-channel | Dialect converter, validator, retry gate, cost estimator, risk router, ER visualizer, transaction wrapper, fuzz harness, index advisor, anti-pattern detector |

### How the pipeline runs end-to-end

Walk through the path a read query takes vs. a write query:

**Read query path:**
```
User query → rate limiter (1) → cache check (2) → 
schema linking (3) → model (4) → sanitizer (5) → 
dialect converter (6) → validator (7) → retry gate (8) → 
cost gate (9) → risk router: read-only → sandbox replica → 
formatted response (16) → User
```

**Write/mutating query path:**
```
User query → rate limiter (1) → cache check (2) → 
schema linking (3) → model (4) → sanitizer (5) → 
dialect converter (6) → validator (7) → retry gate (8) → 
cost gate (9) → risk router: mutating → 
ER visualizer (11) → human approval (12) → 
transaction wrapper (13) → schema version control (14) → 
production DB (15) → formatted response (16) → User
```

The audit log (15) and offline tools write in the background — they are not in the request path.

### What to implement first (phasing)

**Day one (cheap to build, removes entire risk classes):**
- Per-user rate limiter
- Parameterized query builder / injection sanitizer
- Read-only sandbox replica
- Bounded retry gate

**Fast-follow (needs real query volume to tune thresholds):**
- Semantic cache (similarity threshold tuning)
- Cost/EXPLAIN gate (threshold calibration)
- Index advisor (needs workload telemetry)

**Ongoing / offline:**
- Fuzz testing harness against the validator
- Schema anti-pattern detector as a scheduled review job

### Anti-patterns to guard against

These patterns are explicitly blocked by the validator and anti-pattern detector — document them so the team knows what NOT to write:

- **EAV misuse**: Entity-Attribute-Value pattern that stores typed data generically (e.g., rows with columns `attribute_name`, `attribute_value`) — loses type safety and query performance.
- **Generic polymorphic columns**: Columns named `type`, `category`, `flag` that hold different data types depending on context — makes schema validation impossible.
- **Missing foreign keys**: Tables that logically reference other tables but have no FK constraint — the validator catches this on DDL review.
- **Raw string interpolation in SQL**: Any attempt to concatenate user input directly into a query string — the sanitizer blocks this at stage 5.

### Design rules every developer must follow

From DESIGN.md (anti-slop rules — these are not suggestions):

**Text rules:**
- No: *delve into, moreover, furthermore, robust, seamless, holistic, leverage (as a verb), in today's fast-paced world, unlock the power of*
- No rule-of-three reflex — if three is right, use three; if not, don't force it
- No closing paragraph that restates instead of adding a final point
- No "ultimately, it depends" when the piece built toward a real position
- No confident claims with invisible sourcing ("research shows" with no study named)

**Design rules:**
- No cream/terracotta palette default (#F4F1EA + #D97757) — this is the most common AI design tell
- No SaaS card kit — identically rounded cards with the same shadow everywhere
- No ALL-CAPS eyebrow labels above headings, no tracked-out labels, no em-dash label format
- No sequence numbers (01/02/03) on content that is not an ordered process
- Binary states (pass/fail, before/after) use the same two ink colors — do not add a third color for routine variety

**HTML documentation (if applicable):**
- Duotone palette: two ink colors plus tints only — not a rainbow of accents
- Fraunces (or Playfair Display) + Inter typography pairing
- Contrast ratio ≥ 4.5:1 for body text

### Commit and devlog conventions

- A **work-day** = one commit or log entry to the repo. After 2 work-days, the teammate rotation swaps.
- Every entry in `devlogs.md` must show all three teammates — even if one did nothing that day, write `Vanshika — off`, etc.
- Devlog entry shape:
  ```
  ## YYYY-MM-DD — short title, sentence case
  
  Vanshika — one line on what she did
  Anunay — one line
  Sarthak — one line
  Learnings — one line per teammate who has one; skip if none
  Blockers — one line, or "none"
  Pipeline stage(s) touched — number(s) or "none"
  Arrange differently next time — one line, or "no change"
  ```
- **Checkpoints** are triggered by: "checkpoint", "what did we learn", "wrap up", "done for today", "logging out" — the agent asks four questions in order before writing the log.

### Testing strategy

- Fuzz testing runs continuously offline against the validator (stage 7).
- Schema anti-pattern detector runs as a scheduled review job, not in the request path.
- QA pass (Vanshika's responsibility): verify the diagram renders correctly in all target formats (SVG, HTML, Confluence, plain PDF).

### What to write in this section

Write a developer-facing guide covering: module ownership, the two pipeline paths (read vs. write), implementation phasing, blocked anti-patterns, the anti-slop rules they must follow in all code and docs, and commit/devlog conventions. This is the section a developer should read the morning they start working and understand exactly what to do and where to put it.

**Hint (from context.md):** Sarthak owns validator rules, dialect converter logic, fuzz harness, cost estimation, and index advisor. Make sure the sections on the validator, dialect converter, and anti-pattern detector are detailed enough that Anunay can integrate them without needing to ask questions.

---

## SECTION 4 — Architecture Diagram Reference

*All three teammates — place shared link here*

**SVG source:** `diagrams/SVG_DIAGRAM.svg` (1600×3560, dark canvas, Miro-exported master)
**HTML preview:** `html/nl2sql.html` (light theme, inline SVG, self-contained)
**PNG render check:** `diagrams/pipeline_v2_check.png` (1400×2045, verifies SVG renders correctly)

**Shared Google Doc link:** [paste link here]

### Color legend

| Color | Meaning | Example nodes |
|---|---|---|
| Blue | Pre-flight / context retrieval | Cache, Schema linking |
| Pink | Security / cost gates | Rate limiter, Sanitizer, Cost gate |
| Green | Human-facing / write-path tooling | ER visualizer, Human approval, Version control |
| Yellow dashed | Offline background support | Fuzz harness, Index advisor |
| Gray dashed | Cross-cutting audit | Audit log |

### Shape legend

| Shape | Meaning |
|---|---|
| Oval | Start / end |
| Rectangle | Action |
| Diamond | Decision / gate |
| Slanted rectangle | Data store |
| Cylinder | Database |

---

## SECTION 5 — Decisions Still Open

*All three teammates — fill in as the project progresses*

| Decision | Options considered | Owner | Status |
|---|---|---|---|
| Which LLM model to use | — | Anunay | Open |
| Which embedding model for RAG | — | Anunay | Open |
| Which SQL parser library | — | Sarthak | Open |
| Cost gate threshold values | — | Sarthak | Open |
| Cache similarity threshold | — | Anunay | Open |
| Target DBMS (which to prioritize first) | MySQL / Oracle / SQL Server / Access | Anunay | Open |
| HTML documentation palette | Ink & Ember vs. Umber & Brass | Vanshika | Open |

Add rows as decisions are made.

---

## SECTION 6 — Meeting and Rotation Log

*All three teammates — update weekly*

| Week | Active teammate | Domain focus | Key decisions |
|---|---|---|---|
| 1 | — | — | — |
| ... | — | — | — |

**Rotation order:** Vanshika → Anunay → Sarthak → (repeat)
**Domain rotation:** Design → AI → Software → (repeat)

Each teammate works in 2-day blocks. After their block, they write one teach-back line in the devlog so the others know what they learned.

---

*Last updated: 2026-09-01*
*Next review: after week 1 checkpoint*
