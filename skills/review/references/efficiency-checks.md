# Efficiency candidate kinds

`analyse_efficiency.py` groups candidates by kind. A candidate is an unverified
lead, found by keyword, that the verify step judges in context. Each kind maps to
a standing recommendation that applies only once a candidate is **confirmed**.

## Kinds

- **manual-edit.** Suspected when the skill mentions editing something by hand
  (for example `str_replace` on generated output). Real only when the *model*
  edits a *generated artifact* at run time, which forces the whole artifact into
  context each cycle, usually the single biggest token cost. A human filling
  fields, or following links, matches the words but is not a finding. Fix when
  real: extend the generator/update script so the artifact never enters context.
- **coverage-gap.** Suspected when the skill says something is "not automated" or
  a script "cannot handle" a case. Real when that gap pushes work to the model at
  run time. Fix: close the gap in the script.
- **regeneration.** Suspected when a whole document is rebuilt. Real when only part
  changed. Fix: patch the changed elements in place.
- **llm-rewrite.** Suspected on the word "placeholder" or "rewrite". Real only when
  the model rewrites stored authored text every run. Static generator tokens and
  privacy stand-ins also match the word but are not findings. Fix: persist authored
  text in the data file so only new or changed items need the model.
- **llm-assembly.** Suspected when the model appears to build structured data. Real
  when that data (IDs, ordering, scoring, JSON shape) is deterministic. Genuine
  judgement the model must do is not a finding. Fix: move the deterministic parts
  into a script.

These five are the code-over-AI opportunities. The verify step
([verification-rubric.md](verification-rubric.md)) decides which candidates are
real; the open-ended pass adds anything the five categories missed.

## Confidence priors

Each candidate carries a `prior` (high/medium/low) reflecting how trustworthy the
bare keyword match is before context is read. `str_replace` on output is a high
prior; a lone "by hand" is low because the same words so often describe a human.
The prior is a starting point for the verifier, not a verdict.

## Credited good practice

Detection also credits patterns that already save tokens: surgical in-place
updates, scripts run rather than read into context, and progressive disclosure.
These are not problems; they are the targets the recommendations move the rest of
the skill towards.

## Reading the output

`candidates.json` carries `candidates` (each with file, line, kind, prior, trigger,
section, context, and a standing why/recommendation) and `credited`. It is
unverified. The verify step turns it into `verdicts.json` (confirmed / suppressed /
uncertain, plus novel), which is what the report and `net-positive-skillify:update` consume.
