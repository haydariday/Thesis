"""Build conference.docx from the chapter sources on the IEEE A4 template (template/conference-template-a4.docx).

Usage (from any directory):
    python3 docs/conference/build_docx_paper.py           # live Zotero citations (Zotero + Better BibTeX running)
    python3 docs/conference/build_docx_paper.py --plain   # no Zotero: citations stay as [@key] text (layout check only)
    python3 docs/conference/build_docx_paper.py --single  # conference-single.docx: one column, ToC, no abstract

Layout: title and author in one column, then Abstract, Keywords and the chapters in the template's two columns.
With --single, the title and author are followed by a table of contents and a page break, then the chapters in
one column, without Abstract and Keywords. The ToC is prefilled with the headings but has no page numbers until it
is updated (Word asks on opening; in OnlyOffice use References > Refresh table).
Chapters become Heading 1 (I., II.) and sections Heading 2 (A., B.), as the template numbers them.
Figures and tables use the template's caption styles, which number them Fig. 1 and TABLE I across the paper,
so "Figure 3.1", "Table 3.2" and "Section 2.2" in the sources are rewritten to that numbering.
Figures span both columns: each sits in its own continuous one-column section, scaled to the text width.
After building, open the file in OnlyOffice > Plugins > Zotero, choose IEEE and Refresh. Then put the cursor in the
empty paragraph under "References" and insert the bibliography (zotero.lua only inserts it for .odt).
"""
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_paper import CHAPTERS, TITLE, chapter_markdown  # noqa: E402

TEMPLATE = HERE / "template/conference-template-a4.docx"
LUA = HERE / "sub/chapter 1/zotero.lua"
OUT = HERE / "conference.docx"
OUT_SINGLE = HERE / "conference-single.docx"

AUTHOR_LINES = [
    "Muhammad Haydar Maulana",
    "Master of Informatics",
    "[University]",
    "[City], Indonesia",
    "haydariday@gmail.com",
]
ABSTRACT = "[Abstract: to be written once the results are final.]"
KEYWORDS = "automated playtesting, game difficulty, large language models, multi-agent debate, playstyle personas, Wordle"

# Two-column body section of the template (its sectPr before the trailing guidance text).
BODY_SECT = ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="595.30pt" w:h="841.90pt" w:code="9"/>'
             '<w:pgMar w:top="54pt" w:right="45.35pt" w:bottom="72pt" w:left="45.35pt" w:header="36pt" '
             'w:footer="36pt" w:gutter="0pt"/><w:cols w:num="2" w:space="18pt"/><w:docGrid w:linePitch="360"/></w:sectPr>')
# Single-column title section, ended by the author paragraph.
TITLE_SECT = ('<w:sectPr><w:pgSz w:w="595.30pt" w:h="841.90pt" w:code="9"/>'
              '<w:pgMar w:top="54pt" w:right="44.65pt" w:bottom="72pt" w:left="44.65pt" w:header="36pt" '
              'w:footer="36pt" w:gutter="0pt"/><w:cols w:space="36pt"/><w:docGrid w:linePitch="360"/></w:sectPr>')

# Text width across both columns: 595.30pt - 2 x 45.35pt, in EMU (1pt = 12700 EMU).
TEXT_EMU = int((595.30 - 2 * 45.35) * 12700)
# One-column body section that holds a full-width figure and its caption.
FIGURE_SECT = BODY_SECT.replace('<w:cols w:num="2" w:space="18pt"/>', '<w:cols w:space="36pt"/>')
# Last section of the single-column layout (a normal section, not a continuous one).
# It carries a centered page number in the footer, left out on the title page.
SINGLE_SECT = (FIGURE_SECT.replace('<w:type w:val="continuous"/>', '<w:footerReference w:type="default" r:id="rIdPageFooter"/>')
               .replace("</w:sectPr>", "<w:titlePg/></w:sectPr>"))
