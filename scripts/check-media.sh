#!/bin/sh
# Event data rules: no footage, frames, screenshots, archives or derived data files in git.
# Our own diagrams are the only images allowed, under assets/diagrams/.
# Usage: <file list on stdin> | sh scripts/check-media.sh [<commit>]   (no commit = staged files)
rev="$1"
max=$((5 * 1024 * 1024))
fail=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  lower=$(printf '%s' "$f" | tr 'A-Z' 'a-z')
  case "$lower" in
    outputs/*|exports/*|data/egohack-data/*|eval/frames/*|gemini_cache/*)
      echo "blocked: $f (local-only folder)"; fail=1; continue ;;
    assets/diagrams/*.svg|assets/diagrams/*.png) ;;
    *.mp4|*.avi|*.mov|*.mkv|*.webm|*.m4v|*.3gp|*.mpg|*.mpeg|*.wmv|*.flv|\
    *.png|*.jpg|*.jpeg|*.webp|*.gif|*.bmp|*.tif|*.tiff|*.heic|*.pdf|\
    *.zip|*.tar|*.gz|*.7z|*.rar|*.parquet|*.npy|*.npz|*.pkl|*.db|*.sqlite)
      echo "blocked: $f (footage, frames, documents and data files never go in git)"; fail=1; continue ;;
  esac
  size=$(git cat-file -s "$rev:$f" 2>/dev/null || echo 0)
  if [ "$size" -gt "$max" ]; then
    echo "blocked: $f is $((size / 1024 / 1024)) MB (limit 5 MB)"; fail=1; continue
  fi
  case "$lower" in
    *.ipynb)
      if git cat-file -p "$rev:$f" | grep -q '"image/'; then
        echo "blocked: $f contains image outputs (clear all outputs first)"; fail=1
      fi ;;
  esac
done
exit $fail
