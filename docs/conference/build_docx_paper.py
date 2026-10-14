"""Build conference.docx from the chapter sources on the IEEE A4 template (template/conference-template-a4.docx).

Usage (from any directory):
    python3 docs/conference/build_docx_paper.py           # live Zotero citations (Zotero + Better BibTeX running)
    python3 docs/conference/build_docx_paper.py --plain   # no Zotero: citations stay as [@key] text (layout check only)

Layout: title and author in one column, then Abstract, Keywords and the chapters in the template's two columns.
Chapters become Heading 1 (I., II.) and sections Heading 2 (A., B.), as the template numbers them.
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


def front_matter():
    title = para("papertitle", run(TITLE))
    author_runs = "<w:r><w:br/></w:r>".join(
        run(line, "" if i == 0 else "<w:i/>") for i, line in enumerate(AUTHOR_LINES))
    author = para("Author", author_runs, TITLE_SECT)
    abstract = para("Abstract", run("Abstract", "<w:i/><w:iCs/>") + run("—" + ABSTRACT))
    keywords = para("Keywords", run("Keywords—" + KEYWORDS))
    return title + author + abstract + keywords


def zotero_running():
    try:
        with urllib.request.urlopen("http://127.0.0.1:23119/better-bibtex/cayw?probe=true", timeout=3) as r:
            return r.read().decode().strip() == "ready"
    except OSError:
        return False


def main():
    plain = "--plain" in sys.argv
    if not plain and not zotero_running():
        sys.exit("Zotero with Better BibTeX is not reachable on 127.0.0.1:23119. "
                 "Start Zotero (with all references imported), or use --plain for a layout check.")
    md = "\n\n".join(chapter_markdown(p) for p in CHAPTERS)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        body_docx = tmp / "body.docx"
        cmd = ["pandoc", "-f", "markdown", "-o", str(body_docx), f"--reference-doc={TEMPLATE}"]
        if not plain:
            cmd += [f"--lua-filter={LUA}", "-M", "zotero_csl-style=ieee"]
        subprocess.run(cmd, input=md, text=True, check=True)

        with zipfile.ZipFile(body_docx) as z:
            files = {n: z.read(n) for n in z.namelist()}
        doc = files["word/document.xml"].decode("utf-8")

        # Pandoc's own paragraph styles -> template styles.
        # The template's Normal is centered, so styles it lacks must not fall back to Normal.
        doc = re.sub(r'<w:pStyle w:val="(FirstParagraph|Compact)" ?/>', '<w:pStyle w:val="BodyText"/>', doc)
        # Pandoc's bookmarks around headings are not needed in the paper.
        doc = re.sub(r'<w:bookmark(Start|End) [^>]*/>', "", doc)

        start = doc.index("<w:body>") + len("<w:body>")
        sect = re.search(r"<w:sectPr.*?</w:sectPr>\s*</w:body>", doc, flags=re.S)
        references = para("Heading5", run("References")) + para("BodyText", "")  # bibliography goes here
        doc = (doc[:start] + front_matter() + doc[start:sect.start()]
               + references + BODY_SECT + "</w:body>" + doc[sect.end():])
        files["word/document.xml"] = doc.encode("utf-8")

        # The template has no footnote styles, so pandoc's would fall back to the centered Normal style.
        styles = files["word/styles.xml"].decode("utf-8")
        if 'w:styleId="FootnoteText"' not in styles:
            styles = styles.replace("</w:styles>", FOOTNOTE_STYLES + "</w:styles>")
        files["word/styles.xml"] = styles.encode("utf-8")

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
    fields = doc.count("ZOTERO_ITEM")
    print(f"wrote {OUT.relative_to(HERE.parent.parent)}" + ("" if plain else f" with {fields} Zotero citation field(s)"))


if __name__ == "__main__":
    main()
