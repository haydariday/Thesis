"""Build thesis-progress-report.docx from thesis-progress-report.md on the programme template.

Usage (from any directory):
    python3 docs/thesis-1/build_docx.py           # live Zotero citations (Zotero + Better BibTeX running)
    python3 docs/thesis-1/build_docx.py --plain   # no Zotero: citations stay as [@key] text (layout check only)

The template (template/FORMAT THESIS PROGRESS REPORT in Word.docx) is filled in place: the cover fields, the
revision table and the schedule table get the report values, and each section's guidance text is replaced by
the report text. The numeric citations in the Markdown are turned back into Better BibTeX keys, so the .docx
carries live Zotero fields. After building, open the file in OnlyOffice > Plugins > Zotero, choose IEEE and
Refresh. Then put the cursor in the empty paragraph under "References" and insert the bibliography.
"""
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "thesis-progress-report.md"
TEMPLATE = HERE / "template/FORMAT THESIS PROGRESS REPORT in Word.docx"
LUA = HERE.parent / "conference/sub/chapter 1/zotero.lua"
OUT = HERE / "thesis-progress-report.docx"

COVER = {
    "Research Title": "Persona-Based Multi-Agent LLM Debate as an Automated Playtester: "
                      "Validating Game Difficulty Data Against Human Performance Baselines",
    "NAME [NIM]": "Muhammad Haydar Maulana [203012510020]",
    "Concentration": "Informatics Software Engineering",
    "(E-mail address)": "(haydariday@gmail.com)",
}
# The report date comes from the "(Reported on …)" line of the Markdown.
_REPORTED = re.search(r"^\(Reported on [^)]*\)$", SRC.read_text(encoding="utf-8"), re.M)
if _REPORTED:
    COVER["(Reported on MM/DD/YYYY)"] = _REPORTED.group(0)
SUPERVISORS = {"(I)": "( Dr. Arfive Gandhi S.T., M.T.I. )",
               "(II)": "( Dr. Eng. Jati Hiliamsyah Husen S.T., M.Eng. )"}

# Reference list entry (by a distinctive substring) -> Better BibTeX key in Zotero.
KEYS = {
    "C. Xiao": "xiao2025", "M. Weber": "weber2020", "Karavidas": "karavidas2022", "Romero-Mendez": "romero2023",
    "Alvarado Villa": "alvarado2021", "Prasetya": "prasetya2026", "Y. Zhao": "zhao2025",
    "Francillette": "francillette2025", "Delfosse": "delfosse2025", "ChessGPT": "feng2023", "PokeLLMon": "hu2024",
    "Voyager": "wang2023", "Sreedhar": "sreedhar2025", "Constant": "constant2017", "Holmgård": "holmgard2019",
    "T. Liang": "liang2024", "Smit": "smit2024", "Gudmundsson": "gudmundsson2018", "Bateni": "bateni2024",
    "MIMIC": "chen2025", "Y. Du": "du2024", "Baltaji": "baltaji2024", "Thompson": "thompson1987",
    "Julious": "julious2005", "Engaging Data": "engagingdata", "Drachen": "drachen2009", "R. C. Wilson": "wilson2014",
    "Bertsimas": "bertsimas2025", "J. Liang": "liang2025", "Licato": "licato2025", "Atkins": "atkins2022",
}

# Markdown heading -> section id. The template already has these headings, so only their content is inserted.
SECTIONS = {
    "## Progress Summary": "summary",
    "### Previous revisions": "revisions",
    "## 1. Background": "background",
    "## 2. Objective and Hypotheses": "objective",
    "## 3. Research Method": "method",
    "### 3.1 Existing software/system/method": "m1",
    "### 3.2 Software/system/method requirement specification": "m2",
    "### 3.3 Design of the software/system/method": "m3",
    "### 3.4 Experiment design": "m5",
    "## 4. Experiment result": "results",
    "## 5. Analysis of the experiment result": "analysis",
    "## 6. Schedule Realization": "schedule",
}
# Template heading text -> (section id, number of guidance elements after it that the content replaces).
TEMPLATE_SLOTS = [
    ("Progress Summary: (max 500 words)", "summary", 2),
    ("Background", "background", 4),
    ("Objective and Hypotheses", "objective", 3),
    ("Research Method (Metode Penelitian)", "method", 1),
    ("Existing software/system/method", "m1", 1),
    ("Software/system/method requirement specification", "m2", 1),
    ("Design of the software/system/method", "m3", 1),
    ("Experiment result", "m5", 1),
    ("Analysis of the experiment result", "analysis", 2),
    ("Schedule Realization", "schedule", 0),
]
# Template headings left out of the report: (heading text, number of guidance elements after it).
TEMPLATE_DROPS = {"Software/system/method implementation Result": 1}
# Template headings whose text the report changes.
TEMPLATE_RENAMES = {"Experiment result": "Experiment design"}
# Headings the template lacks: (title, section id) inserted before a template heading, in the same style.
TEMPLATE_INSERTS = {"Analysis of the experiment result": [("Experiment result", "results")]}

