# Decision-Averaging

Does asking a decision model the same question several times in one request, and pooling the answers, make it
more accurate or more stable?

Jev returns a probability for each option, and those probabilities move by about 0.05 to 0.15 between identical
copies of a question, even inside one request (see Hard-Decisions, 2026-10-01). Its answer flips when the top
two options are that close. Jev bills input tokens only, and each extra copy of a question adds about 175 of them
(the question's text, not the document). So pooling k copies is cheap, and this project measures whether it pays.

## Design

- **Items:** the same 1,800 OWA and 1,800 CWA ProofWriter items as Hard-Decisions (`tasks/SOURCE.md`).
- **Arms:** `jev-k1`, `jev-k3`, `jev-k5`, `jev-k10`: one request per item carrying k identical copies of the
  task's question. Every slot's full answer is recorded.
- **Pooling, offline:** `vote` (most slots; ties to the higher mean probability) and `mean` (highest mean
  probability). Both rules are scored from the same requests.
- **Two runs per arm**, for test-retest agreement (Gwet's AC1) and for comparing variation within one request
  against variation between requests.

Study 2 (`docs/preregistration-2.md`) asks whether copies in one request that are made to differ do better, on ProofWriter OWA
and on Emotion (`dair-ai/emotion` test split, 2,000 items):

- `jev-perm3`: one request, options in three rotations of the task's order.
- `jev-para3`: one request, three wordings from `tasks/<task>/variants.yaml`.

Prior work and what it predicts is in `docs/prior-art.md`.

## Run notes

- Run 1 began with a 20-item `jev-k10` OWA pilot, answered before the `jev-k1` arm and so out of the
  preregistered k = 1, 3, 5, 10 order. Those rows are kept; the rest of run 1 followed the order.
- Run 2 was stopped at 1,162 of 1,800 `jev-k10` OWA items and later resumed, so its manifest has more than one
  line.
- The Jev key is not read from this repo: the imported Hard-Decisions engine loads `../Hard-Decisions/.env`.

## Quickstart

```
make install                                        # installs ../Hard-Decisions too; the harness is shared
da answer 3 proofwriter-owa --run 1                 # dry run: prints the price, sends nothing
da answer 3 proofwriter-owa --run 1 --confirm --max-requests 1800
da answer jev-perm3 emotion --run 1                 # study 2 arms: jev-perm3, jev-para3
da replay && da report                              # rescore from the records, write RESULTS.md
```

## Layout

```
decision_averaging/   pooled engine and rules, analysis, report, CLI (reuses hard_decisions)
tasks/                the ProofWriter samples (copied from Hard-Decisions) and Emotion (scripts/build_emotion.py)
answers/<arm>/run<r>/<task>.jsonl.gz   committed records; <task>.runs.jsonl beside each is the run manifest
studies/<task>.jsonl  scored rows;  RESULTS.md is generated from them
docs/preregistration.md
```
