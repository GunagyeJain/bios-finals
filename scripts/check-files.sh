#!/bin/sh
# What may enter git (event data-use agreement: footage leaks = disqualification). Allowlist:
#  - text files with a known code/doc extension, max 1 MB, no secrets
#  - images only as our own diagrams in assets/diagrams/ (.svg, .png); .html/.js only for the app UI in app/
#  - notebooks only with every output cleared
# Everything else is blocked: video, frames, PDFs, archives, CSV/JSONL of clips, weights, binaries.
# Usage: <file list on stdin> | sh scripts/check-files.sh [<commit>]   (no commit = staged files)
rev="$1"
max=$((1024 * 1024))
fail=0
block() { echo "blocked: $1 ($2)"; fail=1; }
while IFS= read -r f; do
  [ -z "$f" ] && continue
  lower=$(printf '%s' "$f" | tr 'A-Z' 'a-z')
  base=${lower##*/}
  case "$lower" in
    outputs/*|exports/*|data/egohack-data/*|eval/frames/*|gemini_cache/*|models/*.*)
      case "$lower" in models/readme.md) ;; *) block "$f" "local-only folder"; continue ;; esac ;;
  esac
  case "$lower" in
    assets/diagrams/*.svg|assets/diagrams/*.png) kind=diagram ;;
    .githooks/*|*/.gitkeep|.gitkeep) kind=text ;;
    *.md|*.py|*.txt|*.sh|*.toml|*.yml|*.yaml|*.json|*.cfg|*.ini|*.css|*.example) kind=text ;;
    .gitignore|.gitattributes|.editorconfig|license|makefile) kind=text ;;
    app/*.html|app/*.js) kind=text ;;
    *.ipynb) kind=notebook ;;
    *) block "$f" "file type not allowed; footage, frames, PDFs, archives, CSV/JSONL, weights stay out of git"; continue ;;
  esac
  [ "$base" = ".env" ] && { block "$f" "secrets file"; continue; }
  size=$(git cat-file -s "$rev:$f" 2>/dev/null || echo 0)
  if [ "$size" -gt "$max" ]; then
    block "$f" "$((size / 1024)) KB, limit 1 MB"; continue
  fi
  [ "$kind" = diagram ] || [ "$size" -eq 0 ] && continue
  if ! git cat-file -p "$rev:$f" | grep -qI .; then
    block "$f" "binary content"; continue
  fi
  if [ "$kind" = notebook ] && git cat-file -p "$rev:$f" | grep -q '"output_type"'; then
    block "$f" "notebook has outputs; clear all outputs first"; continue
  fi
  if git cat-file -p "$rev:$f" | grep -qE 'AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[0-9A-Za-z]{36}|hf_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_-]{32,}'; then
    block "$f" "looks like an API key or private key; use environment variables"
  fi
done
exit $fail
