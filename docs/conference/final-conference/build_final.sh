#!/usr/bin/env bash
# Build the IEEEtran conference paper into build/.
# Run from anywhere: docs/conference/final-conference/build_final.sh
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p build
# BibTeX rejects the leading % comment line of references.bib, so build a copy.
grep -v '^%' ../references.bib > build/references.bib
# IEEEtran.bst ignores eprint/archiveprefix, so turn them into notes in the build copy.
python3 - <<'EOF'
import re
path = 'build/references.bib'
text = open(path, encoding='utf-8').read()
text = re.sub(r"eprint\s*=\s*\{([^}]+)\},\s*\n\s*archiveprefix\s*=\s*\{arXiv\}",
              r"note = {arXiv:\1}", text)
open(path, 'w', encoding='utf-8').write(text)
EOF
cp IEEEtran.bst build/

pdflatex -interaction=nonstopmode -output-directory=build final-conference.tex > /dev/null
(cd build && bibtex final-conference > /dev/null)
pdflatex -interaction=nonstopmode -output-directory=build final-conference.tex > /dev/null
pdflatex -interaction=nonstopmode -output-directory=build final-conference.tex > /dev/null

cp build/final-conference.pdf final-conference.pdf
echo "wrote docs/conference/final-conference/final-conference.pdf"
