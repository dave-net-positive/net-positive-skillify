#!/usr/bin/env python3
"""
apply_patch.py - apply a reviewed set of surgical edits to a skill.

Usage:
    python3 scripts/apply_patch.py <patch.json> [--dry-run]

Applies targeted edits in place. It never regenerates a whole file: a
find/replace must match an exact, unique (or explicitly counted) string, so an
edit either lands precisely or fails loudly. This keeps an update cheap and
safe. With --dry-run, every edit is validated (files exist, find strings match
the expected count, add_file targets are absent) but nothing is written, so a
whole patch is proven landable before a single byte changes. Pure standard
library.

patch.json schema:
{
  "target_dir": "path/to/skill",
  "edits": [
    {"file": "SKILL.md", "find": "old text", "replace": "new text", "count": 1},
    {"action": "add_file", "path": "scripts/new.py", "content": "..."},
    {"action": "add_file", "path": "scripts/gen.py", "copy_from": "/abs/template.py"},
    {"action": "rename", "from": "reference/x.md", "to": "references/x.md"}
  ]
}
"""

import json
import os
import sys


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv[1:]
    if not args:
        raise SystemExit("usage: python3 scripts/apply_patch.py <patch.json> [--dry-run]")
    patch = json.load(open(args[0], encoding="utf-8"))
    root = patch.get("target_dir")
    if not root or not os.path.isdir(root):
        raise SystemExit("apply_patch: target_dir missing or not a directory: %s" % root)

    edits = patch.get("edits", [])
    if not edits:
        raise SystemExit("apply_patch: no edits in patch.")

    verb = "would replace" if dry else "replaced"
    applied, errors = [], []
    for n, e in enumerate(edits, 1):
        action = e.get("action", "replace")
        try:
            if action == "replace":
                rel = e["file"]
                path = os.path.join(root, rel)
                if not os.path.isfile(path):
                    raise ValueError("file not found: %s" % rel)
                text = open(path, encoding="utf-8").read()
                find, repl = e["find"], e.get("replace", "")
                if not find:
                    raise ValueError("empty find string in %s (unauthored stub edit?)" % rel)
                want = e.get("count", 1)
                got = text.count(find)
                if got == 0:
                    raise ValueError("find string not present in %s" % rel)
                if got != want:
                    raise ValueError("find string occurs %d time(s) in %s, expected %d; make it more specific" % (got, rel, want))
                if not dry:
                    open(path, "w", encoding="utf-8").write(text.replace(find, repl))
                applied.append("%d. %s in %s" % (n, verb, rel))
            elif action == "add_file":
                path = os.path.join(root, e["path"])
                if os.path.exists(path):
                    raise ValueError("path already exists: %s (use replace to edit it)" % e["path"])
                if e.get("copy_from") and not os.path.isfile(e["copy_from"]):
                    raise ValueError("copy_from not found: %s" % e["copy_from"])
                if not dry:
                    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                    if e.get("copy_from"):
                        content = open(e["copy_from"], encoding="utf-8").read()
                    else:
                        content = e.get("content", "")
                    open(path, "w", encoding="utf-8").write(content)
                applied.append("%d. %s %s" % (n, "would add" if dry else "added", e["path"]))
            elif action == "rename":
                src, dst = os.path.join(root, e["from"]), os.path.join(root, e["to"])
                if not os.path.exists(src):
                    raise ValueError("rename source not found: %s" % e["from"])
                if os.path.exists(dst):
                    raise ValueError("rename target already exists: %s" % e["to"])
                if not dry:
                    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
                    os.rename(src, dst)
                applied.append("%d. %s %s -> %s" % (n, "would rename" if dry else "renamed", e["from"], e["to"]))
            else:
                raise ValueError("unknown action: %s" % action)
        except Exception as ex:  # noqa: BLE001
            errors.append("edit %d (%s): %s" % (n, action, ex))

    for a in applied:
        print("OK  " + a)
    if errors:
        for er in errors:
            print("ERR " + er, file=sys.stderr)
        print("\n%d edit(s) %s, %d failed. Failed edits made no change; fix and re-run." % (
            len(applied), "validated" if dry else "applied", len(errors)), file=sys.stderr)
        sys.exit(1)
    if dry:
        print("\nDry run: all %d edit(s) validated; nothing written. Re-run without --dry-run to apply." % len(applied))
    else:
        print("\nAll %d edit(s) applied surgically. Re-run net-positive-skillify:review to confirm." % len(applied))


if __name__ == "__main__":
    main()
