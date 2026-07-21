# Design principles: efficient by construction

These are the authoring-time versions of the rules net-positive-skillify:review enforces.
Design against them from the start and the review becomes a formality.

## The golden rule

If a step can be done with code rather than the model, use code. The model's
share of a skill is judgement: deciding, assessing, writing prose that genuinely
differs each run. Everything deterministic (scoring, counting, formatting,
assembling structured data, transforming files) belongs in a script.

## The five anti-patterns to design out

These are the findings the review confirms. Each has a design-time cure.

- **manual-edit.** Never plan for the model to edit a generated artifact. If an
  output might need correcting after generation, that is a requirement on the
  generator: give it an update mode, or drive it from a data file the model
  edits instead. A generated file should never enter the model's context.
- **regeneration.** Design every generator to patch in place. If one field
  changes, the run should change one field, not rebuild the document. Keep the
  canonical state in a small data file (JSON is ideal) and make the generator a
  pure function of it.
- **llm-rewrite.** Any authored text that recurs across runs (boilerplate,
  house-style blocks, standard paragraphs) is data. Persist it in a file the
  generator reads; the model writes it once, at creation time.
- **llm-assembly.** IDs, orderings, totals, JSON shapes, and table layouts are
  deterministic. If the model produces judgements, have it emit them once as a
  minimal canonical structure, then let one script fan that out to every output
  format. One judgement pass, many rendered artifacts, guaranteed consistent.
- **coverage-gap.** If you catch yourself writing "the script does not handle X,
  so describe it in prose", stop and extend the script. Documented gaps become
  run-time model work.

## Structure rules

- **Progressive disclosure.** SKILL.md is the always-loaded core; keep it lean
  (aim under 150 lines) and push detail into `references/`, each loaded only
  when its step needs it. Tell the reader exactly when to read each reference.
- **Scripts are run, never read.** Write scripts so they are invoked via bash
  with clear arguments and loud failures. Nothing should require the model to
  read a script's source to use it.
- **Contents lists.** Any reference likely to exceed 100 lines gets a Contents
  list near the top from day one.
- **One job per file.** A reference covers one topic; a script does one thing.
  This is what makes future surgical updates cheap.

## Frontmatter rules

Set these at creation, not retrofit: a spec-valid `name` matching the folder, a
`description` that says what the skill does AND when to use it with concrete
trigger phrases, and a `compatibility` field naming every runtime dependency.
Full rules in [skill-spec.md](skill-spec.md).

## Net Positive house rules

British English throughout. No em dashes; use commas, colons, semicolons, or
full stops. Any branded document output must carry the AI disclaimer footer and
use brand colours with WCAG AA text combinations.
Never embed real personal data in examples; use the organisation's synthetic
placeholders.

## A worked example of the split

A skill that reviews reports and produces a docx, a dashboard, and a CSV:

- Model: reads the report, makes the judgements, emits one `results.json`.
- Script: renders `results.json` into all three outputs, computes every count
  and total, and patches individual fields on re-runs.
- References: the judgement rubric (loaded at review time), the output spec
  (loaded only if the renderer needs changing).

The model never sees the generated files, nothing is rewritten twice, and the
outputs cannot disagree with each other.
