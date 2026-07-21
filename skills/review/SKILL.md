---
name: review
description: "Analyses a single Agent Skill for run-time efficiency and token cost, finds pain points and places where code should replace model work, verifies each finding in context before reporting, and produces a clean, self-contained HTML report with prioritised recommendations, Net Positive branded by default via the bundled brand file. Stops at recommendations: it changes nothing until the user approves, after which the net-positive-skillify:update skill applies the changes surgically. Use when the user asks to analyse, review, profile, skillify, or streamline a skill, find why a skill is slow or token-heavy, or work out where code could replace AI. Triggers: 'skillify this skill', 'run a skillify review', 'analyse this skill', 'streamline this skill', 'why is this skill so token-heavy', 'where can code replace AI', 'review my skill for efficiency'."
compatibility: "Requires Python 3 (standard library). No third-party packages or external assets are needed."
metadata:
  version: "2.0"
---

# Net Positive Skillify Review

Analyses one skill and reports how to make it cheaper to run. The guiding rule is
the user's: **if a step can be done with code rather than the model, use code.**
The expensive anti-patterns are regenerating whole documents, the model
hand-editing large generated artifacts, and the model doing deterministic work
(scoring, formatting, assembling JSON) that a script could do.

Detecting those patterns is itself a judgement, not a deterministic job, so this
skill does not let keyword matching have the last word. Code casts a wide net to
find candidates, the model verifies each one in context, and code renders only
what survived. That split is the point: detection is tuned for recall, verification
for precision, and they stop trading one off against the other.

This skill only analyses and recommends. It never edits the target skill. Applying
changes is a separate, user-approved step handled by the `net-positive-skillify:update` skill.

## Workflow

```
- [ ] Step 1: Inspect structure (run analyse_structure.py -> analysis.json)
- [ ] Step 2: Detect candidates (run analyse_efficiency.py -> candidates.json)
- [ ] Step 3: Verify each candidate in context, then the open-ended pass -> verdicts.json
- [ ] Step 4: Produce the report (run generate_analysis_report.py)
- [ ] Step 5: Present the report and ask whether to proceed
- [ ] Step 6: If approved, hand the confirmed recommendations to net-positive-skillify:update
```

**Step 1 to 2: Detect.** Run both analysers against a skill directory or a
`.skill`/`.zip`:

```bash
python3 scripts/analyse_structure.py <skill-path> analysis.json
python3 scripts/analyse_efficiency.py <skill-path> candidates.json
```

`analyse_efficiency.py` emits *unverified candidates*, each tagged with a kind, a
confidence prior, and the surrounding `context` and `section`. It deliberately
over-collects: a candidate is a place to look, not a confirmed problem. What each
kind means: [references/efficiency-checks.md](references/efficiency-checks.md).

**Step 3: Verify (the model's job, not a script).** This is where judgement
belongs. Read [references/verification-rubric.md](references/verification-rubric.md),
then work through `candidates.json` one entry at a time. For each, read its
`context` and decide: **confirmed**, **suppressed** (matched the words but not the
behaviour, with a reason), or **uncertain** (context does not settle it). Then run
the open-ended pass: look once at the whole skill for any expensive pattern the
keyword categories would have missed, and add it to `novel` at low confidence.
Write the result to `verdicts.json` in the shape the rubric specifies. Do not skip
this step and report raw candidates: that is what produced false positives before.

**Step 4: Report.** Render a clean, self-contained HTML report from the verdicts,
Net Positive branded via the bundled brand file:

```bash
python3 scripts/generate_analysis_report.py verdicts.json report.html \
    --candidates candidates.json --structure analysis.json \
    --brand assets/brand.net-positive.json
```

The report shows three tiers, confirmed, uncertain, and suppressed (collapsed but
with reasons, so the filtering is auditable), plus any novel findings, credited
good practice, and governance or security sections when those passes were run.
The Net Positive brand file applies the brand palette (Ember accent on a clean
neutral theme, WCAG AA contrast), the Net Positive logo on the accent header
band, and the AI disclaimer footer. Omit `--brand` for a neutral theme, or point
it at another brand file. See [references/branding.md](references/branding.md).

**Step 5: Gate.** Present the report. Summarise the confirmed recommendations in
chat and ask the user whether to apply them. Change nothing yet.

**Step 6: Hand off.** Only if the user approves, pass the confirmed
recommendations to `net-positive-skillify:update`, which turns them into a surgical patch.

## Inputs and outputs

- **Input:** one skill (directory, `.skill`, or `.zip`).
- **Intermediate:** `analysis.json` (structure), `candidates.json` (unverified),
  `verdicts.json` (verified).
- **Output:** a self-contained `report.html`. No change to the target skill.

## Dependencies

- `python3` (standard library). No third-party packages or external assets.

## Reference files

- [references/efficiency-checks.md](references/efficiency-checks.md) - what each candidate kind means.
- [references/verification-rubric.md](references/verification-rubric.md) - how the model judges candidates into verdicts, and the verdicts.json shape.
- [references/branding.md](references/branding.md) - the optional brand.json for embedding your own identity.

## House style

British English. No em dashes; use commas, colons, semicolons, or full stops.