SUBHEADING_STYLE = (
    '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SubHeading"><w:name w:val="Sub Heading"/>'
    '<w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:qFormat/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="2"/></w:pPr>'
    '<w:rPr><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_of(xml):
    return "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml))


def top_level(body):
    """Split a <w:body> inner string into its top-level elements (paragraphs, tables, sectPr)."""
    tag = re.compile(r"<(/?)w:(p|tbl|sectPr)([ >/])")
    out, depth, start, kind = [], 0, None, None
    pos = 0
    while True:
        m = tag.search(body, pos)
        if not m:
            break
        closing, name = m.group(1) == "/", m.group(2)
        end = body.index(">", m.start()) + 1
        selfclose = body[end - 2] == "/"
        if depth == 0 and not closing:
            start, kind = m.start(), name
            if selfclose:
                out.append(body[start:end])
            else:
                depth = 1
        elif depth and name == kind:
            if closing:
                depth -= 1
                if depth == 0:
                    out.append(body[start:end])
            elif not selfclose:
                depth += 1
        pos = end
    return out


def set_text(p, new, center=False):
    """Replace a paragraph's runs with one run of `new`, keeping its pPr and the first run's rPr."""
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
    ppr = ppr.group(0) if ppr else "<w:pPr></w:pPr>"
    if center and "<w:jc " not in ppr:
        ppr = re.sub(r"(<w:rPr>|</w:pPr>)", r'<w:jc w:val="center"/>\1', ppr, count=1)
    rpr = re.search(r"<w:r(?: [^>]*)?>\s*(<w:rPr>.*?</w:rPr>)", p, re.S)
    head = re.match(r"<w:p(?: [^>]*)?>", p).group(0)
    return (head + ppr + "<w:r>" + (rpr.group(1) if rpr else "")
            + f'<w:t xml:space="preserve">{esc(new)}</w:t></w:r></w:p>')


def set_row(row, values, rpr=""):
    """Fill the cells of a table row by position; None leaves a cell as it is."""
    parts = re.split(r"(<w:tc>.*?</w:tc>)", row, flags=re.S)
    k = 0
    for j, part in enumerate(parts):
        if part.startswith("<w:tc>"):
            if k < len(values) and values[k]:
                parts[j] = fill_cell(part, values[k], rpr)
            k += 1
    return "".join(parts)


def bold_header(tbl):
    """Bold the runs of a pandoc table's first row."""
    m = re.search(r"<w:tr(?: [^>]*)?>.*?</w:tr>", tbl, re.S)
    row = m.group(0)
    row = re.sub(r"<w:r>(?!<w:rPr>)", "<w:r><w:rPr><w:b/></w:rPr>", row)
    row = re.sub(r"<w:r><w:rPr>(?!<w:b/>)", "<w:r><w:rPr><w:b/>", row)
    return tbl[:m.start()] + row + tbl[m.end():]


def fill_cell(tc, value, rpr=""):
    """Put `value` into the first paragraph of a table cell."""
    run = f'<w:r>{rpr}<w:t xml:space="preserve">{esc(value)}</w:t></w:r>'
    tc = re.sub(r"<w:p( [^>]*?)? ?/>", lambda m: f"<w:p{m.group(1) or ''}></w:p>", tc, count=1)
    i = tc.index("</w:p>")
    p_start = tc.rfind("<w:p", 0, i)
    p = tc[p_start:i]
    p = re.sub(r"<w:r(?: [^>]*)?>.*?</w:r>", "", p, flags=re.S)  # drop any placeholder runs
    return tc[:p_start] + p + run + tc[i:]


def md_table(lines):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines if ln.strip().startswith("|")]
    return [r for r in rows[2:]]  # skip header and separator


