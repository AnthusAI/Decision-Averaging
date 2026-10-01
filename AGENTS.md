# Agent instructions: Decision-Averaging

A benchmark of pooling repeated copies of one question in a single decision-model request. Same conventions as
Hard-Decisions, whose harness it imports.

- **Preregistered:** commit predictions (`docs/preregistration.md`) before any arm answers an item.
- **Replayable:** `da replay` must reproduce `studies/*.jsonl` byte for byte from `answers/`, offline.
- **Same protocol for every arm:** the only thing that changes between arms is k. No arm gets extra prompt work,
  reruns or selection.
- **Spend:** `da answer` is a dry run unless `--confirm --max-requests N` is given. Jev runs are authorized by
  the user; price them first and say what they cost.
- **Secrets:** keys come from the environment or a gitignored `.env`. Never read, print or `source` a `.env`.
- Conventional Commits; work on a branch.