PAGE_FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
               '<w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="center"/></w:pPr>'
               '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
               '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r>'
               '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
# ToC entry styles: indented per level, page number at the right margin after a dot leader.
TOC_STYLES = "".join(
    f'<w:style w:type="paragraph" w:styleId="TOC{n}"><w:name w:val="toc {n}"/><w:basedOn w:val="Normal"/>'
    '<w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>'
    f'<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="504pt"/></w:tabs>'
    f'<w:spacing w:before="{6 if n == 1 else 0}pt" w:after="2pt"/><w:ind w:start="{14.4 * (n - 1):.1f}pt"/>'
    '<w:jc w:val="start"/></w:pPr></w:style>' for n in (1, 2, 3))
# Empty paragraph that ends the two-column text before a figure.
END_COLUMNS = ('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
               f'{BODY_SECT}</w:pPr></w:p>')
# IEEE tables: rules above and below the table and under the header row.
# The elements follow the schema order of tblPr: jc and tblBorders after tblW, tblCellMar after tblLayout.
TABLE_BORDERS = ('<w:jc w:val="center"/>'
                 '<w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                 '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                 '<w:insideH w:val="single" w:sz="2" w:space="0" w:color="000000"/></w:tblBorders>')
TABLE_MARGINS = '<w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar>'


FOOTNOTE_STYLES = (
    '<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:spacing w:after="2pt"/><w:jc w:val="both"/></w:pPr><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>'
    '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/>'
    '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, props=""):
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(style, runs, extra_ppr=""):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra_ppr}</w:pPr>{runs}</w:p>'


def front_matter(single=False):
    title = para("papertitle", run(TITLE))
    author_runs = "<w:r><w:br/></w:r>".join(
        run(line, "" if i == 0 else "<w:i/>") for i, line in enumerate(AUTHOR_LINES))
    author = para("Author", author_runs, "" if single else TITLE_SECT)
    if single:
        return title + author
    abstract = para("Abstract", run("Abstract", "<w:i/><w:iCs/>") + run("—" + ABSTRACT))
    keywords = para("Keywords", run("Keywords—" + KEYWORDS))
    return title + author + abstract + keywords


def roman(n):
    out = ""
    for value, numeral in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out, n = out + numeral, n - value
    return out


def ieee_numbering(chapters):
    """Rewrite the chapter-style cross-references to the template's paper-wide numbering."""
    out, n_fig, n_tab = [], 0, 0
    for c, text in enumerate(chapters, start=1):
        figs, tabs = {}, {}
        for line in text.splitlines():
            if re.match(r"!\[.+\]\(", line):
                n_fig += 1
                figs[f"{c}.{len(figs) + 1}"] = n_fig
            elif line.startswith("Table: "):
                n_tab += 1
                tabs[f"{c}.{len(tabs) + 1}"] = n_tab
        # IEEE spells out "Figure" at the start of a sentence and abbreviates it elsewhere.
        text = re.sub(r"(^|\. )?\bFigure (\d+\.\d+)",
                      lambda m: f"{m.group(1) or ''}{'Figure' if m.group(1) is not None else 'Fig.'} {figs[m.group(2)]}",
                      text, flags=re.M)
        text = re.sub(r"\bTable (\d+\.\d+)", lambda m: f"Table {roman(tabs[m.group(1)])}", text)
        text = re.sub(r"\bSection (\d+)\.(\d+)\b",
                      lambda m: f"Section {roman(int(m.group(1)))}-{chr(64 + int(m.group(2)))}", text)
        out.append(text)
    return out


