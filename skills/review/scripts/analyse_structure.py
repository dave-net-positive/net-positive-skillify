#!/usr/bin/env python3
"""
analyse_skill.py - inspect a single Agent Skill and report on its structure
against the Agent Skills specification (agentskills.io) and Claude's authoring
best practices.

Usage:
    python3 scripts/analyse_skill.py <path> [analysis.json]

<path> may be a skill directory, a lone SKILL.md, or a .skill/.zip container.
Writes analysis.json and a neutral analysis.md next to the JSON, and prints a
short summary. Pure standard library.
"""

import json
import os
import re
import sys
import tempfile
import zipfile

# --- thresholds (justified, not magic) ---
SKILLMD_MAX_LINES = 500       # best-practice line ceiling for SKILL.md body
SKILLMD_WARN_LINES = 300      # approaching the ceiling; consider splitting soon
SKILLMD_TOKEN_BUDGET = 5000   # spec: SKILL.md body should load under ~5k tokens
SECTION_CHUNK_LINES = 60      # an H2 section this long is a candidate to move out
REF_TOC_LINES = 100           # reference files longer than this should carry a TOC
DESC_MAX = 1024               # frontmatter description hard limit
NAME_MAX = 64                 # frontmatter name hard limit
COMPAT_MAX = 500              # frontmatter compatibility hard limit
RESERVED = ("claude", "anthropic")
REF_PREFIXES = ("references/", "reference/")  # spec uses plural; accept both
KNOWN_FM_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")

# full spec name rule: lowercase alnum and single hyphens, no leading/trailing/
# consecutive hyphens
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DOC_GEN_KEYWORDS = [
    "docx", "pptx", "xlsx", ".pdf", "present_files", "create_file", "artifact",
    ".html", "generate_", "ooxml", "spreadsheet", "word document",
    "presentation", "slide deck",
]
DEP_HINTS = re.compile(r"(requires |install |pip install|npm install|python3|node\b|node\.js)", re.I)


