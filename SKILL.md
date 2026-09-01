# SKILL.md — skills the agent uses in this repo

Three skills, each tied to a teammate's domain. None of these are generic "AI skills" — they are the working craft this project actually needs. Governed by `rules/anti-slop-craft-SKILL.md` and `rules/devlog-rules.md`.

## 1. Anti-slop craft (cross-cutting)

**Source:** `rules/anti-slop-craft-SKILL.md` — load it, do not paraphrase it.

**What it covers here:**
- All prose in `.md`, `nl2sql.html`, `template.html`, devlog entries, and AGENT/SKILL/CONTEXT/DOCUMENTATION files.
- All visual decisions in `SVG_DIAGRAM.svg`, the inline SVG in `nl2sql.html`, and any future rendered HTML documentation.
- Devil's Advocate self-review (Part 4) before every deliverable.

**Why it exists here:** Vanshika owns creative + documentation. Anti-slop is her craft made enforceable for the agent.

**Ponytail check:** the rule file already exists. This SKILL.md only points to it — no copy of the rules here.

## 2. NL → SQL pipeline craft (Anunay's domain)

Skills the agent uses when working on stages 1, 3, 4, 5, 14, 16, and the audit side-channel:

- **Rate / budget limiting** — token bucket per user, hard cap before model call, soft cap before DBMS.
- **Semantic cache** — query embedding + normalized-SQL key; cache hit short-circuits stages 4–15.
- **Schema linking / RAG** — embed schema fragments, retrieve top-k by query similarity, pass as context to model; never dump full schema.
- **Model prompting** — system prompt pins dialect, schema snapshot, parameter style; user prompt carries only the natural-language query + retrieved context.
- **Response shaping** — return rows + explanation + applied-parameter map, not raw SQL alone.
- **Audit logging** — every stage decision logged with input hash, decision, cost, latency. Cross-cutting, dashed in the diagram for a reason.

**Why it exists here:** these are the AI/LLM skills the project was approved on. Anything outside this list is out of scope per the architecture doc.

## 3. Algorithmic validation craft (Sarthak's domain)

Skills the agent uses when working on stages 6, 7, 8, 9, 10, 11, 13, and the offline side-channel (fuzz + anti-pattern + index advisor):

- **Parameterized query building** — never string-concat user input; bind parameters, escape identifiers.
- **Deterministic dialect conversion** — pure function, no LLM in the loop; test fixtures per (source dialect × target dialect).
- **Static validation** — parse, type-check, identifier-resolution, deny-list (DROP, TRUNCATE outside admin role, etc.).
- **Cost / scan estimation** — EXPLAIN or dialect equivalent; reject plans above a scan-row threshold before stage 10.
- **Risk tiering** — read-only / single-statement-mutating / multi-statement / DDL — each tier has a fixed downstream path.
- **Transaction wrapper** — BEGIN, run, validate affected rows, COMMIT or ROLLBACK; checkpoint on every COMMIT.
- **Fuzz harness** — generate malformed NL queries, verify pipeline fails closed (no DB write, no leak).
- **Anti-pattern detector** — flag SELECT *, missing WHERE on UPDATE/DELETE, implicit type coercion in JOIN.
- **Index advisor** — read recent slow-query log, suggest covering indexes, never auto-apply.

**Why it exists here:** these are the deterministic, testable skills. Socratic questioner mode applies here — when given an algo claim, the agent asks "what would falsify this?" before agreeing.

## Skill loading order

1. Load `rules/anti-slop-craft-SKILL.md` first (governs everything below).
2. Load `rules/devlog-rules.md` (governs logging cadence).
3. Load only the domain skill (2 or 3) the current stage belongs to. Don't load both at once — they don't compose.
4. Cross-domain question (e.g., cost gate + RAG) → load both, but split the answer along the seam.

Ponytail skip: no separate skill files per stage, no skill registry, no metadata block. Three sections, three teammates, one pointer to the rules directory.
