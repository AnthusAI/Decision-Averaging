#!/usr/bin/env bash
# Study 2 arms in the order fixed by docs/preregistration-2.md. Dry run (prices only) unless --confirm is given.
set -euo pipefail
cd "$(dirname "$0")/.."
cells=(
  "jev-k3 emotion"
  "jev-perm3 proofwriter-owa"
  "jev-para3 proofwriter-owa"
  "jev-k1 emotion"
  "jev-para3 emotion"
  "jev-perm3 emotion"
)
for cell in "${cells[@]}"; do
  read -r arm task <<< "$cell"
  if [[ "${1:-}" == "--confirm" ]]; then
    da answer "$arm" "$task" --run 1 --confirm --max-requests 2000
  else
    da answer "$arm" "$task" --run 1 | sed -n 1,2p
  fi
done
