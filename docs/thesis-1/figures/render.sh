#!/usr/bin/env bash
# Render the Mermaid sources in this folder to PNG for the report.
# Needs Node (npx fetches mermaid-cli). If puppeteer finds no Chrome, point
# CHROME at one, e.g. from `npx @puppeteer/browsers install chrome-headless-shell@131`.
set -euo pipefail
cd "$(dirname "$0")"
args=()
if [[ -n "${CHROME:-}" ]]; then
  cfg=$(mktemp --suffix=.json)
  trap 'rm -f "$cfg"' EXIT
  printf '{"executablePath": "%s", "args": ["--no-sandbox"]}\n' "$CHROME" > "$cfg"
  args=(-p "$cfg")
fi
for src in fig-*.mmd; do
  npx -y @mermaid-js/mermaid-cli@11.4.2 "${args[@]}" -c mermaid-config.json -C mermaid.css \
    -i "$src" -o "${src%.mmd}.png" -s 3 -b white
done
