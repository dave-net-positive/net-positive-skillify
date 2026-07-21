# Patching: surgical edits

`apply_patch.py` reads a `patch.json` and applies edits in place. It never
rewrites a whole file. Every find/replace must match an exact string the
expected number of times, so an edit lands precisely or fails without changing
anything. `--dry-run` validates the whole patch first without writing.

## Schema

```json
{
  "target_dir": "path/to/skill",
  "edits": [
    { "file": "SKILL.md", "find": "exact old text", "replace": "exact new text", "count": 1 },
    { "action": "add_file", "path": "scripts/new.py", "content": "..." },
    { "action": "add_file", "path": "scripts/gen.py", "copy_from": "/abs/path/template.py" },
    { "action": "rename", "from": "reference/x.md", "to": "references/x.md" }
  ]
}
```

- `replace` (default action): exact find/replace. `count` is how many times the
  string should occur (default 1). If it occurs a different number of times, the
  edit fails and asks you to make the `find` more specific. Quote enough
  surrounding text to be unique. An empty `find` is rejected, so unauthored
  stubs from `verdicts_to_patch.py` cannot apply by accident.
- `add_file`: create a new file from `content` or `copy_from`. Fails if the path
  exists (use a replace to edit an existing file).
- `rename`: move a file, for example aligning `reference/` to the spec's
  `references/`. Fails if the target already exists.

Keys beginning with `_` (such as the `_from_verdict` metadata that
`verdicts_to_patch.py` writes) are ignored by `apply_patch.py`; delete them as
you author each stub to keep the patch readable.

## Turning a confirmed finding into edits

- **manual-edit / coverage-gap:** add the missing capability to the script
  (`add_file` a helper, or `replace` the relevant function), then `replace` the
  workflow prose that said "edit by hand" with an instruction to run the script.
- **regeneration:** `replace` the step that regenerates with a call to the
  in-place update script.
- **llm-rewrite:** `replace` the instruction to rewrite recurring text with one
  that reads persisted text from the data file.
- **llm-assembly:** `add_file` a small script that does the deterministic
  computation, then `replace` the prose step with the command to run it.

## Direct user requests

The same schema and discipline apply when the user asks for changes with no
review involved: a rename, a fix, a new reference, a wording change. Author
`patch.json` straight from the request, one edit per change, and restate the
planned edits to the user before applying if the request left room for
interpretation. `rename` handles file moves, `add_file` handles new references
or scripts, and everything else is an exact `replace`.

## Authoring rules

- Read the target file immediately before quoting it; the `find` must match the
  raw file content exactly, including whitespace.
- One recommendation may need several edits (a script change plus a prose
  change). Keep them adjacent in the edits array.
- Never widen an edit to "tidy things up while here"; that is how surgical
  updates become rewrites.

## After applying

Re-run net-positive-skillify:review against the updated skill and confirm the targeted
findings are cleared. If a find/replace failed, fix the `find` string and
re-run; never fall back to regenerating the file.
