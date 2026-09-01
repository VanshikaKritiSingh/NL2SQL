# devlogs.md — team log, append-only

Format governed by `DESIGN.md` (devlog rules section) and `TEAM.md`. Trigger: user says "checkpoint" / "wrap up" / "done for today" / "what did we learn". Agent asks the four reflection questions (what done, what learned, arrange differently, whose work) before writing. No auto-prompt on session close.

---

## 2026-07-10 — repo documentation and agent profile setup

**Vanshika** — added `AGENT.md` (pipeline-stage mapping to team), `DOCUMENTATION.md` (machine-readable + human-readable block), `SKILL.md` referencing anti-slop; reviewed palette/design rules.
**Anunay** — defined pipeline stage mapping (1–16 + 4 side-channels); owned the machine-readable YAML block in `DOCUMENTATION.md`; mapped LLM/RAG stages.
**Sarthak** — structured the three-member view rule into `devlog-rules.md`; designed bullet format with stage links; added reflection trigger (operator-initiated, not automatic).

**Learnings** — Documentation can be machine-first and stay readable. Anti-slop craft rules (`DESIGN.md`) govern both prose and design; they do not need duplication in `AGENT.md` / `SKILL.md`. Devlog format needs three lines per entry, always.
**Blockers** — `Projects.pdf` uninspected; `NL2SQL-Pipeline-Architecture (1).md` near-duplicate kept for review (no deletion per request).
**Pipeline stage(s) touched** — 0 (docs / meta; no pipeline execution).
**Arrange differently next time** — Read `Projects.pdf` before finishing first checkpoint; decide whether duplicate `.md` should stay or be merged.

---

To checkpoint: say "checkpoint", "wrap up", "done", or "what did we learn". The agent will ask, then log here — never fabricate the four answers.
