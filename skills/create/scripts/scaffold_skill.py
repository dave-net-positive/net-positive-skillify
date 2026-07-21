#!/usr/bin/env python3
"""
scaffold_skill.py - deterministically scaffold a new Agent Skill from a spec.

Usage:
    python3 scripts/scaffold_skill.py spec.json <output-parent-dir>

Reads a spec.json describing the skill and creates <output-parent-dir>/<name>/
with a valid SKILL.md, reference stubs, and script stubs. Validates the spec
against the naming and frontmatter rules (see references/skill-spec.md) and
fails loudly rather than producing a broken skill. Pure standard library.

spec.json shape (see assets/spec.example.json):
{
  "name": "my-skill",
  "display_name": "My Skill",
  "description": "What it does and when to use it, with trigger phrases.",
  "compatibility": "Requires Python 3 (standard library).",
  "version": "1.0",
  "references": [
    {"file": "rubric.md", "title": "Rubric", "long": true}
  ],
  "scripts": [
    {"file": "do_thing.py", "purpose": "Does the thing deterministically."}
  ]
}
"""

import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
COMPAT_MAX = 500
RESERVED = ("claude", "anthropic")

SKILL_TEMPLATE = """---
name: {name}
description: "{description}"
{compat_line}metadata:
  version: "{version}"
---

# {display_name}

TODO: one short paragraph on what this skill does and the principle behind it.

## Workflow

```
{checklist}
```

TODO: expand each step. Scripts are run via bash, never read into context.
References are linked at the step that needs them, not loaded up front.

## Inputs and outputs

- **Input:** TODO
- **Output:** TODO

## Dependencies

{deps_section}

## Reference files

{ref_links}

## House style

British English. No em dashes; use commas, colons, semicolons, or full stops.
"""

REF_TEMPLATE = """# {title}

{contents}TODO: author this reference. One topic per file; say in SKILL.md
exactly when to read it.
"""

CONTENTS_BLOCK = """## Contents

- TODO: list the sections here once written (required, this file is expected to
  exceed 100 lines)

"""

SCRIPT_TEMPLATE = '''#!/usr/bin/env python3
"""
{file} - {purpose}

Usage:
    python3 scripts/{file} <args>

TODO: implement. Deterministic work only; fail loudly; pure standard library
where possible. This script is run via bash and never read into context.
"""

import sys


def main():
    raise SystemExit("{file}: not yet implemented")


if __name__ == "__main__":
    main()
'''


def fail(msg):
    raise SystemExit("scaffold_skill: " + msg)


def validate(spec):
    problems = []
    name = spec.get("name", "")
    if not name:
        problems.append("spec has no name")
    elif not NAME_RE.match(name):
        problems.append("name must be lowercase alphanumeric with single hyphens")
    if len(name) > NAME_MAX:
        problems.append("name exceeds %d characters" % NAME_MAX)
    if any(r in name for r in RESERVED):
        problems.append("name contains a reserved word (%s)" % " / ".join(RESERVED))
    desc = spec.get("description", "")
    if not desc:
        problems.append("spec has no description")
    if '"' in desc:
        problems.append('description must not contain double quotes')
    compat = spec.get("compatibility", "")
    if compat and len(compat) > COMPAT_MAX:
        problems.append("compatibility exceeds %d characters" % COMPAT_MAX)
    if spec.get("scripts") and not compat:
        problems.append("skill has scripts but no compatibility field; state the runtime (for example 'Requires Python 3')")
    low = desc.lower()
    if "use when" not in low and "use this" not in low and "trigger" not in low:
        print("scaffold_skill: WARNING - description does not state when to use the skill or give trigger phrases; the review will flag this.", file=sys.stderr)
    for r in spec.get("references", []):
        f = r.get("file", "")
        if not f.endswith(".md"):
            problems.append("reference %r must be a .md file" % f)
        if not re.match(r"^[a-z0-9][a-z0-9\-_.]*\.md$", f):
            problems.append("reference filename %r should be lowercase kebab-case" % f)
    return problems


def main():
    if len(sys.argv) < 3:
        fail("usage: python3 scripts/scaffold_skill.py spec.json <output-parent-dir>")
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    parent = sys.argv[2]
    problems = validate(spec)
    if problems:
        for p in problems:
            print("ERR " + p, file=sys.stderr)
        fail("%d problem(s) in spec; nothing created." % len(problems))

    name = spec["name"]
    root = os.path.join(parent, name)
    if os.path.exists(root):
        fail("target already exists: %s" % root)

    refs = spec.get("references", [])
    scripts = spec.get("scripts", [])
    os.makedirs(root)
    if refs:
        os.makedirs(os.path.join(root, "references"))
    if scripts:
        os.makedirs(os.path.join(root, "scripts"))

    compat = spec.get("compatibility", "")
    compat_line = 'compatibility: "%s"\n' % compat if compat else ""
    checklist = "\n".join(
        "- [ ] Step %d: TODO" % i for i in range(1, max(3, len(scripts) + 2) + 1))
    deps = ("- `python3` (standard library).\n- TODO: list anything else from the compatibility field."
            if scripts else "- None beyond the model itself. TODO: confirm.")
    ref_links = "\n".join(
        "- [references/%s](references/%s) - TODO: when to read it." % (r["file"], r["file"])
        for r in refs) or "- None."

    skill_md = SKILL_TEMPLATE.format(
        name=name,
        description=spec["description"],
        compat_line=compat_line,
        version=spec.get("version", "1.0"),
        display_name=spec.get("display_name", name),
        checklist=checklist,
        deps_section=deps,
        ref_links=ref_links,
    )
    open(os.path.join(root, "SKILL.md"), "w", encoding="utf-8").write(skill_md)

    for r in refs:
        contents = CONTENTS_BLOCK if r.get("long") else ""
        body = REF_TEMPLATE.format(title=r.get("title", r["file"]), contents=contents)
        open(os.path.join(root, "references", r["file"]), "w", encoding="utf-8").write(body)

    for s in scripts:
        body = SCRIPT_TEMPLATE.format(file=s["file"], purpose=s.get("purpose", "TODO"))
        path = os.path.join(root, "scripts", s["file"])
        open(path, "w", encoding="utf-8").write(body)
        os.chmod(path, 0o755)

    made = 1 + len(refs) + len(scripts)
    print("Scaffolded %s (%d file(s)): SKILL.md, %d reference(s), %d script(s)." % (
        root, made, len(refs), len(scripts)))
    print("Next: author the content (Step 4), then run net-positive-skillify:review as the quality gate (Step 5).")


if __name__ == "__main__":
    main()
