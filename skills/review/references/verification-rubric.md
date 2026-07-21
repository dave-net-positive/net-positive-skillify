# Verification rubric

## Contents

- The decisive distinctions
- Kinds and what makes each one real
- Verdicts
- The open-ended pass
- Output: verdicts.json

The detection scan (`analyse_efficiency.py`) finds *candidates* by keyword and
cannot read meaning, so it over-collects on purpose. This rubric is how the model
turns those raw candidates into verdicts. Work through `candidates.json` one entry
at a time, read each candidate's `context` and `section`, and decide.

The single question behind every kind: **does this make the model do work that
code could do deterministically, at run-time token cost?** If yes, it is a real
finding. If the words merely resemble an anti-pattern but the actual behaviour is
a human acting, a generator doing its job, or a one-off, it is not.

## The decisive distinctions

These are the traps the keyword scanner falls into. Apply them first.

- **Who acts: model or human?** "Fill it in by hand", "complete after review",
  "the approver adds the name" usually means a *person* editing a finished
  document. That is never a finding. It is only a finding when the *model* edits a
  generated artifact at run time. Read `context` for the subject of the verb.
- **What kind of placeholder?** Three different things share the word. (a) A
  static token the generator inserts or leaves as-is (`[INSERT PURPOSE]`,
  `[To be completed]`): generator behaviour, not a finding. (b) A privacy or
  safety stand-in (`NHS-000-000-0000`, `Test Participant Alpha`): a deliberate
  rule, not a finding. (c) The model rewriting the same authored prose every run:
  that *is* an `llm-rewrite` finding. Only (c) counts.
- **Retrieval vs editing.** "Follow the links by hand", "fall back to searching":
  a retrieval strategy, not editing a generated artifact. Not a finding.
- **One-off vs every run.** Setup or first-run-only work does not carry the
  per-run cost the recommendation targets. Note it, but lower the confidence.

## Kinds and what makes each one real

- **manual-edit.** Real only when the model edits a generated artifact (HTML,
  docx, large file) at run time, for example `str_replace` on generated output.
  This drags the whole artifact into context each cycle, usually the biggest cost.
  Not real: a human filling fields; following wikilinks; editing a small data file
  the generator reads.
- **regeneration.** Real when the model regenerates a whole document because part
  changed. Not real: first-time generation, or regenerating a tiny file.
- **llm-rewrite.** Real when the model rewrites stored/authored text every run.
  Not real: static generator tokens, privacy stand-ins, or text the user supplies
  fresh each time.
- **llm-assembly.** Real when the model assembles deterministic structure (IDs,
  ordering, scoring, JSON shape) by reasoning. Not real: the model exercising
  genuine judgement (writing prose, deciding a rating) that no script could do.
- **coverage-gap.** Real when the skill admits a script cannot handle a case and
  pushes it to the model. Not real: an aside about a limitation that never costs
  run-time tokens.

## Verdicts

For each candidate, choose exactly one:

- **confirmed** - the behaviour is real per the rubric. Carry the recommendation.
- **suppressed** - the words matched but the behaviour is not the anti-pattern.
  Give the reason in plain terms (for example, "subject is the approver, a human").
- **uncertain** - the context genuinely does not settle it. Do not force a call;
  this tier is reviewed by a person and is the guard against wrongly binning a
  real issue. Use it sparingly, only when honestly unsure.

Set `confidence` (high/medium/low) on confirmed and uncertain verdicts. A `high`
prior with confirming context is high; a `low` prior confirmed only weakly is
medium or low.

## The open-ended pass

After judging every candidate, look once at the whole skill and ask: **is there
an expensive run-time pattern the five keyword categories would never have
caught?** For example a workflow step that quietly asks the model to do a large
deterministic transform, or to hold a big file in context that a script could
process. Add any such finding to `novel`, always at `confidence: "low"` and
clearly labelled, so it is offered as a lead to investigate, not asserted as a
precise flag. If nothing stands out, leave `novel` empty. Do not pad it.

## Output: verdicts.json

Write this exact shape:

```json
{
  "skill": "<name from candidates.json>",
  "stage": "verdicts",
  "verdicts": [
    {
      "candidate_id": "c1",
      "kind": "manual-edit",
      "file": "references/template_structure.md",
      "line": 141,
      "verdict": "suppressed",
      "confidence": "high",
      "reason": "The subject who fills the cell by hand is the user, after generation, not the model.",
      "evidence": "the generator leaves the DPO cell blank so the user can fill in a name by hand",
      "recommendation": ""
    }
  ],
  "novel": [
    {
      "kind": "general",
      "file": "SKILL.md",
      "line": 0,
      "observation": "short description of the pattern",
      "recommendation": "what to do",
      "confidence": "low",
      "source": "open-ended"
    }
  ]
}
```

One verdict per candidate, keyed by `candidate_id`. `recommendation` is filled for
confirmed verdicts (copy or sharpen the candidate's), empty for suppressed. Carry
`file` and `line` through from the candidate so the report can locate each finding.
Then render with `generate_analysis_report.py verdicts.json report.html
--candidates candidates.json --structure analysis.json`.
