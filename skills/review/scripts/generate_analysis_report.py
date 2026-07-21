#!/usr/bin/env python3
"""
generate_analysis_report.py - render a verified skill-analysis as a clean,
self-contained HTML report.

Usage:
    python3 scripts/analyse_efficiency.py <skill> candidates.json
    # then the model-driven verify step writes verdicts.json
    python3 scripts/generate_analysis_report.py verdicts.json report.html \
        [--candidates candidates.json] [--structure analysis.json] [--brand brand.json]

The primary input is verdicts.json: the adjudicated output of the verify step,
where each detection candidate has been judged in context as confirmed,
suppressed, or uncertain, and any novel findings the keyword categories missed
have been added. The report renders three tiers so nothing is hidden:

  - Confirmed   -> prioritised recommendations, the only tier handed to net-positive-skillify:update
  - Uncertain   -> flagged for a human eye, not actioned automatically
  - Suppressed  -> shown collapsed, WITH the reason, so over-suppression is auditable

By default the report uses a neutral built-in theme. Pass --brand pointing at a
small JSON file (see assets/brand.example.json) to embed your own identity. Pure
standard library.
"""

import base64
import html
import json
import os
import sys

DEFAULT_BRAND = {
    "name": "",
    "accent": "#1f6f78",
    "accent_dark": "#16545b",
    "logo": "",
    "footer": "Generated with the assistance of AI.",
}

THEME = """
*{box-sizing:border-box}
body{margin:0;background:#f5f6f7;color:#1c2426;line-height:1.6;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:24px 20px 8px}
.report-header{display:flex;align-items:center;justify-content:space-between;gap:16px;
 background:__ACCENT__;color:#fff;padding:16px 22px;border-radius:10px 10px 0 0}
.report-header .brand{display:flex;align-items:center;gap:12px;font-weight:600;font-size:16px}
.report-header .brand-logo{height:32px;width:auto;display:block}
.report-header .report-kind{font-size:12px;opacity:.85;text-transform:uppercase;letter-spacing:.07em}
main{background:#fff;border:1px solid #e3e7e8;border-top:none;border-radius:0 0 10px 10px;padding:26px 30px}
h1{font-size:24px;margin:.1em 0 .5em}
h2{font-size:17px;margin:1.6em 0 .5em;padding-bottom:6px;border-bottom:2px solid #eef1f2}
p{margin:.55em 0}
code{background:#eef2f3;padding:1px 5px;border-radius:4px;font-size:.92em}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:14px}
th,td{border:1px solid #dde3e4;padding:8px 10px;text-align:left;vertical-align:top}
th{background:__ACCENT_DARK__;color:#fff;font-weight:600}
tr:nth-child(even) td{background:#fafbfb}
ul{margin:.5em 0;padding-left:1.2em}
li{margin:.25em 0}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600}
.pill.high{background:#e7f4ec;color:#1d6b3f}
.pill.medium{background:#fff4e0;color:#92600c}
.pill.low{background:#eef2f3;color:#566}
.counts{display:flex;flex-wrap:wrap;gap:10px;margin:.6em 0}
.count{flex:1 1 120px;border:1px solid #e3e7e8;border-radius:8px;padding:10px 12px}
.count .n{font-size:22px;font-weight:700}
.count .l{font-size:12px;color:#6b7678;text-transform:uppercase;letter-spacing:.05em}
details{border:1px solid #e3e7e8;border-radius:8px;padding:8px 12px;margin:.8em 0;background:#fafbfb}
summary{cursor:pointer;font-weight:600}
.muted{color:#6b7678}
.finding{border:1px solid #e3e7e8;border-left:3px solid __ACCENT__;border-radius:6px;padding:10px 14px;margin:.8em 0;background:#fafbfb}
.finding-head{font-weight:600;margin-bottom:.3em}
.finding p{margin:.4em 0}
footer{max-width:860px;margin:16px auto 0;padding:0 22px 32px;color:#7a8688;font-size:12px}
"""

