# Skill spec: frontmatter, naming, and packaging

The rules the scaffolder enforces, matching what net-positive-skillify:review validates.

## Name

- Lowercase alphanumeric with single hyphens: `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
  No leading, trailing, or consecutive hyphens.
- 64 characters or fewer.
- Must not contain the reserved words `claude` or `anthropic`.
- Must exactly match the parent directory name, and therefore the zip's root
  folder when packaged. Display names ("Net Positive Skillify Create") live in the
  SKILL.md heading, not the frontmatter.

## Description

- One quoted string. Say what the skill does AND when to use it, in the third
  person, and include concrete trigger phrases users would actually say.
- This is the only text the model sees when deciding whether to load the skill,
  so it earns its length; a vague description means the skill never triggers or
  triggers wrongly.

## Compatibility

- Optional but set it whenever the skill has any runtime dependency (Python,
  Node, packages, other skills). 500 characters or fewer.
- The review flags a skill that mentions dependencies in prose without a
  compatibility field.

## Known frontmatter fields

`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.
Anything else is flagged as unknown. Version the skill under `metadata.version`.

## Directory conventions

```
<skill-name>/
├── SKILL.md          (always loaded; keep it lean)
├── references/       (loaded on demand, one topic per file)
├── scripts/          (run via bash, never read into context)
└── assets/           (templates, brand files, images)
```

Use `references/` (plural). Reference files use kebab-case filenames. Any
reference over 100 lines carries a Contents list near the top.

## Packaging

Zip the skill folder so the archive's root is the folder named exactly after the
frontmatter name. Exclude `__pycache__`, `.git`, and editor droppings. A `.skill`
extension is a zip by another name; both are accepted by the review tooling.