def prepare_markdown(md):
    """Return (pandoc markdown with section markers, revision rows, schedule rows)."""
    body, refs = md.split("\n## References", 1)
    # Number -> key from the reference list.
    numkey = {}
    for n, entry in re.findall(r"^\[(\d+)\] (.*)$", refs, re.M):
        hits = [k for s, k in KEYS.items() if s in entry]
        if len(hits) != 1:
            sys.exit(f"no unique Zotero key for reference [{n}]: {entry[:60]}")
        numkey[n] = hits[0]

    def cite(m):
        nums = re.findall(r"\[(\d{1,2})\]", m.group(0))
        return "[" + "; ".join("@" + numkey[n] for n in nums) + "]"

    body = re.sub(r"\[\d{1,2}\](?:, \[\d{1,2}\])*", cite, body)
    body = body[body.index("## Progress Summary"):]

    lines, out, revisions, schedule = body.split("\n"), [], [], []
    section = None
    for ln in lines:
        if ln.rstrip() in SECTIONS:
            section = SECTIONS[ln.rstrip()]
            out += ["", f"ZZMARK:{section}", ""]
            continue
        if ln.strip() == "---":
            continue
        if ln.startswith("|") and section in ("revisions", "schedule"):
            (revisions if section == "revisions" else schedule).append(ln)
            continue
        if re.match(r"#{3,4} ", ln):
            ln = "### " + re.sub(r"^#{3,4} ", "", ln)  # keep the "3.4.3" number in the text
        # Drop the alt text (pandoc would turn it into a caption) and keep an
        # explicit {width=...}, defaulting to the full text width.
        ln = re.sub(
            r"^!\[[^\]]*\]\(([^)]+)\)(\{[^}]*\})?$",
            lambda m: f"![]({m[1]}){m[2] or '{width=6in}'}",
            ln,
        )
        out.append(ln)
    out += ["", "ZZMARK:end", ""]
    return "\n".join(out), md_table(revisions), md_table(schedule)


def zotero_running():
    try:
        with urllib.request.urlopen("http://127.0.0.1:23119/better-bibtex/cayw?probe=true", timeout=3) as r:
            return r.read().decode().strip() == "ready"
    except OSError:
        return False


def chunks_from(doc):
    inner = doc[doc.index("<w:body>") + len("<w:body>"):doc.rindex("</w:body>")]
    chunks, current = {}, None
    for el in top_level(inner):
        t = text_of(el)
        if t.startswith("ZZMARK:"):
            current = t[len("ZZMARK:"):]
            chunks[current] = []
        elif current and not el.startswith("<w:sectPr"):
            chunks[current].append(el)
    return chunks


def restyle(xml):
    # Pandoc's paragraph styles -> template styles.
    xml = re.sub(r'<w:pStyle w:val="(FirstParagraph|Compact)" ?/>', '<w:pStyle w:val="BodyText"/>', xml)
    xml = re.sub(r'<w:pStyle w:val="Heading[34]" ?/>', '<w:pStyle w:val="SubHeading"/>', xml)
    if '<w:tblStyle w:val="Table"' in xml:
        xml = bold_header(re.sub(r'<w:tblStyle w:val="Table" ?/>', '<w:tblStyle w:val="TableGrid"/>', xml))
    # Center the figure paragraphs and keep each one on the page of its caption.
    def figure(m):
        ppr = re.sub(r'(<w:pStyle [^>]*/>)?', lambda s: (s[0] or "") + "<w:keepNext/>", m[2], count=1)
        return f'{m[1]}<w:pPr>{ppr}<w:jc w:val="center"/></w:pPr>{m[3]}'
    xml = re.sub(r'(<w:p>|<w:p [^>]*>)<w:pPr>((?:(?!</w:pPr>).)*)</w:pPr>((?:(?!</w:p>).)*<w:drawing>)',
                 figure, xml, flags=re.S)
    return xml


# Column widths (twips) set by hand in OnlyOffice, keyed by the text of a table's first row.
COL_WIDTHS = {
    "Comments/Feedback from ReviewersUpdates": [1701, 7370],
    "PersonaRolePlaystyle": [1843, 1701, 5528],
    "Exp A (deep)Exp B (wide)": [1984, 3402, 3685],
    "ActivityScheduleRealizationOutput TargetRealization": [2006, 897, 720, 720, 720, 1980, 2028],
}


