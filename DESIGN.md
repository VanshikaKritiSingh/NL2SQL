# DESIGN.md — visual + text craft for the agent

One file, both design and text anti-slop. Governs every visual deliverable (`SVG_DIAGRAM.svg`, inline SVG in `nl2sql.html`, future rendered HTML) and every prose deliverable (`.md`, devlog, `*.md` doc, copy in HTML). Source merged from `rules/anti-slop-craft-SKILL.md` and `rules/devlog-rules.md`. Referenced from `AGENT.md`, `SKILL.md`, `TEAM.md`. Ponytail skip: no per-asset overrides, no theme registry, no "design system" folder.

---

## Part 1 — Text anti-slop pass

Hunt these three tell categories. Finding one is a signal to rewrite the sentence, not just delete the word.

**Lexical tells** — words fine alone but flag the sentence as machine output when they appear at all: *delve into, moreover, furthermore, in today's fast-paced world, it's important to note, unlock the power of, robust, seamless, holistic, leverage (as a verb), navigate the landscape of, at the end of the day*. If a sentence needs one of these to make its transition work, the transition itself is weak — fix the logic, not the connective tissue.

**Structural tells:**
- The rule-of-three reflex — reaching for exactly three examples/adjectives/clauses by default, whether or not three is the right number for this content.
- The fake conclusion — a closing paragraph that restates the piece instead of adding a final point ("In conclusion, X is a powerful tool that offers many benefits").
- The hedge-closer — ending an argument or critique with "ultimately, it depends" or "both sides have merit" when the piece actually built toward a real position. This quietly cancels everything useful that came before; see Part 4 veto rule.
- Uniform paragraph rhythm — every paragraph the same length, every section the same shape. Real writing has variance because ideas don't come in identical units.

**Substance tells** — these are worse than style tells because they erode trust, not just polish:
- Confident claims with invisible sourcing ("research shows," "studies suggest") with no study named. If it can't be cited, say it's an observation, not a finding.
- Sentences that parse correctly but assert nothing ("taking a holistic approach ensures every touchpoint reinforces the brand"). Read every sentence and ask what it would mean for it to be false — if nothing, cut it.
- Symmetric even-handedness applied to questions that don't deserve it, papering over a real asymmetry in the evidence for the sake of sounding balanced.

**Fix pattern:** paraphrase in the writer's actual voice, vary sentence and paragraph length on purpose, delete any sentence that survives a "what would it mean for this to be false" test with "nothing", and make sure the piece is allowed to end on a real point instead of a restatement.

---

## Part 2 — Design anti-slop pass

Cookie-cutter layouts, generic gradients, and repeated visual patterns are the design equivalent of "delve into." Watch for these current default clichés — they show up regardless of subject matter, which is exactly how you know they're defaults and not choices:

