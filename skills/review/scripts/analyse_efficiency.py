#!/usr/bin/env python3
"""
analyse_efficiency.py - find candidate token pain points in a skill and capture
the context a verifier needs to judge each one.

Usage:
    python3 scripts/analyse_efficiency.py <skill-path> [candidates.json]

<skill-path> is a skill directory or a .skill/.zip. Scans the SKILL.md and every
markdown file under the skill for patterns that *might* cost tokens at run time,
then writes candidates.json and prints a summary.

This script deliberately does NOT decide whether a candidate is a real problem.
Keyword matching cannot read meaning: "edit the file by hand" (the model editing
a generated artifact, a real cost) and "the approver fills it in by hand" (a
human, not a cost) match the same words. So detection is tuned for recall: cast a
wide net, attach the surrounding context and a confidence prior, and leave the
judgement to the model-driven verify step (see references/verification-rubric.md),
which writes verdicts.json. The report renders verdicts, not raw candidates.

The golden rule the verifier applies: if a step can be done with code rather than
the model, it should be. The expensive anti-patterns are (a) regenerating whole
documents instead of patching them, (b) the model hand-editing large generated
artifacts, and (c) the model doing deterministic work (scoring, formatting,
assembling JSON) a script could do. Pure standard library.
"""

import json
import os
import re
import sys
import tempfile
import zipfile

# Each pattern: id, compiled regex, kind, prior, why it might cost tokens, fix.
# prior is the confidence the bare keyword match deserves before context is read:
#   high   - the phrase almost always means the anti-pattern (e.g. str_replace on output)
#   medium - often the anti-pattern, but context can flip it
#   low    - ambiguous; the same words frequently describe something harmless
# Recall is the priority here. Over-collecting is fine: the verify step filters.
PATTERNS = [
    ("manual_html_edit_strong",
     re.compile(r"str_replace|edit(ing)? the (generated |output )?(html|document|docx|file|artifact) (directly|by hand|in place)", re.I),
     "manual-edit", "high",
     "The model may be editing a generated artifact by hand, which forces the whole file into context every cycle.",
     "Extend the generator/update script to cover this edit so the artifact is never loaded into context."),
    ("manual_html_edit_weak",
     re.compile(r"\bby hand\b|\bmanually (edit|adjust|tweak|change)\b|hand[- ]edit", re.I),
     "manual-edit", "low",
     "Something is described as done by hand. If it is the model editing a generated artifact, that is expensive; if it is a human, it is not a finding.",
     "If the model hand-edits an artifact, move the edit into the generator/update script."),
    ("full_regeneration",
     re.compile(r"regenerat\w*( the)?( full| whole| entire| complete)|rebuild the (whole|full|entire)|re[- ]?create the (whole|full|entire|document)", re.I),
     "regeneration", "medium",
     "A whole document may be regenerated when only part changed, spending tokens reproducing unchanged content.",
     "Patch only the changed elements (surgical update) instead of regenerating."),
    ("llm_rewrite_placeholder",
     re.compile(r"placeholder|must review and replace|review and replace|rewrite (the|each|all)|fill in the (prose|text) (each|every)", re.I),
     "llm-rewrite", "low",
     "The model may rewrite generated placeholder text every run. But a placeholder can also be a static token the generator handles, or a privacy stand-in, neither of which is a finding.",
     "If the model rewrites the same authored text each run, persist it in the data file so only new or changed items need the model."),
    ("llm_assembles_json",
     re.compile(r"assembl\w+ .*json|the model (writes|assembles|builds) .*(json|payload|table|ids)|claude (assembles|scores|orders|formats)", re.I),
     "llm-assembly", "medium",
     "The model may assemble structured data (IDs, ordering, scoring, JSON) by reasoning, which is token-heavy and error-prone.",
     "Move deterministic assembly into a script; leave only judgement to the model."),
    ("not_automated",
     re.compile(r"not automated|cannot handle|can't handle|script (does not|doesn't|can't|cannot)|manual additions|left to the model", re.I),
     "coverage-gap", "medium",
     "A gap in script coverage may push work back onto the model, usually as hand-editing.",
     "Close the gap in the script so the whole operation stays in code."),
]