def set_widths(body):
    """Give the tables in COL_WIDTHS fixed column widths."""
    def one(m):
        tbl = m.group(0)
        head = re.search(r"<w:tr[ >].*?</w:tr>", tbl, re.S)
        widths = COL_WIDTHS.get(text_of(head.group(0)) if head else "")
        if not widths:
            return tbl
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", f"<w:tblGrid>{grid}</w:tblGrid>", tbl, count=1, flags=re.S)
        tbl = re.sub(r"<w:tblW [^>]*/>", '<w:tblW w:w="0" w:type="auto"/>', tbl, count=1)
        if "<w:tblLayout " not in tbl:
            tbl = tbl.replace("</w:tblPr>", '<w:tblLayout w:type="fixed"/></w:tblPr>', 1)

        def row(r):
            col = 0

            def cell(c):
                nonlocal col
                span = re.search(r'<w:gridSpan w:val="(\d+)"', c.group(0))
                n = int(span.group(1)) if span else 1
                w = sum(widths[col:col + n])
                col += n
                return re.sub(r"<w:tcW [^>]*/>", f'<w:tcW w:w="{w}" w:type="dxa"/>', c.group(0), count=1)
            return re.sub(r"<w:tc>.*?</w:tc>", cell, r.group(0), flags=re.S)
        return re.sub(r"<w:tr[ >].*?</w:tr>", row, tbl, flags=re.S)
    return re.sub(r"<w:tbl>.*?</w:tbl>", one, body, flags=re.S)


# Section id -> its number in the Markdown heading ("3.4"), put in front of the template heading text.
NUMBERS = {sid: m[1] for h, sid in SECTIONS.items() if (m := re.match(r"#+ (\d+(?:\.\d+)*)\.? ", h))}


def numbered(p, sid, title):
    """Set a template heading to `title` with the Markdown section number, replacing any list numbering."""
    p = re.sub(r"<w:numPr>.*?</w:numPr>", "", p, flags=re.S)
    n = NUMBERS.get(sid)
    return set_text(p, f"{n}{'.' if '.' not in n else ''} {title}" if n else title)


def build_body(template_doc, chunks, revisions, schedule):
    inner = template_doc[template_doc.index("<w:body>") + len("<w:body>"):template_doc.rindex("</w:body>")]
    els = top_level(inner)
    sect = els.pop()
    assert sect.startswith("<w:sectPr"), "template body must end with sectPr"

    out = []
    i = 0
    slots = {h: (sid, n) for h, sid, n in TEMPLATE_SLOTS}
    while i < len(els):
        el = els[i]
        t = text_of(el).strip()
        if el.startswith("<w:p") and t in COVER:
            out.append(set_text(el, COVER[t]))
            if t == "Research Title" and not text_of(els[i + 1]).strip():
                i += 1  # the longer title needs the room of one empty line
        elif el.startswith("<w:tbl") and "Approved by" in text_of(el):
            def sup(m):
                p = m.group(0)
                for key, name in SUPERVISORS.items():
                    if re.search(r"Supervisor \s*" + re.escape(key) + r"\s*.s\s+name", text_of(p)):
                        return set_text(p, name, center=True)
                return p
            out.append(re.sub(r"<w:p(?: [^>]*)?>.*?</w:p>", sup, el, flags=re.S))
        elif el.startswith("<w:tbl") and "Comments/Feedback from Reviewers" in text_of(el):
            rows = re.findall(r"<w:tr(?: [^>]*)?>.*?</w:tr>", el, re.S)
            header, blank = rows[0], rows[1]
            new_rows = []
            blank_clean = re.sub(r' w14:(paraId|textId)="[^"]*"', "", blank)  # copies must not share ids
            for comment, update in revisions:
                new_rows.append(set_row(blank_clean, [comment, update]))
            el = el.replace(blank, "".join(new_rows))
            out.append(el)
        elif el.startswith("<w:tbl") and "Reference tracing" in text_of(el):
            sched = {r[0]: r[1:] for r in schedule}
            for row in re.findall(r"<w:tr(?: [^>]*)?>.*?</w:tr>", el, re.S):
                cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
                name = text_of(cells[0]).strip()
                if name not in sched:
                    continue
                rpr = re.search(r"<w:r(?: [^>]*)?>\s*(<w:rPr>.*?</w:rPr>)", cells[0], re.S)
                new_row = set_row(row, [None] + sched.pop(name), rpr.group(1) if rpr else "")
                el = el.replace(row, new_row)
            if sched:
                sys.exit(f"schedule rows not in the template: {sorted(sched)}")
            out.append(el)
        elif el.startswith("<w:p") and t in TEMPLATE_DROPS:
            i += TEMPLATE_DROPS[t]
        elif el.startswith("<w:p") and t in slots:
            sid, n_guidance = slots.pop(t)
            for title, new_sid in TEMPLATE_INSERTS.get(t, []):
                copy = re.sub(r' w14:(paraId|textId)="[^"]*"', "", el)  # copies must not share ids
                out.append(numbered(copy, new_sid, title))
                out += chunks.get(new_sid, [])
            out.append(numbered(el, sid, TEMPLATE_RENAMES.get(t, t)))
            out += chunks.get(sid, [])
            i += n_guidance
        else:
            out.append(el)
        i += 1
    if slots:
        sys.exit(f"template headings not found: {sorted(slots)}")

    # References heading (template Heading1 look) and an empty paragraph for the Zotero bibliography.
    heading = next(e for e in out if e.startswith("<w:p") and text_of(e).strip().endswith("Background"))
    out.append(set_text(re.sub(r' w14:(paraId|textId)="[^"]*"', "", heading), "References"))
    out.append('<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr></w:p>')
    out.append(sect)
    return "".join(out)


