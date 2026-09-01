# TEAM.md — how the three teammates work together

One file, all three views. No separate per-member files (ponytail). All prose follows anti-slop rules (see SKILL.md §1, DESIGN.md). The agent never invents a teammate's contribution.

---

## 1. Three teammates (names + craft + voice)

Each has a private persona agent (`persona-{name}.md`, repo root, gitignored, auto-created on clone + harness attach). The agent adopts their voice in text; the domain expert agent handles the module.

- **Vanshika Kriti Singh** — creative, documentation, graphic design, QA testing. Persona: editorial, visual, precise. Owns: `design/` direction, color/typography choices, diagram edits, devlog copy, QA pass. Memory: `persona-vanshika.md`.
- **Anunay Sharma** — backbone, AI / ML / LLM, tech support, system design. Persona: analytical, structured, cautious. Owns: model selection, RAG design, schema linking, audit-log schema, pipeline stages 1/3/4/5/14/16 and audit side-channel. Memory: `persona-anunay.md`.
- **Sarthak Singh** — software, algo design, socratic questioner, eager learner. Persona: probing, concise, step-by-step. Owns: validator rules, dialect converter (pure function), fuzz harness, cost estimation, index advisor, stages 6/7/8/9/10/11/13 and offline side-channel. Memory: `persona-sarthak.md`.

Full transparency: all three see all work (devlogs, commits, design notes). No hidden lanes.

---

## 2. Agent architecture (6 agents, hybrid)

Two agent types, loaded together per session (2 per turn):

- **Personal agent** (3 total, private): adopted by the teammate whose turn it is. Uses their persona voice from `persona-{name}.md`. Not committed to `main`; lives on the teammate's local harness + memory file. Updates after each chat session.
- **Domain expert agent** (3 total, shared, committed): Design / AI / Software. Each is a single shared instance so concurrent work in the same domain stays in sync; rotation prevents concurrent development on one field.

Per-session load (2 agents):
- If it is Vanshika's turn → load `Vanshika-persona` + whichever domain the rotation calls (Design → AI → Software → Design).
- If it is Anunay's turn → load `Anunay-persona` + rotating domain agent.
- If it is Sarthak's turn → load `Sarthak-persona` + rotating domain agent.

No harness directory needed (per user confirmation); persona notes go in `devlogs.md` and `persona-{name}.md`.

---

## 3. Rotation (round-robin, 2-day cycle)

Trigger: a work-day = one commit / log entry to the repo. After 2 such days, the teammate swaps to the next in the cycle. The domain expert also rotates independently (Design → AI → Software → Design). The cyclic design means no two teammates work in the same domain at once.

Order (personas): Vandshika → Anunay → Sarthak → Vanshika ...
Order (domains): Design → AI → Software → Design ...

Example cycle:
- Day 1 (V's turn, Design domain): Vanshika-persona + Design-expert. Module: pipeline design + legend + SVG edits.
- Day 2 (V's turn, Design): continue.
- Day 3 (A's turn, AI): Anunay-persona + AI-expert. Module: RAG / cache / model prompt.
- Day 4 (A's turn, AI): continue.
- Day 5 (S's turn, Software): Sarthak-persona + Software-expert. Module: validator / dialect / fuzz.
- Day 6 (S's turn, Software): continue.
- Day 7 (V's turn, AI): Vanshika-persona + AI-expert. Cross-train: creative work on AI-module documentation.

Swap (informal): a teammate can mention in the group chat (or devlogs.md) that they want to move a module slice to another teammate. No formal gate; domain expert approves only if it doesn't break the rotation (no concurrent same-domain work).

---

## 4. Module division (brainstorm → split → rotate)

Initiated by the domain expert of the active domain for that session.

1. **Brainstorm** (domain expert + all 3): divide the domain's pipeline stage(s) into module slices. Example: Design = legend + SVG + HTML theme + card layout.
2. **Split**: equal-sized slices assigned to the 3 teammates, regardless of primary craft. The domain expert keeps a heavier slice.
3. **Implementation**: each teammate works their slice in 2-day blocks, with their persona agent + the domain expert agent.
4. **Mix / cross-train**: after the initial division, slices are redistributed so everyone touches Design + AI + Software modules over the cycle.

No factory / no interface. When a module needs documentation or design, the active teammate's persona agent writes it, guided by the domain expert agent.

---

## 5. Phase: shadow → cross-train

- **Shadow** (early): all three discuss each domain; domain expert leads; team observes and asks questions (socratic mode — Sarthak's craft, applied to everyone).
- **Active / implementation** (after module division): each teammate leads their slice in their turn; cross-training begins because slices move across domains.
- **Teach-back** (after rotation): the teammate who just worked a domain explains it to the others (one line in devlog or brief note), so nothing stays silenced.

---

## 6. Conflict resolution

If persona agent and domain agent disagree, the teammate decides (confirmed by user). The agent surfaces both positions plainly; never closes with "ultimately, it depends" — either pick, or name an experiment.

No `architect-agent.md` usage (explicit user correction; file is excluded from this repo's working rules — see `the-architect-agent.md` in archive only, not referenced in AGENT.md / SKILL.md / CONTEXT.md).

---

## 7. Devlog format (from `devlog-rules.md` — see SKILL.md §1, DOCUMENTATION.md)

Every entry: 5 lines (date + 3 teammate lines + learnings + blockers + stage + arrange). All 3 members always present (`Vanshika — ...`, `Anunay — ...`, `Sarthak — ...`). No rule-of-three inside any line. No banned words (`delve`, `robust`, `seamless`, `leverage`). Date in ISO; title sentence case; no emoji / all-caps / em-dash label format.

Checkpoint triggers (user decides — never auto-prompts): "checkpoint", "what did we learn", "wrap up", "done for today", "logging out". Four questions asked in order: what did you do, what did you learn, what would you arrange differently, whose work touched this.

If partial, log `(not captured)`; never invent.

---

## 8. Design rules reference

Anti-slop (Part 1 text, Part 2 design, Part 3 HTML spec, Part 4 Devil's Advocate) lives in `DESIGN.md`. `SKILL.md` points to it. The agent runs Part 4 (steelman → weakest element → Part 1/2 checklist → fatal-flaw veto → one honest weakness) before delivering anything that touches text or design.

Color / typography rules (duotone: Ink & Ember OR Umber & Brass; Fraunces + Inter; binary encoding for states; contrast ≥ 4.5:1): see DESIGN.md §Palette / §Typography.

---

*Written: TEAM.md. Source rules (`rules/`) merged into DESIGN.md (design + anti-slop Part 2/3), SKILL.md (skill load + anti-slop Part 1 reference), DOCUMENTATION.md (devlog rules + documentation spec), and devlogs.md (first entry 2026-07-10).* 
*Rules directory removed after content verified; `the-architect-agent.md` preserved as archive reference only (not active)."
