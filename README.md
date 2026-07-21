# Net Positive Skillify

Skill lifecycle tooling for Net Positive. Three skills covering the full life of
an Agent Skill, sharing one philosophy: if a step can be done with code rather
than the model, use code.

## Skills

- **net-positive-skillify:create** scaffolds a new skill that is efficient by
  construction: valid frontmatter, progressive disclosure, and a designed
  code/model split, finishing with a review as the quality gate.
- **net-positive-skillify:review** analyses a skill for run-time token cost. Code detects
  candidate pain points, the model verifies each in context against a rubric
  (confirmed, suppressed, or uncertain, plus open-ended findings the keywords
  would miss), and a self-contained, Net Positive branded HTML report presents all
  tiers auditably. Nothing is changed without approval.
- **net-positive-skillify:update** applies changes surgically, either the confirmed tier
  of a review or edits the user requests directly. Exact find/replace patches
  with a dry-run gate; never regenerates whole files.

## Installation

Personal scope, loaded in place with no install step: copy the `net-positive-skillify`
folder into `~/.claude/skills/` and it loads as `net-positive-skillify@skills-dir` on the
next session. Alternatively distribute via a plugin marketplace or load for one
session with `claude --plugin-dir ./net-positive-skillify`.

## Dependencies

Python 3 (standard library only). No third-party packages.

## House style

British English. No em dashes. Branded output carries the mandatory footer
"This document has been created with the assistance of AI" and uses Net Positive
brand colours with WCAG 2.1 AAA text combinations.

## Roadmap

Governance and security review skills (rubric-driven, mapped to the Net Positive
AI risk management model) are planned for a future release, alongside verdict
mining to codify recurring findings into deterministic detectors.
