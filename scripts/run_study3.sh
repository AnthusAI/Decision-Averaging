#!/usr/bin/env bash
# Study 3 (docs/preregistration-3.md): k = 1, 2, 3, 5, 10, 20 identical copies, runs 3-7, ProofWriter OWA and CWA.
# Within each run the twelve (k, task) cells go in the order random.Random(run).shuffle gives (printed below).
# Dry run (prices only) unless --confirm is given. Resumable: a rerun only answers what is missing.
set -euo pipefail
cd "$(dirname "$0")/.."
for run in 3 4 5 6 7; do
  cells=$(python3 -c "
import random
cells = [(k, t) for t in ('proofwriter-owa', 'proofwriter-cwa') for k in (1, 2, 3, 5, 10, 20)]
random.Random($run).shuffle(cells)
print(' '.join(f'{k}:{t}' for k, t in cells))")
  for cell in $cells; do
    k=${cell%%:*}; task=${cell#*:}
    if [[ "${1:-}" == "--confirm" ]]; then
      # Retry a cell's failed items by rerunning it (it skips answered ids) before moving on.
      for attempt in 1 2 3; do
        da answer "$k" "$task" --run "$run" --confirm --max-requests 1800 && break
        [[ $attempt == 3 ]] && exit 1
        sleep 10
      done
    else
      da answer "$k" "$task" --run "$run" | sed -n 1,2p
    fi
  done
done