KIND_PRIORITY = ["manual-edit", "coverage-gap", "regeneration", "llm-rewrite", "llm-assembly"]
CONF_RANK = {"high": 0, "medium": 1, "low": 2}


def opt(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def esc(s):
    return html.escape(str(s if s is not None else ""))


def pill(conf):
    c = (conf or "low").lower()
    return '<span class="pill %s">%s</span>' % (esc(c), esc(c))


def embed_logo(logo):
    if not logo:
        return ""
    if logo.startswith(("http://", "https://", "data:")):
        return logo
    if os.path.isfile(logo):
        ext = os.path.splitext(logo)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "svg": "image/svg+xml", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        data = base64.b64encode(open(logo, "rb").read()).decode()
        return "data:%s;base64,%s" % (mime, data)
    sys.stderr.write("generate_analysis_report: logo not found (%s); omitting it.\n" % logo)
    return ""


def sort_key(v):
    k = v.get("kind", "")
    return (KIND_PRIORITY.index(k) if k in KIND_PRIORITY else 99,
            CONF_RANK.get((v.get("confidence") or "low").lower(), 2))


def build_body(verd, cand, struct):
    name = verd.get("skill", "skill")
    verdicts = verd.get("verdicts", [])
    novel = verd.get("novel", [])

    confirmed = sorted([v for v in verdicts if v.get("verdict") == "confirmed"], key=sort_key)
    uncertain = sorted([v for v in verdicts if v.get("verdict") == "uncertain"], key=sort_key)
    suppressed = [v for v in verdicts if v.get("verdict") == "suppressed"]

    # counts banner (governance/security counts appended only when present)
    governance = verd.get("governance", [])
    security = verd.get("security", [])
    counts = [
        ("Confirmed", len(confirmed)),
        ("Uncertain", len(uncertain)),
        ("Suppressed", len(suppressed)),
        ("Novel", len(novel)),
    ]
    if governance:
        counts.append(("Governance", len(governance)))
    if security:
        counts.append(("Security", len(security)))
    counts_html = '<div class="counts">' + "".join(
        '<div class="count"><div class="n">%d</div><div class="l">%s</div></div>' % (n, esc(l))
        for l, n in counts) + "</div>"

    # confirmed -> prioritised recommendations
    rec_rows = []
    rank = 1
    for v in confirmed:
        rec_rows.append(
            "<tr><td>%d</td><td>%s</td><td>%s</td><td><code>%s:%s</code></td><td>%s</td></tr>" % (
                rank, esc(v.get("kind", "")), pill(v.get("confidence")),
                esc(v.get("file", "")), esc(v.get("line", "")), esc(v.get("recommendation", ""))))
        rank += 1
    rec_html = (
        "<table><tr><th>#</th><th>Kind</th><th>Confidence</th><th>Location</th><th>Recommendation</th></tr>%s</table>"
        % (("".join(rec_rows)) or "<tr><td colspan=5>No confirmed recommendations. Nothing to action.</td></tr>"))

    # Reusable full-text finding section: a heading, a caveat intro, then one
    # bordered block per finding with observation + recommendation. Used for the
    # open-ended (code-over-model) findings and, when present, the out-of-scope
    # governance and security passes.
    def findings_section(title, intro, items):
        if not items:
            return ""
        blocks = ""
        for it in items:
            label = it.get("category", it.get("kind", "general"))
            obs = esc(it.get("observation", ""))
            rec = esc(it.get("recommendation", it.get("note", "")))
            blocks += (
                "<div class='finding'>"
                "<div class='finding-head'>%s %s &middot; <code>%s:%s</code></div>"
                "%s%s</div>") % (
                    esc(label), pill(it.get("confidence", "low")),
                    esc(it.get("file", "")), esc(it.get("line", "")),
                    ("<p>%s</p>" % obs) if obs else "",
                    ("<p><strong>Recommendation:</strong> %s</p>" % rec) if rec else "")
        return "<h2>%s</h2><p class='muted'>%s</p>%s" % (esc(title), esc(intro), blocks)

    novel_html = findings_section(
        "Code over model: open-ended findings",
        "These are not keyword matches. The verifier read the whole skill and looked for expensive "
        "run-time patterns the five categories would miss, chiefly the model doing deterministic work a "
        "script could do. They are marked low confidence by design, since they come from reading the "
        "skill rather than observing a run: treat them as leads to weigh, not settled flags.",
        novel)

    governance_html = findings_section(
        "Governance findings (out of scope for efficiency)",
        "First-pass triage only, and not a substitute for a proper governance or data-protection review. "
        "These are concrete things noticed while reading the skill that fall outside its efficiency remit, "
        "for example transparency, human oversight, and automated decision-making. Each is a lead for the "
        "right owner to weigh, not an adjudicated finding.",
        governance)

    security_html = findings_section(
        "Security findings (out of scope for efficiency)",
        "First-pass triage only, and not a substitute for a proper security review. These are concrete "
        "things noticed while reading the skill that fall outside its efficiency remit, for example egress, "
        "control bypasses, and untrusted-input handling. Each is a lead for the right owner to weigh, not "
        "an adjudicated finding.",
        security)

    # uncertain
    unc_html = ""
    if uncertain:
        rows = "".join(
            "<tr><td>%s</td><td><code>%s:%s</code></td><td>%s</td></tr>" % (
                esc(v.get("kind", "")), esc(v.get("file", "")), esc(v.get("line", "")),
                esc(v.get("reason", "")))
            for v in uncertain)
        unc_html = (
            "<h2>Needs a human eye</h2>"
            "<p class='muted'>The verifier could not settle these from the surrounding context. "
            "Review before deciding; they are not handed to net-positive-skillify:update automatically.</p>"
            "<table><tr><th>Kind</th><th>Location</th><th>Why it is unclear</th></tr>%s</table>" % rows)

    # suppressed, collapsed but auditable
    sup_html = ""
    if suppressed:
        items = "".join(
            "<li><code>%s:%s</code> (%s) &mdash; %s</li>" % (
                esc(v.get("file", "")), esc(v.get("line", "")), esc(v.get("kind", "")),
                esc(v.get("reason", "no reason given")))
            for v in suppressed)
        sup_html = (
            "<details><summary>Suppressed candidates (%d) &mdash; shown for audit</summary>"
            "<p class='muted'>Detection flagged these, but verification judged them not real, "
            "for the reason given. If a reason looks wrong, that is a false suppression to correct.</p>"
            "<ul>%s</ul></details>" % (len(suppressed), items))

    # credited good practice (from candidates.json if provided, else verdicts)
    credited = (cand or {}).get("credited", []) or verd.get("credited", [])
    good_html = ""
    if credited:
        good_html = "<h2>Credited good practice</h2><ul>%s</ul>" % "".join(
            "<li>%s</li>" % esc(c.get("note", "")) for c in credited)

    # structure
    struct_html = ""
    if struct:
        sm = struct.get("skill_md", {})
        fl = {k: v for k, v in struct.get("flags", {}).items() if v}
        recs = struct.get("recommendations", [])
        struct_html = (
            "<h2>Structure</h2><p>SKILL.md body: <strong>%d lines</strong> (~%d tokens). "
            "Reference files: %d. Scripts: %d.</p>" % (
                sm.get("body_lines", 0), sm.get("token_estimate", 0),
                len(struct.get("structure", {}).get("reference_files", [])),
                len(struct.get("structure", {}).get("script_files", []))) +
            ("<ul>%s</ul>" % "".join("<li>%s</li>" % esc(r) for r in recs)
             if recs and not (len(recs) == 1 and recs[0].startswith("No structural"))
             else "<p>No structural issues found.</p>"))

    gate = (
        "<h2>Next step: your decision</h2>"
        "<p>This is an analysis only. No files have been changed. Only the <strong>confirmed</strong> "
        "tier is proposed for action. Approve it and the companion <strong>net-positive-skillify:update</strong> step "
        "applies the changes <em>surgically</em>, using the skill's own scripts and targeted edits "
        "rather than regenerating whole files.</p>")

    return (
        "<h1>%s</h1>" % esc(name) +
        "<p>Findings are <strong>verified</strong>: each detection candidate was judged in context "
        "before reaching this report, so a flag here means it survived that check. "
        "Suppressed candidates are listed too, with reasons, so the filtering itself can be audited.</p>" +
        counts_html +
        struct_html +
        "<h2>Confirmed recommendations</h2>" + rec_html +
        novel_html +
        governance_html +
        security_html +
        unc_html +
        sup_html +
        good_html +
        gate)


def render_page(title, body, brand):
    css = THEME.replace("__ACCENT__", brand["accent"]).replace("__ACCENT_DARK__", brand["accent_dark"])
    # extra_css lets a brand file restyle beyond the two accents (fonts, page
    # background, pill palette) without touching the engine. Appended last so it
    # wins the cascade.
    extra = brand.get("extra_css", "")
    if extra:
        css += "\n" + extra.replace("__ACCENT__", brand["accent"]).replace("__ACCENT_DARK__", brand["accent_dark"])
    name = brand.get("name") or ""
    logo_src = embed_logo(brand.get("logo", ""))
    logo_html = '<img class="brand-logo" src="%s" alt="%s">' % (logo_src, esc(name) or "logo") if logo_src else ""
    inner = logo_html + ('<span>%s</span>' % esc(name) if name else "")
    brand_html = '<div class="brand">%s</div>' % inner
    footer = brand.get("footer", DEFAULT_BRAND["footer"])
    footer_html = "<footer>%s</footer>" % esc(footer) if footer else ""
    kind_label = brand.get("kind_label", "Skill analysis (verified)")
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s</title><style>%s</style></head><body>'
        '<div class="wrap"><header class="report-header">%s'
        '<span class="report-kind">%s</span></header>'
        '<main>%s</main></div>%s</body></html>'
        % (esc(title), css, brand_html, esc(kind_label), body, footer_html))


