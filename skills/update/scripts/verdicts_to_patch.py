#!/usr/bin/env python3
"""
verdicts_to_patch.py - seed a patch skeleton from a review's confirmed tier.

Usage:
    python3 scripts/verdicts_to_patch.py verdicts.json <target-skill-dir> [patch.json]

Reads a net-positive-skillify:review verdicts.json and converts every confirmed verdict
into a stub edit in a patch.json skeleton. Suppressed and uncertain verdicts are
never included: suppressed findings are not findings, and uncertain ones go back
to a human. Novel findings are listed in a note for consideration but are not
turned into edits automatically, since they are low-confidence leads.

The deterministic part (structure, metadata, filtering by verdict) is done here;
the judgement (authoring the exact find/replace strings) stays with the model,
which fills in each stub. apply_patch.py refuses empty find strings, so an
unauthored stub cannot be applied by accident. Pure standard library.
"""

import json
import os
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: python3 scripts/verdicts_to_patch.py verdicts.json <target-skill-dir> [patch.json]")
    verd = json.load(open(sys.argv[1], encoding="utf-8"))
    target = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "patch.json"
    if not os.path.isdir(target):
        raise SystemExit("verdicts_to_patch: target dir not found: %s" % target)

    confirmed = [v for v in verd.get("verdicts", []) if v.get("verdict") == "confirmed"]
    novel = verd.get("novel", [])

    edits = []
    for v in confirmed:
        edits.append({
            "file": v.get("file", ""),
            "find": "",
            "replace": "",
            "count": 1,
            "_from_verdict": {
                "candidate_id": v.get("candidate_id", ""),
                "kind": v.get("kind", ""),
                "line": v.get("line", 0),
                "recommendation": v.get("recommendation", ""),
            },
            "_todo": "Author the exact find/replace for this recommendation, then delete the _from_verdict and _todo keys.",
        })

    patch = {
        "target_dir": os.path.abspath(target),
        "skill": verd.get("skill", ""),
        "edits": edits,
    }
    if novel:
        patch["_novel_note"] = (
            "%d novel (low-confidence) finding(s) in the review were NOT converted to edits. "
            "Discuss with the user before acting on: %s" % (
                len(novel),
                "; ".join("%s (%s:%s)" % (n.get("kind", "general"), n.get("file", ""), n.get("line", "")) for n in novel)))

    with open(out, "w", encoding="utf-8") as f:
        json.dump(patch, f, indent=2)

    print("Seeded %s: %d stub edit(s) from %d confirmed verdict(s)." % (out, len(edits), len(confirmed)))
    if not confirmed:
        print("Nothing confirmed in the review; if you are applying structural fixes or user-requested changes, author patch.json by hand.")
    if novel:
        print("Note: %d novel finding(s) were not converted; see _novel_note in the patch." % len(novel))
    print("Next: author each stub's find/replace, dry-run apply_patch.py, then apply.")


if __name__ == "__main__":
    main()