# Credited good practice (reduces, not raises, concern). Surfaced as-is; the
# verifier may note where a credited pattern should be extended to other paths.
GOOD = [
    ("surgical_update", re.compile(r"does not regenerate|surgical|only changed|in[- ]place|patch (the )?changed", re.I),
     "Surgical, in-place updates are used somewhere; extend this to every update path."),
    ("scripts_not_read", re.compile(r"never (read|loaded) into context|run via bash|do not load|run the script", re.I),
     "Scripts are run rather than read into context, which is the efficient pattern."),
    ("progressive", re.compile(r"on demand|load .* only|do not load all|read only the one|progressive disclosure", re.I),
     "Progressive disclosure is used: files load only when needed."),
]


def resolve(path):
    if path.endswith((".skill", ".zip")):
        tmp = tempfile.mkdtemp(prefix="eff_")
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        for root, _d, files in os.walk(tmp):
            if "SKILL.md" in files:
                return root
        raise SystemExit("analyse_efficiency: no SKILL.md inside " + path)
    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            return path
        raise SystemExit("analyse_efficiency: no SKILL.md in " + path)
    if os.path.isfile(path) and path.endswith(".md"):
        return os.path.dirname(os.path.abspath(path)) or "."
    raise SystemExit("analyse_efficiency: cannot handle " + path)


def nearest_heading(lines, idx):
    """Text of the closest markdown heading at or above line index idx (0-based)."""
    for j in range(idx, -1, -1):
        m = re.match(r"^#{1,6}\s+(.*)", lines[j])
        if m:
            return m.group(1).strip()
    return ""


def context_window(lines, idx, radius=2):
    lo = max(0, idx - radius)
    hi = min(len(lines), idx + radius + 1)
    return "\n".join(lines[lo:hi]).strip()


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python3 scripts/analyse_efficiency.py <skill-path> [candidates.json]")
    skill_dir = resolve(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "candidates.json"
    name = os.path.basename(os.path.abspath(skill_dir))

    md_files, scripts = [], []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), skill_dir).replace(os.sep, "/")
            if f.endswith(".md"):
                md_files.append(rel)
            if rel.startswith("scripts/") and f.endswith((".py", ".js", ".sh")):
                scripts.append(rel)

    candidates, credited, seen = [], [], set()
    cn = 0
    for rel in sorted(md_files):
        lines = open(os.path.join(skill_dir, rel), encoding="utf-8").read().splitlines()
        for i, line in enumerate(lines):
            for pid, rx, kind, prior, why, fix in PATTERNS:
                m = rx.search(line)
                if not m:
                    continue
                key = (pid, rel, line.strip()[:80])
                if key in seen:
                    continue
                seen.add(key)
                cn += 1
                candidates.append({
                    "candidate_id": "c%d" % cn,
                    "id": pid,
                    "kind": kind,
                    "prior": prior,
                    "file": rel,
                    "line": i + 1,
                    "trigger": m.group(0),
                    "excerpt": line.strip()[:200],
                    "section": nearest_heading(lines, i),
                    "context": context_window(lines, i),
                    "why": why,
                    "recommendation": fix,
                })
            for gid, rx, note in GOOD:
                if rx.search(line) and gid not in {c["id"] for c in credited}:
                    credited.append({"id": gid, "file": rel, "line": i + 1, "note": note})

    by_kind, by_prior = {}, {}
    for c in candidates:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        by_prior[c["prior"]] = by_prior.get(c["prior"], 0) + 1

    result = {
        "skill": name,
        "stage": "candidates",
        "scripts_present": scripts,
        "summary": {
            "candidates": len(candidates),
            "by_kind": by_kind,
            "by_prior": by_prior,
            "good_practices": [c["id"] for c in credited],
        },
        "candidates": candidates,
        "credited": credited,
        "note": "These are unverified candidates. Run the verify step (references/verification-rubric.md) to produce verdicts.json before reporting.",
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Detection scan of %s: %d candidate(s) across %d markdown file(s); %d good practice(s) credited." % (
        name, len(candidates), len(md_files), len(credited)))
    print("By kind: " + (", ".join("%s=%d" % (k, v) for k, v in sorted(by_kind.items())) or "none"))
    print("By prior: " + (", ".join("%s=%d" % (k, v) for k, v in sorted(by_prior.items())) or "none"))
    print("Wrote %s. Candidates are unverified; run the verify step next." % out)


if __name__ == "__main__":
    main()
