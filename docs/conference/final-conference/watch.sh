#!/usr/bin/env bash
# Rebuild the paper whenever a source changes, for a live preview.
#
#   ./watch.sh                      # build once, then poll every second
#   zathura final-conference.pdf    # in another terminal; it reloads on change
#
# Figures are standalone documents. When a figures/fig-*.tex is newer than its
# PDF, the figure is recompiled and its 300 dpi PNG regenerated before the
# paper is built, so the paper and the thesis chapter pick up the change.
#
# No inotify tool is assumed: the script compares modification times, so it
# works anywhere bash and stat exist. ctrl-c stops it.
set -uo pipefail
cd "$(dirname "$0")"

sources=(final-conference.tex ../references.bib figures/*.tex)

newest_mtime() {
  stat -c %Y "${sources[@]}" 2>/dev/null | sort -n | tail -n 1
}

build_figures() {
  local tex base
  for tex in figures/fig-*.tex; do
    base=${tex%.tex}
    if [ "$tex" -nt "$base.pdf" ]; then
      printf '%s  figure %s\n' "$(date +%H:%M:%S)" "$(basename "$base")"
      (
        cd figures || exit 1
        pdflatex -interaction=nonstopmode "$(basename "$tex")" >/dev/null 2>&1 &&
          pdftoppm -r 300 -png -singlefile "$(basename "$base").pdf" "$(basename "$base")-tikz"
      ) || printf '%s  figure build failed\n' "$(date +%H:%M:%S)"
    fi
  done
}

build_all() {
  build_figures
  ./build_final.sh
}

last=$(newest_mtime)
build_all

echo
echo "watching ${sources[*]}"
echo "open the PDF in a viewer that reloads, for example:"
echo "  zathura $(pwd)/final-conference.pdf"
echo "ctrl-c to stop."
echo

while true; do
  sleep 1
  now=$(newest_mtime)
  if [ "$now" != "$last" ]; then
    last=$now
    printf '%s  change detected, rebuilding\n' "$(date +%H:%M:%S)"
    build_figures
    if ./build_final.sh >/dev/null 2>&1; then
      printf '%s  ok\n' "$(date +%H:%M:%S)"
    else
      printf '%s  build failed, see build/final-conference.log\n' "$(date +%H:%M:%S)"
    fi
    last=$(newest_mtime)
  fi
done