def merged_root(template_doc, body_doc):
    """Template's <w:document> tag plus any namespace declarations pandoc's body needs."""
    t_root = re.search(r"<w:document[^>]*>", template_doc).group(0)
    b_root = re.search(r"<w:document[^>]*>", body_doc).group(0)
    have = dict(re.findall(r'xmlns:(\w+)="([^"]+)"', t_root))
    extra = "".join(f' xmlns:{p}="{u}"' for p, u in re.findall(r'xmlns:(\w+)="([^"]+)"', b_root) if p not in have)
    return t_root[:-1] + extra + ">"


def main():
    plain = "--plain" in sys.argv
    if not plain and not zotero_running():
        sys.exit("Zotero with Better BibTeX is not reachable on 127.0.0.1:23119. "
                 "Start Zotero (with all references imported), or use --plain for a layout check.")
    md, revisions, schedule = prepare_markdown(SRC.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        body_docx = Path(tmp) / "body.docx"
        cmd = ["pandoc", "-f", "markdown", "-o", str(body_docx), f"--reference-doc={TEMPLATE}",
               f"--resource-path={HERE}"]
        if not plain:
            cmd += [f"--lua-filter={LUA}", "-M", "zotero_csl-style=ieee"]
        subprocess.run(cmd, input=md, text=True, check=True, cwd=HERE)

        with zipfile.ZipFile(body_docx) as z:
            files = {n: z.read(n) for n in z.namelist()}
        with zipfile.ZipFile(TEMPLATE) as z:
            template_doc = z.read("word/document.xml").decode("utf-8-sig")
            template_numbering = z.read("word/numbering.xml").decode("utf-8-sig")

        body_doc = files["word/document.xml"].decode("utf-8")
        chunks = {}
        for k, v in chunks_from(body_doc).items():
            chunks[k] = []
            for e in v:
                chunks[k].append(restyle(e))
                if e.startswith("<w:tbl"):  # a little air between a table and the text under it
                    chunks[k].append('<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:p>')
        missing = set(SECTIONS.values()) - {"revisions"} - set(chunks)
        if missing:
            sys.exit(f"sections missing from the pandoc output: {sorted(missing)}")

        body = set_widths(build_body(template_doc, chunks, revisions, schedule))
        files["word/document.xml"] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                      + merged_root(template_doc, body_doc) + "<w:body>" + body
                                      + "</w:body></w:document>").encode("utf-8")

        # The template's numbered Heading 2 list must survive pandoc's numbering.xml.
        numbering = files["word/numbering.xml"].decode("utf-8")
        for num_id in re.findall(r'<w:numId w:val="(\d+)"', template_doc):
            if f'w:numId="{num_id}"' not in numbering:
                sys.exit(f"numbering {num_id} from the template is missing in pandoc's numbering.xml")
        del template_numbering

        styles = files["word/styles.xml"].decode("utf-8")
        if 'w:styleId="SubHeading"' not in styles:
            styles = styles.replace("</w:styles>", SUBHEADING_STYLE + "</w:styles>")
        files["word/styles.xml"] = styles.encode("utf-8")

        types = files["[Content_Types].xml"].decode("utf-8")
        for ext in sorted({n.rsplit(".", 1)[1].lower() for n in files if n.startswith("word/media/")}):
            if f'Extension="{ext}"' not in types:
                ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[ext]
                types = types.replace("<Types ", "<Types ", 1).replace(
                    "</Types>", f'<Default Extension="{ext}" ContentType="{ctype}"/></Types>')
        files["[Content_Types].xml"] = types.encode("utf-8")

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
    fields = body.count("ZOTERO_ITEM")
    print(f"wrote {OUT.relative_to(HERE.parent.parent)}" + ("" if plain else f" with {fields} Zotero citation field(s)"))


if __name__ == "__main__":
    main()