def parse_frontmatter(text):
    """Return (frontmatter_dict, body). Handles scalars, quoted values,
    '>'/'|' block scalars, and one level of nested map (for metadata)."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    body = "\n".join(lines[end + 1:])
    fm = {}
    i = 1
    while i < end:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            j = i + 1
            while j < end and (lines[j].startswith((" ", "\t")) or lines[j].strip() == ""):
                block.append(lines[j].strip())
                j += 1
            fm[key] = " ".join(b for b in block if b).strip()
            i = j
            continue
        if val == "":
            nested = {}
            j = i + 1
            while j < end and lines[j].startswith((" ", "\t")):
                mm = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", lines[j])
                if mm:
                    nested[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
                j += 1
            fm[key] = nested if nested else ""
            i = j
            continue
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        fm[key] = val
        i += 1
    return fm, body


def find_sections(body):
    lines = body.splitlines()
    heads = [(i, l[3:].strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    out = []
    for idx, (ln, title) in enumerate(heads):
        nxt = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        out.append({"title": title, "start_line": ln + 1, "lines": nxt - ln})
    return out


def resolve_input(path):
    """Return (skill_dir, skill_md_path, lone)."""
    if path.endswith(".skill") or path.endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="skill_analyse_")
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        for root, _dirs, files in os.walk(tmp):
            if "SKILL.md" in files:
                return root, os.path.join(root, "SKILL.md"), False
        raise SystemExit("analyse_skill: no SKILL.md found inside " + path)
    if os.path.isdir(path):
        smd = os.path.join(path, "SKILL.md")
        if not os.path.isfile(smd):
            raise SystemExit("analyse_skill: no SKILL.md in directory " + path)
        return path, smd, False
    if os.path.isfile(path) and path.endswith(".md"):
        return os.path.dirname(os.path.abspath(path)) or ".", path, True
    raise SystemExit("analyse_skill: cannot handle input " + path)


def list_tree(skill_dir):
    files = []
    for root, dirs, fnames in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in fnames:
            rel = os.path.relpath(os.path.join(root, f), skill_dir)
            files.append(rel.replace(os.sep, "/"))
    return sorted(files)


def name_issues(name, dirname, lone):
    issues = []
    if not name:
        return ["name is empty"]
    if len(name) > NAME_MAX:
        issues.append("over %d characters" % NAME_MAX)
    if not NAME_RE.match(name):
        issues.append("must be lowercase alphanumeric with single hyphens (no leading, trailing, or consecutive hyphens)")
    if any(r in name for r in RESERVED):
        issues.append("contains a reserved word (%s)" % " / ".join(RESERVED))
    if not lone and dirname and name != dirname:
        issues.append('does not match the parent directory name "%s"' % dirname)
    return issues


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python3 scripts/analyse_skill.py <path> [analysis.json]")
    in_path = sys.argv[1]
    out_json = sys.argv[2] if len(sys.argv) > 2 else "analysis.json"

    skill_dir, smd_path, lone = resolve_input(in_path)
    text = open(smd_path, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    body_lines = len(body.splitlines())
    token_est = len(body) // 4

    files = list_tree(skill_dir)
    ref_files = [f for f in files if f.startswith(REF_PREFIXES) and f.endswith(".md")]
    script_files = [f for f in files if f.startswith("scripts/")]
    asset_files = [f for f in files if f.startswith("assets/")]
    only_skillmd = lone or files == ["SKILL.md"]
    dirname = os.path.basename(os.path.abspath(skill_dir))

    name = fm.get("name", "")
    desc = fm.get("description", "")
    compat = fm.get("compatibility", "")
    nissues = name_issues(name, dirname, lone)
    name_valid = not nissues
    desc_ok = bool(desc) and len(desc) <= DESC_MAX
    desc_has_when = bool(re.search(r"(use when|when the user|triggers?|trigger:)", desc, re.I))
    unknown_fields = [k for k in fm if k not in KNOWN_FM_FIELDS]

    sections = find_sections(body)
    chunk_candidates = [s for s in sections if s["lines"] >= SECTION_CHUNK_LINES]

    low = text.lower()
    evidence = sorted({k.strip() for k in DOC_GEN_KEYWORDS if k in low})
    generates_documents = len(evidence) > 0
    has_scripts = len(script_files) > 0

    # deep nesting: a reference file links to a references/*.md that SKILL.md
    # does not link to directly (only reachable through another reference file)
    def norm_link(base_rel, link):
        link = link.split("#")[0].strip()
        if not link or link.startswith(("http://", "https://", "mailto:")):
            return None
        return os.path.normpath(os.path.join(os.path.dirname(base_rel), link)).replace(os.sep, "/")

    smd_links = set()
    for link in re.findall(r"\]\(([^)]+)\)", body):
        n = norm_link("SKILL.md", link)
        if n:
            smd_links.add(n)
    deep_nesting = []
    for rf in ref_files:
        for link in re.findall(r"\]\(([^)]+)\)", open(os.path.join(skill_dir, rf), encoding="utf-8").read()):
            n = norm_link(rf, link)
            if not n or not n.endswith(".md") or n.endswith("SKILL.md"):
                continue
            if n.startswith(REF_PREFIXES) and n not in smd_links:
                deep_nesting.append({"file": rf, "links_to": n})

    win_paths = bool(re.search(r"[A-Za-z0-9_]+\\[A-Za-z0-9_]+", text))
    time_sensitive = bool(re.search(r"(before|after|as of|until)\s+20\d\d", low))

    missing_toc = []
    toc_heading = re.compile(r"^#{1,6}\s+(table of\s+)?contents\b", re.I)
    for rf in ref_files:
        rlines = open(os.path.join(skill_dir, rf), encoding="utf-8").read().splitlines()
        if len(rlines) <= REF_TOC_LINES:
            continue
        # A Contents list counts wherever it sits: a "Contents" heading anywhere,
        # or the literal word in the top of the file. Not tied to a line window,
        # so a TOC below a long preamble is still recognised.
        has_toc = any(toc_heading.match(ln) for ln in rlines) or \
            "contents" in "\n".join(rlines[:25]).lower()
        if not has_toc:
            missing_toc.append(rf)

    mentions_deps = bool(DEP_HINTS.search(text))

    flags = {
        "skillmd_over_max_lines": body_lines > SKILLMD_MAX_LINES,
        "skillmd_approaching_max_lines": SKILLMD_WARN_LINES < body_lines <= SKILLMD_MAX_LINES,
        "skillmd_over_token_budget": token_est > SKILLMD_TOKEN_BUDGET,
        "name_invalid": not name_valid,
        "description_problem": not desc_ok or not desc_has_when,
        "compatibility_too_long": bool(compat) and len(compat) > COMPAT_MAX,
        "missing_compatibility": mentions_deps and not compat,
        "unknown_frontmatter_fields": len(unknown_fields) > 0,
        "lone_skillmd": only_skillmd,
        "doc_gen_without_scripts": generates_documents and not has_scripts,
        "deep_nesting": len(deep_nesting) > 0,
        "windows_paths": win_paths,
        "time_sensitive": time_sensitive,
        "missing_toc_on_long_refs": len(missing_toc) > 0,
    }

    recs = []
    if flags["skillmd_over_max_lines"]:
        recs.append("SKILL.md body is %d lines (over %d). Move large sections into references/ files." % (body_lines, SKILLMD_MAX_LINES))
    elif flags["skillmd_approaching_max_lines"]:
        recs.append("SKILL.md body is %d lines (approaching the %d ceiling). Consider splitting soon." % (body_lines, SKILLMD_MAX_LINES))
    if flags["skillmd_over_token_budget"]:
        recs.append("SKILL.md body is ~%d tokens (over the ~%d budget). Trim or split it." % (token_est, SKILLMD_TOKEN_BUDGET))
    if chunk_candidates:
        recs.append("Chunk candidates (sections >= %d lines): %s." % (SECTION_CHUNK_LINES, ", ".join(c["title"] for c in chunk_candidates)))
    if flags["name_invalid"]:
        recs.append('Frontmatter name "%s" is invalid: %s.' % (name, "; ".join(nissues)))
    if not desc:
        recs.append("Frontmatter description is empty. State what the skill does and when to use it, with trigger phrases.")
    elif len(desc) > DESC_MAX:
        recs.append("Description is %d chars (over %d). Trim it." % (len(desc), DESC_MAX))
    elif not desc_has_when:
        recs.append("Description does not say WHEN to use the skill. Add trigger phrases / 'Use when ...'.")
    if flags["compatibility_too_long"]:
        recs.append("compatibility is %d chars (over %d). Shorten it." % (len(compat), COMPAT_MAX))
    if flags["missing_compatibility"]:
        recs.append("SKILL.md mentions runtime requirements but no 'compatibility' frontmatter field is set. Add one (for example 'Requires Python 3' or 'Requires Node').")
    if flags["unknown_frontmatter_fields"]:
        recs.append("Unrecognised frontmatter field(s): %s. Allowed: name, description, license, compatibility, metadata, allowed-tools." % ", ".join(unknown_fields))
    if flags["lone_skillmd"]:
        recs.append("Skill exists only as a SKILL.md. Refactor into a .skill container with references/ and scripts/ as needed.")
    if flags["doc_gen_without_scripts"]:
        recs.append("Skill generates documents/artifacts (%s) but bundles no scripts. Add deterministic generator scripts so they are run, not regenerated each time." % ", ".join(evidence))
    if flags["deep_nesting"]:
        recs.append("Reference files link to other reference files not reachable from SKILL.md (deep nesting). Keep all references one level deep from SKILL.md.")
    if flags["windows_paths"]:
        recs.append("Possible Windows-style paths found. Use forward slashes everywhere.")
    if flags["time_sensitive"]:
        recs.append("Possible time-sensitive wording found. Move dated guidance into an 'old patterns' section.")
    if flags["missing_toc_on_long_refs"]:
        recs.append("Reference files over %d lines without a Contents list: %s." % (REF_TOC_LINES, ", ".join(missing_toc)))
    if not recs:
        recs.append("No structural issues found. The skill already follows the key best practices.")

    analysis = {
        "input": in_path,
        "skill_dir": skill_dir,
        "directory_name": dirname,
        "frontmatter": {
            "name": name, "name_valid": name_valid, "name_issues": nissues,
            "description_length": len(desc), "description_ok": desc_ok,
            "description_states_when": desc_has_when,
            "license": fm.get("license", ""), "compatibility": compat,
            "metadata": fm.get("metadata", ""), "allowed_tools": fm.get("allowed-tools", ""),
            "unknown_fields": unknown_fields,
        },
        "skill_md": {"body_lines": body_lines, "char_count": len(body),
                     "token_estimate": token_est, "sections": sections,
                     "chunk_candidates": chunk_candidates},
        "structure": {"files": files, "reference_files": ref_files,
                       "script_files": script_files, "asset_files": asset_files,
                       "only_skillmd": only_skillmd},
        "generation": {"generates_documents": generates_documents,
                        "evidence": evidence, "has_scripts": has_scripts},
        "flags": flags,
        "details": {"deep_nesting": deep_nesting, "missing_toc": missing_toc},
        "recommendations": recs,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    md_path = (os.path.splitext(out_json)[0] + ".md") if out_json.endswith(".json") else out_json + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Skill analysis: %s\n\n" % (name or dirname))
        f.write("- Input: `%s`\n" % in_path)
        f.write("- SKILL.md body: %d lines (~%d tokens; budget ~%d)\n" % (body_lines, token_est, SKILLMD_TOKEN_BUDGET))
        f.write("- Name valid: %s%s\n" % ("yes" if name_valid else "no", "" if name_valid else " (" + "; ".join(nissues) + ")"))
        f.write("- Description: %d / %d chars; states when: %s\n" % (len(desc), DESC_MAX, "yes" if desc_has_when else "no"))
        f.write("- Optional fields: license=%s, compatibility=%s, metadata=%s\n" % (
            "set" if fm.get("license") else "none",
            "set" if compat else "none",
            "set" if fm.get("metadata") else "none"))
        f.write("- Reference files: %d | Scripts: %d | Assets: %d\n" % (len(ref_files), len(script_files), len(asset_files)))
        f.write("- Generates documents: %s%s\n\n" % ("yes" if generates_documents else "no",
                 (" (" + ", ".join(evidence) + ")") if evidence else ""))
        f.write("## Recommendations\n\n")
        for r in recs:
            f.write("- %s\n" % r)
        if chunk_candidates:
            f.write("\n## Chunk candidates\n\n")
            for c in chunk_candidates:
                f.write("- %s (%d lines)\n" % (c["title"], c["lines"]))

    print("Analysed %s: %d-line SKILL.md (~%d tok), %d reference file(s), %d script(s); %d recommendation(s)." % (
        name or dirname, body_lines, token_est, len(ref_files), len(script_files), len(recs)))
    print("Wrote %s and %s" % (out_json, md_path))


if __name__ == "__main__":
    main()
