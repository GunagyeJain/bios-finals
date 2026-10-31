#!/bin/sh
# One-time setup per clone. Run from the repo root: sh scripts/setup.sh
set -e
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true
echo "Hooks enabled."
echo "Commits will be authored as: $(git config user.name) <$(git config user.email)>"
email=$(git config user.email | tr 'A-Z' 'a-z')
if ! grep -v '^#' .github/team-emails.txt | tr 'A-Z' 'a-z' | grep -qxF "$email"; then
  echo "WARNING: $(git config user.email) is not in .github/team-emails.txt."
  echo "Add it there (or change git config user.email) before pushing."
fi