def style_tables(doc):
    """Template caption and cell styles, rules and left-aligned cells for every table."""
    def one(m):
        tbl = m.group(0).replace('<w:tblStyle w:val="Table" />', "")
        tbl = re.sub(r"(<w:tblW [^>]*/>)", r"\1" + TABLE_BORDERS, tbl, count=1)
        tbl = re.sub(r"(<w:tblLayout [^>]*/>)", r"\1" + TABLE_MARGINS, tbl, count=1)
        rows = re.findall(r"<w:tr>.*?</w:tr>", tbl, flags=re.S)
        for row in rows:
            style = "tablecolhead" if "<w:tblHeader" in row else "tablecopy"
            new = re.sub(r'<w:pStyle w:val="Compact" ?/>',
                         f'<w:pStyle w:val="{style}"/><w:jc w:val="start"/>', row)
            tbl = tbl.replace(row, new, 1)
        return tbl
    doc = re.sub(r"<w:tbl>.*?</w:tbl>", one, doc, flags=re.S)
    # Space between a table and the text below it.
    doc = re.sub(r'</w:tbl>(\s*<w:p>\s*<w:pPr>\s*<w:pStyle w:val="[^"]*" ?/>)', r'</w:tbl>\1<w:spacing w:before="8pt"/>', doc)
    doc = re.sub(r'<w:pStyle w:val="TableCaption" ?/>', '<w:pStyle w:val="tablehead"/>', doc)
    doc = re.sub(r'<w:pStyle w:val="ImageCaption" ?/>', '<w:pStyle w:val="figurecaption"/>', doc)
    # The template's Normal is centered, which suits the paragraph that holds a figure.
    return re.sub(r'<w:pStyle w:val="CaptionedFigure" ?/>', '<w:pStyle w:val="Normal"/>', doc)


def wide_figures(doc, sections=True):
    """Scale every figure to the text width. With sections, it sits with its caption in a one-column section."""
    def scale(drawing):
        ext = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', drawing)
        cx, cy = int(ext.group(1)), int(ext.group(2))
        new_cy = round(cy * TEXT_EMU / cx)
        return re.sub(rf'cx="{cx}"(\s*)cy="{cy}"', rf'cx="{TEXT_EMU}"\1cy="{new_cy}"', drawing)

    def one(m):
        figure = re.sub(r"<w:drawing>.*?</w:drawing>", lambda d: scale(d.group(0)), m.group(1), flags=re.S)
        if not sections:
            return figure + m.group(2)
        caption = m.group(2).replace('<w:pStyle w:val="figurecaption"/>',
                                     '<w:pStyle w:val="figurecaption"/>' + FIGURE_SECT, 1)
        return END_COLUMNS + figure + caption
    return re.sub(r'(<w:p><w:pPr><w:pStyle w:val="Normal"/>.*?<w:drawing>.*?</w:p>)\s*'
                  r'(<w:p><w:pPr><w:pStyle w:val="figurecaption"/>.*?</w:p>)', one, doc, flags=re.S)


def table_of_contents(doc):
    """A TOC field over Heading 1 to 3, prefilled with the headings and their template numbering."""
    entries, counts = [], [0, 0, 0]
    for m in re.finditer(r'<w:p><w:pPr><w:pStyle w:val="Heading([123])" ?/>.*?</w:p>', doc, flags=re.S):
        level = int(m.group(1))
        counts[level - 1] += 1
        counts[level:] = [0] * (3 - level)
        n = counts[level - 1]
        label = (f"{roman(n)}." if level == 1 else f"{chr(64 + n)}." if level == 2 else f"{n})")
        text = re.sub(r"<[^>]+>", "", m.group(0))
        if level == 1:
            text = text.upper()
        entries.append((level, f"{label} {text}"))
    begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
             '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
    end = '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    paras = [para(f"TOC{level}", (begin if i == 0 else "") + run(text) + (end if i == len(entries) - 1 else ""))
             for i, (level, text) in enumerate(entries)]
    page_break = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    return para("Heading5", run("Table of Contents")) + "".join(paras) + page_break


def zotero_running():
    try:
        with urllib.request.urlopen("http://127.0.0.1:23119/better-bibtex/cayw?probe=true", timeout=3) as r:
            return r.read().decode().strip() == "ready"
    except OSError:
        return False


