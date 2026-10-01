# Decision-Averaging

Does asking a decision model for several classifications of the same item in one request, and pooling them,
make it more accurate or more stable?

Jev (TypeSafe's System One decision model) returns a probability for each option, and one request can carry
several questions about one document. Jev bills input tokens only, and each extra copy of a question adds about
175 of them (the question's text, not the document's). So pooling k classifications in one request is cheap.
This project measures whether it pays.

## Result

**No, for accuracy. Yes, a little, for repeatability.** Two preregistered studies, about 40,000 requests, under
$2 of Jev. Write-up with every prediction scored: [`docs/findings.md`](docs/findings.md).

| task | one classification | 3 identical | 3 option orders | 3 wordings |
|---|---|---|---|---|
| ProofWriter OWA (1,800) | 84.2% | 84.5% | 84.6% | 84.9% |
| ProofWriter CWA (1,800) | 90.1% | 89.5% | | |
| Emotion (2,000) | 59.2% | 59.0% | 59.1% | 58.9% |

Run 1, `mean` rule (average the probabilities, take the top option). No pooled arm differs from one
classification by more than 1 point on any task or run, with up to ten copies. Jev's mistakes are made by every
copy: copies disagree on 1.8–5.6% of items while 10–41% of answers are wrong, so even a rule that always picked
a right copy would gain at most 2.6 points. Pooling ten copies did halve how often the answer changes between
two runs (OWA: 28 items of 1,800 against 52).

## Design

- **Study 1** ([`docs/preregistration.md`](docs/preregistration.md)): ProofWriter OWA and CWA, the same 1,800
  items per task as the Hard-Decisions benchmark (`tasks/SOURCE.md`). Arms `jev-k1`, `jev-k3`, `jev-k5`,
  `jev-k10`: one request per item carrying k identical copies of the question. Two runs per arm.
- **Study 2** ([`docs/preregistration-2.md`](docs/preregistration-2.md)): copies made to differ, still one
  request per item, on ProofWriter OWA and Emotion (`dair-ai/emotion` test split, 2,000 items).
  `jev-perm3` rotates the option order; `jev-para3` uses three wordings from `tasks/<task>/variants.yaml`.
- **Pooling, offline:** `vote` (most slots; ties to the higher mean probability) and `mean` (highest mean
  probability), both scored from the same requests. Every slot's full answer is recorded.
- **Prior work** and what it predicts: [`docs/prior-art.md`](docs/prior-art.md).

## Reproduce

```
make install              # pip install -e '.[dev,jev]'
da replay && da report    # rescore every committed record offline (no key needed), regenerate RESULTS.md
make test
```

`da replay` reproduces `studies/*.jsonl` and `RESULTS.md` byte for byte from `answers/`.

To send new requests you need a TypeSafe key in the environment (`TYPESAFE_API_KEY`) or a gitignored `.env`.
`da answer` is a dry run that prints the price unless `--confirm --max-requests N` is given:

```
da answer 3 proofwriter-owa --run 1                        # price only
da answer 3 proofwriter-owa --run 1 --confirm --max-requests 1800
scripts/run_study2.sh                                       # study 2 arms in the preregistered order (price only)
```

Emotion's tweet text is not in this repository (as in the sibling projects); `tasks/emotion/items.jsonl` holds
ids and labels, which is all replay needs. `python scripts/build_emotion.py` (needs `pip install -e '.[emotion]'`)
writes the text to a gitignored `tasks/emotion/texts.jsonl` before answering.

## Run notes

- Study 1 run 1 began with a 20-item `jev-k10` OWA pilot, answered before the `jev-k1` arm and so out of the
  preregistered order. Those rows are kept; the rest of run 1 followed the order.
- Study 1 run 2 was stopped at 1,162 of 1,800 `jev-k10` OWA items and resumed later, so that manifest has more
  than one line.
- Study 2 withdrew a three-separate-requests arm before any arm answered (see its amendment).
- Before publishing, history was rewritten to remove Emotion text from earlier commits. Run manifests that name
  commit `bd2b213` refer to what is now `112aa87` (same code); `0139dd1` is unchanged. Preregistration 2 was
  frozen in `8b769b8`, before any of its arms answered.

## Layout

```
decision_averaging/          pooled engine and arms, analysis, report, CLI (`da`)
decision_averaging/harness/  task loading, answer runner, records, metrics, AC1: vendored from Hard-Decisions
tasks/                       ProofWriter samples and Emotion ids and labels
answers/<arm>/run<r>/<task>.jsonl.gz   committed records; <task>.runs.jsonl beside each is the run manifest
studies/<task>.jsonl         scored rows; RESULTS.md is generated from them
docs/                        preregistrations, prior art, findings
```

Model `jev-1.13.0`, recorded per row. Results describe Jev as served on 2026-10-01.
