# SKILL.md — skills the agent uses in this repo

Three skills, each tied to a teammate's domain. Governed by `DESIGN.md` (anti-slop + design spec + devlog rules) and `TEAM.md` (personas + rotation). Load order: DESIGN.md first → domain skill → cross-domain split.

---

## 1. Anti-slop craft (cross-cutting — all 3 teammates)

**Source:** `DESIGN.md` (Part 1 text, Part 2 design, Part 4 Devil's Advocate, devlog rules). Load it, do not paraphrase it.

**What it covers here:**
- All prose in `.md` files, `nl2sql.html`, `template.html`, devlog entries (`devlogs.md`), `AGENT.md`, `TEAM.md`, `SKILL.md`, `CONTEXT.md`, `DOCUMENTATION.md`.
- All visual decisions in `SVG_DIAGRAM.svg`, inline SVG in `nl2sql.html`, and any future rendered HTML documentation.
- Devil's Advocate self-review (Part 4) before every deliverable: steelman the draft → weakest element → checklist review → fatal-flaw veto (hedge-closer / fabricated citation / cream-terracotta default = automatic fail) → one honest remaining weakness named to user.

**Why it exists here:** Vanshika owns creative + documentation. Anti-slop is her craft made enforceable for the agent.

**Ponytail check:** `DESIGN.md` is the single source; no duplication in this file. The anti-slop rules are enforced by reference, not copy.

---

## 2. NL → SQL pipeline craft (Anunay's domain — rotation Design → AI → Software → Design)

Used on stages 1, 3, 4, 5, 14, 16, and the audit side-channel:

- Rate / budget limiting — token bucket per user, hard cap before model call, soft cap before DBMS.
- Semantic cache — query embedding + normalized-SQL key; cache hit short-circuits stages 4–15.
- Schema linking / RAG — embed schema fragments, retrieve top-k by query similarity, pass as context to model; never dump full schema.
- Model prompting — system prompt pins dialect, schema snapshot, parameter style; user prompt carries only the natural-language query + retrieved context.
- Response shaping — return rows + explanation + applied-parameter map, not raw SQL alone.
- Audit logging — every stage decision logged with input hash, decision, cost, latency. Cross-cutting, dashed in the diagram for a reason.

**Why it exists here:** these are the AI/LLM skills the project was approved on. Anything outside this list is out of scope per `NL2SQL-Pipeline-Architecture.md`.

---

## 3. Algorithmic validation craft (Sarthak's domain — same rotation cycle)

Used on stages 6, 7, 8, 9, 10, 11, 13, and the offline side-channel (fuzz + anti-pattern + index advisor):

- Parameterized query building — never string-concat user input; bind parameters, escape identifiers.
- Deterministic dialect conversion — pure function, no LLM in the loop; test fixtures per (source dialect × target dialect).
- Static validation — parse, type-check, identifier-resolution, deny-list (DROP, TRUNCATE outside admin role, etc.).
- Cost / scan estimation — EXPLAIN or dialect equivalent; reject plans above a scan-row threshold before stage 10.
- Risk tiering — read-only / single-statement-mutating / multi-statement / DDL — each tier has a fixed downstream path.
- Transaction wrapper — BEGIN, run, validate affected rows, COMMIT or ROLLBACK; checkpoint on every COMMIT.
- Fuzz harness — generate malformed NL queries, verify pipeline fails closed (no DB write, no leak).
- Anti-pattern detector — flag SELECT *, missing WHERE on UPDATE/DELETE, implicit type coercion in JOIN.
- Index advisor — read recent slow-query log, suggest covering indexes, never auto-apply.

**Why it exists here:** these are the deterministic, testable skills. Socratic questioner mode applies here — when given an algo claim, the agent asks "what would falsify this?" before agreeing.

---

## Skill loading order

1. Load `DESIGN.md` (governs everything below). No `rules/` directory — content merged.
2. Load the domain skill (§2 or §3) the current stage belongs to. Don't load both at once — they don't compose.
3. Cross-domain question (e.g., cost gate + RAG) → load both, split the answer along the seam; don't blend answers.
4. Before delivery → `DESIGN.md` Part 4 (Devil's Advocate). Always. No skip.

---

*Ponytail skip: no separate skill files per stage, no skill registry, no metadata block. Three sections, three teammates, one pointer to `DESIGN.md` (merged from `rules/anti-slop-craft-SKILL.md`). `rules/devlog-rules.md` merged into `DESIGN.md` (devlog section) and `devlogs.md` (first entry).* 
*`the-architect-agent.md` excluded from agent governance per user correction (archive only).*