def main():
    plain = "--plain" in sys.argv
    single = "--single" in sys.argv
    out = OUT_SINGLE if single else OUT
    if not plain and not zotero_running():
        sys.exit("Zotero with Better BibTeX is not reachable on 127.0.0.1:23119. "
                 "Start Zotero (with all references imported), or use --plain for a layout check.")
    md = "\n\n".join(ieee_numbering([chapter_markdown(p) for p in CHAPTERS]))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        body_docx = tmp / "body.docx"
        cmd = ["pandoc", "-f", "markdown", "-o", str(body_docx), f"--reference-doc={TEMPLATE}",
               f"--resource-path={HERE}"]
        if not plain:
            cmd += [f"--lua-filter={LUA}", "-M", "zotero_csl-style=ieee"]
        subprocess.run(cmd, input=md, text=True, check=True)

        with zipfile.ZipFile(body_docx) as z:
            files = {n: z.read(n) for n in z.namelist()}
        doc = files["word/document.xml"].decode("utf-8")

        doc = wide_figures(style_tables(doc), sections=not single)
        # Pandoc's own paragraph styles -> template styles.
        # The template's Normal is centered, so styles it lacks must not fall back to Normal.
        doc = re.sub(r'<w:pStyle w:val="(FirstParagraph|Compact)" ?/>', '<w:pStyle w:val="BodyText"/>', doc)
        # Pandoc's bookmarks around headings are not needed in the paper.
        doc = re.sub(r'<w:bookmark(Start|End) [^>]*/>', "", doc)

        start = doc.index("<w:body>") + len("<w:body>")
        # The document's own last section; the figures add earlier sectPr elements inside paragraphs.
        sect = re.compile(r"<w:sectPr.*?</w:sectPr>\s*</w:body>", re.S).search(doc, doc.rindex("<w:sectPr"))
        references = para("Heading5", run("References")) + para("BodyText", "")  # bibliography goes here
        front = front_matter(single) + (table_of_contents(doc) if single else "")
        doc = (doc[:start] + front + doc[start:sect.start()]
               + references + (SINGLE_SECT if single else BODY_SECT) + "</w:body>" + doc[sect.end():])
        files["word/document.xml"] = doc.encode("utf-8")

        # The template has no footnote styles, so pandoc's would fall back to the centered Normal style.
        styles = files["word/styles.xml"].decode("utf-8")
        if 'w:styleId="FootnoteText"' not in styles:
            styles = styles.replace("</w:styles>", FOOTNOTE_STYLES + "</w:styles>")
        if single and 'w:styleId="TOC1"' not in styles:
            styles = styles.replace("</w:styles>", TOC_STYLES + "</w:styles>")
        files["word/styles.xml"] = styles.encode("utf-8")
        if single:
            # Word offers to update the ToC page numbers when the file is opened.
            settings = files["word/settings.xml"].decode("utf-8")
            if "w:updateFields" not in settings:
                settings = re.sub(r"(<w:settings[^>]*>)", r'\1<w:updateFields w:val="true"/>', settings, count=1)
            files["word/settings.xml"] = settings.encode("utf-8")
            files["word/footer1.xml"] = PAGE_FOOTER.encode("utf-8")
            rels = files["word/_rels/document.xml.rels"].decode("utf-8")
            files["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", (
                '<Relationship Id="rIdPageFooter" Target="footer1.xml" Type='
                '"http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"/></Relationships>')).encode("utf-8")
            types = files["[Content_Types].xml"].decode("utf-8")
            files["[Content_Types].xml"] = types.replace("</Types>", (
                '<Override PartName="/word/footer1.xml" ContentType='
                '"application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')).encode("utf-8")

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
    fields = doc.count("ZOTERO_ITEM")
    print(f"wrote {out.relative_to(HERE.parent.parent)}" + ("" if plain else f" with {fields} Zotero citation field(s)"))


if __name__ == "__main__":
    main()
