#!/usr/bin/env bash
# Build chapter-1.docx with live Zotero citations (IEEE).
# Needs: pandoc, Zotero running with Better BibTeX, references.bib imported.
# Afterwards open the .docx in OnlyOffice/Word, press Zotero > Refresh (IEEE),
# then insert the bibliography under 'References' (zotero.lua only adds it for .odt).
set -euo pipefail
cd "$(dirname "$0")"

command -v pandoc >/dev/null || { echo "pandoc not found (sudo pacman -S pandoc-cli)"; exit 1; }
if [ "$(curl -s -m 3 'http://127.0.0.1:23119/better-bibtex/cayw?probe=true' || true)" != "ready" ]; then
  echo "Zotero with Better BibTeX is not reachable on 127.0.0.1:23119. Start Zotero first."
  exit 1
fi

tmp=$(mktemp --suffix=.md)
trap 'rm -f "$tmp"' EXIT
# Replace the static-reference placeholder with a pandoc refs div,
# where zotero.lua inserts the live bibliography field.
python3 -I -c '
import sys
t = open(sys.argv[1], encoding="utf-8").read()
assert "{{REFERENCES}}" in t, "placeholder {{REFERENCES}} missing"
open(sys.argv[2], "w", encoding="utf-8").write(t.replace("{{REFERENCES}}", "::: {#refs}\n:::"))
' chapter-1.src.md "$tmp"

pandoc "$tmp" -f markdown -o chapter-1.docx \
  --lua-filter=zotero.lua -M zotero_csl-style=ieee

n=$(unzip -p chapter-1.docx word/document.xml | grep -o 'ZOTERO_ITEM' | wc -l)
echo "chapter-1.docx written: $n citation field(s)."
echo "Next: open it in OnlyOffice > Plugins > Zotero, choose IEEE, Refresh,"
echo "then put the cursor under 'References' and Insert Bibliography."