1. **The warm-cream-and-terracotta default** — a cream background near `#F4F1EA` with a terracotta accent near `#D97757`. This is currently the single most common AI-design tell (close to a well-known AI assistant's own interaction accent, so it reads as a giveaway rather than a brand choice). Warm palettes are welcome — Part 3 asks for one — but never land on this exact pairing by default; earn a warm palette with a deliberate, different pair of hues.
2. **The SaaS-card kit** — every block of content chopped into identically rounded cards, one border-radius applied everywhere regardless of hierarchy, the same soft grey drop-shadow (`rgba(0,0,0,.1)`) under each one.
3. **Template chrome** — a tracked-out ALL-CAPS eyebrow label above every heading; meta strings joined with middle dots; a spaced em-dash label format ("WORD — fragment"); a monospace face used only for small numeric labels because it "looks technical"; a "→" arrow appended to every link or button.
4. **Sequence markers on non-sequences** — numbered 01 / 02 / 03 badges on content that isn't actually an ordered process.
5. **Single-word headline accenting** — italicizing or recoloring exactly one word in a headline for "emphasis," every time.
6. **Motion for its own sake** — a fade-and-slide-up entrance on every section, a hover-lift on every card, with no single moment that actually earns attention.

**Fix pattern:** before building anything, write a short, specific design plan — palette (named hex values), type (roles and pairing), layout (one-sentence description + rough wireframe), and a stated principle for what makes *this* piece look like it was made for *this* content. Then check the plan against the list above; anything that matches a default without a reason specific to this brief gets replaced.

---

## Part 3 — HTML documentation design spec

When the deliverable is an HTML file built for documentation (a report, spec, style guide, or reference doc rendered as a webpage), apply this concrete system on top of Part 2's guardrails.

### Palette: warm, duotone, and *not* the cliché

"Duotone" here means the whole document runs on two ink colors plus their tints/shades — not a rainbow of accent colors. Pick one pair, use it everywhere, and don't introduce a third hue except for a single, rare, functional exception (e.g. an error state). Two starting options that are warm without repeating the cream/terracotta default:

- **Ink & Ember** — near-black warm ink `#241C1A` for text and rules, warm parchment `#F2E9DC` for the page ground, ember/oxblood `#8A2E1F` as the single accent (links, active states, emphasis marks). Darker and more editorial than the cliché pairing.
- **Umber & Brass** — espresso `#3A2B22` for text, warm ivory `#F5EEE1` for ground, brass/ochre `#A97C24` as the accent. Reads as heritage/craft rather than "AI demo."

Either pair should hit at least a 4.5:1 contrast ratio between text and ground, and the accent should be reserved for things that are actually interactive or actually need emphasis — not decoration.

### Binary color coding — make the duotone do work, not just look nice

Instead of adding a traffic-light system (green/red/yellow) for statuses, encode paired binary states — before/after, included/excluded, pass/fail, old/new — using the *same two inks* the document already runs on: ground-color fill vs. accent-color fill, or accent-outline vs. no-outline. This keeps the palette genuinely duotone while still giving the reader a consistent, learnable signal every time a binary state appears in a table, diagram, or callout. Reserve a third color, if you ever need one, strictly for a true alarm state (an actual error/failure notice) — never for routine variety.

### Typography: Fraunces (or Playfair Display) + Inter (or Helvetica)

- **Display / headings:** Fraunces — note the spelling; it's often typed "Frunces." It's a variable serif with a WONK axis controlling how irregular the letterforms feel. Keep WONK low for a restrained, documentation-appropriate voice; save higher WONK values for a section that genuinely wants personality (a title page, not a body of specs). Use two weights maximum — e.g. 600 for H1/H2, 400 italic for pull-quotes or callouts — rather than stacking Bold-on-Black-on-ExtraBold.
  - If Fraunces isn't available, Playfair Display is the documented alternative pairing partner for Inter/Helvetica and carries a similarly high-contrast, editorial presence — use it the same way, at Bold (700) for headings only, never for body copy (its stroke contrast fights legibility at small sizes).
- **Body / UI / labels:** Inter (or Helvetica/Helvetica Neue where system fonts are preferred). Regular (400) for body copy, Medium (500) for captions, table headers, and metadata. Its neutrality is the point — it should never compete with the serif for attention.
- **Rules:** line length under ~80 characters for body text; give serif headings slightly looser tracking than the sans body; don't use small caps or tracked-out uppercase for section labels (see Part 2, item 3) — sentence case with a rule or indent does the same signposting job without the template-chrome tell.

---

## Part 4 — Devil's Advocate self-review

Before presenting *any* output this skill touched — text or design — run one adversarial pass on your own draft. This is the same discipline as a human editor reading their own piece cold before sending it.

1. **Steelman the draft's own goal first.** State plainly what this piece is trying to do, so the critique that follows is aimed at the real target, not a strawman of it.
2. **Ask: would a sharp human reviewer flag this as AI-written or AI-designed in the first ten seconds?** Name the single weakest sentence, section, or visual element — the one most likely to trigger that reaction — specifically. "It's fine" is not an answer; if nothing is weak, say what specifically makes it hold up.
3. **Run it against Part 1 and Part 2's checklists explicitly**, not from memory — cliché-hunting from memory is exactly how clichés slip through.
4. **Fatal-flaw veto:** if the draft still contains a hedge-closer, a fabricated citation, or the cream/terracotta default, that's an automatic fail regardless of how polished everything else is — fix it before delivery, don't note it as a caveat and ship anyway.
5. **State one honest remaining weakness to the user**, even after cleanup. A deliverable that claims to be flawless is itself a slop tell; a specific, real caveat ("the metaphor in paragraph three is doing more work than it should") reads as considered, not machine-perfect.

---

## Essential tools reference

Use these to verify rather than assume the pass worked — a second, independent check catches what self-review alone misses:

**Text:** a readability pass (e.g. Hemingway-style sentence-length and passive-voice check) to catch structural bloat; a plagiarism/originality check when source material was referenced heavily, to confirm paraphrase stayed paraphrase.

**Design:** a contrast checker (WCAG 4.5:1 minimum for body text) run against the actual chosen palette, not assumed from the hex values; a type-scale check at real production sizes — Fraunces/Playfair in particular can look fine at display size and fail at anything smaller, so never approve a pairing without checking body-size legibility specifically.

---

## Condensed workflow

1. Draft the deliverable normally.
2. Text present? → Part 1 pass.
3. Design/HTML present? → Part 2 pass, then Part 3 spec if it's HTML documentation specifically.
4. Always → Part 4 Devil's Advocate self-review, fatal-flaw veto included.
5. Deliver, with the one honest remaining weakness named.

---

## Devlog rules (merged from `rules/devlog-rules.md`)

### When the agent logs
The user triggers a checkpoint. Three trigger phrases the agent recognises (case-insensitive):
- "checkpoint" / "log it" / "save the devlog"
- "what did we learn" / "wrap up"
- "done for today" / "logging out"

The agent does **not** auto-prompt on session close. The user decides when to checkpoint. This is a team of three students — open-ended by design, the user picks the moment.

### Reflection prompt
When triggered, the agent asks, in this exact order, before writing anything:
1. "What did you do since the last checkpoint?" — open; let the user name the work, not the agent.
2. "What did you learn that you didn't know at the last checkpoint?" — the learning, not the work.
3. "Anything you'd arrange differently next time?" — the adjustment, not a confession.
4. "Whose work touched this — Vanshika, Anunay, Sarthak, or a mix?" — the team view, mandatory.

If the user gives a partial answer, the agent logs the partial answer and marks the missing field as `(not captured)` rather than fabricating it. Anti-slop rule: never invent a learning to fill the field.

### Entry shape (mandatory)
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
- One line per teammate, always. If a teammate didn't work that day, write `Vanshika — off`, etc. Never collapse two teammates into one line.
- No rule-of-three inside any line. If you need three examples, write three separate devlog entries instead.
- No "delve into," "robust," "seamless," "leverage," "it's important to note." If a line needs one of these, the line is wrong — rewrite.
- No fake conclusion. The last line of the entry is `Arrange differently next time`, not a summary.
- Date in ISO format. Title in sentence case, no emoji, no all-caps, no em-dash label format.

### Three-member view rule
Each entry must show all three views even if one teammate did nothing that day. This is the team-of-three contract — the devlog is the only place every member's day is visible at once. If a teammate is not reachable, the agent writes `not reachable today` and asks the user on the next checkpoint whether to backfill.

### Cleanup pass (anti-slop Part 4)
Before saving the entry, the agent runs Devil's Advocate on its own draft:
1. Did any line use a banned word? Cut it.
2. Did any line survive a "what would it mean for this to be false" test with "nothing"? Cut it.
3. Does the entry end on a real adjustment, or on a restatement? If restatement, cut the restatement.
4. State one honest remaining weakness to the user before saving ("the blocker line is vague, you'll want to tighten it later" reads better than silence).

Ponytail skip: no separate per-member files, no metadata YAML per entry, no index file. One file, one shape, one cleanup pass.

---

*Source: `rules/anti-slop-craft-SKILL.md` (Parts 1, 2, 3, 4 + tools + condensed workflow) and `rules/devlog-rules.md` (when, prompt, shape, three-member rule, cleanup) merged into DESIGN.md. `the-architect-agent.md` is excluded from agent governance per user correction; preserved as archive only. Rules directory removed after this consolidation.*
