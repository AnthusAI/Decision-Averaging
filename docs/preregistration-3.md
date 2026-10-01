# Preregistration 3: does pooling more copies make Jev's answer more repeatable?

**Status: Frozen.** Committed before any run of this study answered an item. Studies 1 and 2 are unchanged.
Scored against these predictions word for word.

## Why

Studies 1 and 2 found that pooling copies in one request leaves accuracy unchanged, and that it raises
test-retest agreement. With one pair of runs per arm, that second effect was clear only on OWA (answers changed
on 50 of 1,800 items at k = 1 and 25 at k = 10). On CWA, k = 3 looked more stable than k = 5, which suggests
noise. This study measures repeatability properly: more runs per arm, more values of k, the same items.

## Information used to write this

Study 1's two runs per arm (k = 1, 3, 5, 10) on both tasks, including their AC1 values, and study 2's results.
No answer from runs 3-7 on any item.

## Design (frozen)

- **Tasks:** ProofWriter OWA and CWA, the same 1,800 items per task as studies 1 and 2.
- **Engine:** Jev (`typesafe-sdk`), model version recorded per row.
- **Arms:** k = 1, 2, 3, 5, 10, 20 identical copies of the task's question in one request per item
  (`jev-k1` ... `jev-k20`). Every slot's answer is recorded.
- **Runs:** five fresh runs per arm and task, numbered 3-7. Studies 1-2's runs 1-2 are not used. Within each
  run, the twelve (k, task) cells go in the order `random.Random(run).shuffle` gives (`scripts/run_study3.sh`):
  - run 3: 2 OWA, 2 CWA, 10 CWA, 1 OWA, 1 CWA, 20 CWA, 10 OWA, 20 OWA, 3 OWA, 3 CWA, 5 CWA, 5 OWA
  - run 4: 20 CWA, 3 OWA, 3 CWA, 10 CWA, 20 OWA, 1 OWA, 5 CWA, 2 CWA, 1 CWA, 2 OWA, 10 OWA, 5 OWA
  - run 5: 10 CWA, 3 OWA, 20 CWA, 2 CWA, 2 OWA, 5 OWA, 1 CWA, 1 OWA, 3 CWA, 20 OWA, 10 OWA, 5 CWA
  - run 6: 1 CWA, 20 OWA, 3 OWA, 5 OWA, 3 CWA, 10 CWA, 20 CWA, 1 OWA, 10 OWA, 2 CWA, 2 OWA, 5 CWA
  - run 7: 2 CWA, 20 CWA, 5 OWA, 10 CWA, 3 CWA, 10 OWA, 5 CWA, 2 OWA, 1 OWA, 1 CWA, 3 OWA, 20 OWA

  Four requests at a time. Failed requests are retried by rerunning the same cell before moving on.
- **Pooling:** `mean` (highest mean probability across slots) is primary; `vote` is reported beside it.
- **Primary metric:** Gwet's multi-rater AC1 across the five runs, treating each run as a rater, for each k
  and task. 95% percentile bootstrap over items (seed 0, 1,000 resamples). Each arm is compared with `jev-k1`
  on the same bootstrap resamples, so the difference has a paired interval. Only items answered in every run of
  every arm are scored.
- **Secondary:** items whose pooled answer is not identical in all five runs; the share of run pairs that
  disagree; the standard deviation across runs of the pooled probability of each item's most common answer;
  accuracy (mean over runs); input tokens and p50 latency per request.
- **Spend:** about 161M input tokens, about $6.80 at $42 per billion (dry run: $7.12). 108,000 requests:
  6 arms × 5 runs × 1,800 items × 2 tasks.
- **If Jev refuses 20 questions in one request,** the `jev-k20` arm is dropped, the other arms still run, and
  the result says so.

## Predictions

1. On both tasks, `jev-k10`'s AC1 exceeds `jev-k1`'s, and the paired 95% interval excludes zero.
2. On both tasks, AC1 at k = 20 ≥ AC1 at k = 5 ≥ AC1 at k = 1.
3. Diminishing returns: on both tasks, the AC1 gain from k = 10 to k = 20 is smaller than the gain from k = 1
   to k = 3.
4. Pooling does not reach perfect repeatability: at k = 20, on both tasks, at least 10 items change across the
   five runs, and the pair flip rate is at least a third of k = 1's. (Copies in one request share part of their
   noise, so k copies count as fewer than k independent answers.)
5. Instability sits on close calls: on both tasks, more than half of the items whose `jev-k1` answer changes
   across the five runs have a top-two margin below 0.15 in `jev-k1`'s run 3 answer.
6. Accuracy (mean over runs) at every k is within 1 point of k = 1's on both tasks.
7. Input tokens grow linearly with k (about 175 per extra copy on OWA, 149 on CWA), and p50 latency at k = 20
   is less than twice k = 1's.

## What would count against us

If AC1 does not rise with k (predictions 1-2 false), extra copies do not buy repeatability, and the study 1
pattern on OWA was noise. If k = 20 reaches near-perfect agreement (prediction 4 false), copies in one request
behave like independent draws, and pooling can be pushed as far as cost allows.

## Caveats stated in advance

One engine, two synthetic tasks. All runs on one day, so the result describes run-to-run variation within a
day, not drift across model updates. Identical copies only; study 2 found varied copies no more useful for
accuracy, and they are not tested here.
