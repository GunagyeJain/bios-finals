#!/bin/sh
# Usage: check-commit.sh <sha>
# Fails if the author/committer email is not a team email, the message has a co-author trailer,
# or the commit adds footage, frames or data files (scripts/check-media.sh).
c="$1"
root=$(git rev-parse --show-toplevel)
allow="$root/.github/team-emails.txt"
fail=0
for email in $(git log -1 --format='%ae %ce' "$c" | tr 'A-Z' 'a-z'); do
  case "$email" in
    *@users.noreply.github.com|noreply@github.com) continue ;;
  esac
  if ! grep -v '^#' "$allow" | tr 'A-Z' 'a-z' | grep -qxF "$email"; then
    echo "commit $(git rev-parse --short "$c"): '$email' is not listed in .github/team-emails.txt"
    fail=1
  fi
done
if git log -1 --format=%B "$c" | grep -qiE '^co-authored-by:'; then
  echo "commit $(git rev-parse --short "$c"): has a Co-authored-by trailer (single-author commits only)"
  fail=1
fi
git diff-tree --no-commit-id --name-only -r --root --diff-filter=AM "$c" \
  | sh "$root/scripts/check-media.sh" "$c" || fail=1
exit $fail
