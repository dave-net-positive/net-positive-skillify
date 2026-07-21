---
name: create
description: "Creates a new Agent Skill that is efficient by construction, following the standards that net-positive-skillify:review checks for: valid frontmatter, code over model, progressive disclosure, and surgical-update-friendly architecture. Scaffolds the structure deterministically from a spec, then guides authoring of the content, and finishes by running net-positive-skillify:review as the quality gate. Use when the user wants to create, build, scaffold, or author a new skill, or turn a repeatable workflow into a skill. Triggers: 'create a skill', 'skillify create', 'build a new skill for X', 'scaffold a skill', 'turn this workflow into a skill', 'make me a skill that does X'."
compatibility: "Requires Python 3 (standard library). net-positive-skillify:review is recommended for the final quality gate."
metadata:
  version: "1.0"
---

# Net Positive Skillify Create

Creates a new Agent Skill that would pass a Skillify review cleanly on day one.
The guiding rule is the same one the review enforces: **if a step can be done
with code rather than the model, use code.** Efficiency is designed in at
authoring time, not retrofitted later.

The split of labour mirrors the review skill: code does the deterministic work
(scaffolding the structure, validating the name and frontmatter shape), the
model does the judgement (deciding the code/model split, authoring the content).

## Workflow

```
- [ ] Step 1: Gather requirements (purpose, triggers, inputs, outputs)
- [ ] Step 2: Design the code/model split (read references/design-principles.md)
- [ ] Step 3: Write spec.json and scaffold (run scaffold_skill.py)
- [ ] Step 4: Author the content (SKILL.md workflow, references, scripts)
- [ ] Step 5: Quality gate (run net-positive-skillify:review on the new skill)
- [ ] Step 6: Package and hand over
```

**Step 1: Gather requirements.** Establish with the user: what the skill does,
when it should trigger (concrete phrases), what it takes in, what it produces,
and what it must never do. If the skill produces documents, identify every
output format now; each one shapes the design.

**Step 2: Design the split.** Before writing anything, decide which parts of
the job are deterministic (scaffold them as scripts) and which need judgement
(they stay with the model, guided by references). Read
[references/design-principles.md](references/design-principles.md); it is the
authoring-time inverse of the review rubric, and following it is what makes the
new skill pass review. Sketch the file layout: SKILL.md, which references, which
scripts.

**Step 3: Scaffold.** Write a `spec.json` describing the skill (a starting
point is [assets/spec.example.json](assets/spec.example.json)), then run:

```bash
python3 scripts/scaffold_skill.py spec.json <output-parent-dir>
```

The scaffolder validates the name against the spec rules (lowercase kebab-case,
64 characters or fewer, no reserved words), creates the directory named exactly
after the skill, and generates the SKILL.md frontmatter, workflow checklist
skeleton, reference stubs (with a Contents list ready for any that will grow
long), and script stubs. It fails loudly on an invalid spec rather than
producing a broken skill. Frontmatter and naming rules are documented in
[references/skill-spec.md](references/skill-spec.md).

**Step 4: Author.** Fill the scaffold with real content. This is one-off
creation work, so the model writing prose here is fine; what matters is what the
skill will cost at run time. As you write, keep checking against the design
principles: scripts are run, never read into context; references load only when
their step needs them; generated artifacts are owned end to end by a generator
script so no run ever hand-edits them; authored text that recurs across runs is
persisted in a data file, not rewritten. For Net Positive skills, apply the house
style: British English, no em dashes, and the mandatory AI disclaimer on any
branded document output.

**Step 5: Quality gate.** Run the full net-positive-skillify:review pipeline against the
new skill: structure analysis, candidate detection, the verify step, and the
report. A freshly created skill should come back with zero confirmed findings
and no structural recommendations. If anything is confirmed, fix it now, while
the skill is a page of files rather than an installed dependency.

**Step 6: Package.** Zip the skill folder (folder name must equal the
frontmatter name) and hand it over, noting where it should be installed and any
dependencies from the compatibility field.

## Inputs and outputs

- **Input:** the user's requirements, captured into `spec.json`.
- **Intermediate:** the scaffolded skill directory.
- **Output:** a complete, review-clean skill, packaged as a zip.

## Dependencies

- `python3` (standard library).
- `net-positive-skillify:review` for the Step 5 quality gate (recommended, not required).

## Reference files

- [references/design-principles.md](references/design-principles.md) - how to design a skill that is efficient by construction.
- [references/skill-spec.md](references/skill-spec.md) - frontmatter, naming, and packaging rules the scaffolder enforces.

## House style

British English. No em dashes; use commas, colons, semicolons, or full stops.