def main():
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    for flag in ("--structure", "--brand", "--candidates"):
        v = opt(flag)
        if v in positional:
            positional.remove(v)
    if len(positional) < 2:
        raise SystemExit("usage: generate_analysis_report.py <verdicts.json> <output.html> "
                         "[--candidates candidates.json] [--structure analysis.json] [--brand brand.json]")

    verd = json.load(open(positional[0], encoding="utf-8"))
    out_path = positional[1]

    cand = None
    cp = opt("--candidates")
    if cp and os.path.isfile(cp):
        cand = json.load(open(cp, encoding="utf-8"))

    struct = None
    sp = opt("--structure")
    if sp and os.path.isfile(sp):
        struct = json.load(open(sp, encoding="utf-8"))

    brand = dict(DEFAULT_BRAND)
    bp = opt("--brand")
    if bp:
        if not os.path.isfile(bp):
            raise SystemExit("generate_analysis_report: brand file not found: %s" % bp)
        brand.update({k: v for k, v in json.load(open(bp, encoding="utf-8")).items() if v is not None})
        # A relative logo path resolves against the brand file's own folder, so a
        # brand file shipped inside the skill works from any working directory.
        logo = brand.get("logo", "")
        if logo and not logo.startswith(("http://", "https://", "data:")) and not os.path.isabs(logo):
            candidate = os.path.join(os.path.dirname(os.path.abspath(bp)), logo)
            if os.path.isfile(candidate):
                brand["logo"] = candidate

    body = build_body(verd, cand, struct)
    page = render_page("Skill analysis: " + verd.get("skill", "skill"), body, brand)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print("Wrote %s%s" % (out_path, " (branded)" if bp else " (default theme)"))


if __name__ == "__main__":
    main()
