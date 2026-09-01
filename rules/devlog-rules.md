# devlog-rules.md — how the agent logs work

This file governs the devlog reflection and the shape of every entry. The anti-slop rules in `rules/anti-slop-craft-SKILL.md` apply on top of these — no `delve into`, no rule-of-three, no fake conclusion, fatal-flaw veto before saving.

## 1. When the agent logs

The user triggers a checkpoint. Three trigger phrases the agent recognises (case-insensitive):
- "checkpoint" / "log it" / "save the devlog"
- "what did we learn" / "wrap up"
- "done for today" / "logging out"

The agent does **not** auto-prompt on session close. The user decides when to checkpoint. This is a team of three students — open-ended by design, the user picks the moment.

## 2. Reflection prompt the agent runs

When triggered, the agent asks, in this exact order, before writing anything:

1. "What did you do since the last checkpoint?" — open; let the user name the work, not the agent.
2. "What did you learn that you didn't know at the last checkpoint?" — the learning, not the work.
3. "Anything you'd arrange differently next time?" — the adjustment, not a confession.
4. "Whose work touched this — Vanshika, Anunay, Sarthak, or a mix?" — the team view, mandatory.

If the user gives a partial answer, the agent logs the partial answer and marks the missing field as `(not captured)` rather than fabricating it. Anti-slop rule: never invent a learning to fill the field.

## 3. Entry shape (mandatory, same for every entry)

Devlog lives in `devlogs.md` (single file, append-only, no per-member files). Every entry is one bullet block with this exact layout:

```
## YYYY-MM-DD — <short title, no slop>

**Vanshika** — <one line, what she did or decided>
**Anunay** — <one line>
**Sarthak** — <one line>

**Learnings** — <one line per teammate who has one; skip the line if not captured>
**Blockers** — <one line, or "none">
**Pipeline stage(s) touched** — <number(s) from AGENT.md, or "none">
**Arrange differently next time** — <one line, or "no change">
```

Rules inside the shape:
- One line per teammate, always. If a teammate didn't work that day, write `Vanshika — off`, etc. Never collapse two teammates into one line.
- No rule-of-three inside any line. If you need three examples, write three separate devlog entries instead.
- No "delve into," "robust," "seamless," "leverage," "it's important to note." If a line needs one of these, the line is wrong — rewrite.
- No fake conclusion. The last line of the entry is `Arrange differently next time`, not a summary.
- Date in ISO format. Title in sentence case, no emoji, no all-caps, no em-dash label format.

## 4. Three-member view rule

Each entry must show all three views even if one teammate did nothing that day. This is the team-of-three contract — the devlog is the only place every member's day is visible at once. If a teammate is not reachable, the agent writes `not reachable today` and asks the user on the next checkpoint whether to backfill.

## 5. Cleanup pass (anti-slop Part 4)

Before saving the entry, the agent runs Devil's Advocate on its own draft:
1. Did any line use a banned word? Cut it.
2. Did any line survive a "what would it mean for this to be false" test with "nothing"? Cut it.
3. Does the entry end on a real adjustment, or on a restatement? If restatement, cut the restatement.
4. State one honest remaining weakness to the user before saving ("the blocker line is vague, you'll want to tighten it later" reads better than silence).

Ponytail skip: no separate per-member files, no metadata YAML per entry, no index file. One file, one shape, one cleanup pass.
