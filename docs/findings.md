# Findings: pooling several classifications in one Jev request

Draft, 2026-10-01. Numbers come from `RESULTS.md` and `studies/*.jsonl`, which `da replay && da report` regenerate
offline from `answers/`. Model `jev-1.13.0` throughout.

## Answer

No. Asking Jev for three, five or ten classifications of the same item in one request, and pooling them by vote
or by averaging probabilities, did not change accuracy on any task. Every pooled arm landed within 1 point of a
single classification (largest gain +0.8 points; largest loss −0.7). This held for identical copies, for copies
with the options in different orders, and for copies with different wording.

Pooling does make answers more repeatable. With ten copies, the pooled answer changed between two runs on 28 of
1,800 OWA items, against 52 for a single copy.

## Why it cannot work here

Pooling corrects mistakes only when copies make different mistakes. Jev's mistakes are almost all made by every
copy:

| task | k = 1 accuracy | items wrong | items where copies disagree | ceiling: any copy right |
|---|---|---|---|---|
| ProofWriter OWA | 84.2% | 15.8% | 2.8% (k = 3) to 5.6% (paraphrased) | 85.4–86.8% |
| ProofWriter CWA | 90.1% | 9.9% | 1.8% (k = 3) to 3.3% (k = 10) | 90.7–91.4% |
| Emotion (6 labels) | 59.2% | 40.8% | 1.9% (k = 3) to 4.7% (paraphrased) | 59.7–60.6% |

Even a pooling rule that always picked a right copy when one existed would gain at most 2.6 points (OWA,
paraphrased) and on Emotion 1.4. Real rules fall well short of that ceiling, because on items where copies
disagree, the majority is wrong about as often as it is right.

This is what ensemble theory predicts: averaging removes variance, not bias (Krogh & Vedelsby 1995; Breiman
1996). The closest human result is the same: a person re-asked the same question gains 0.3 points (Herzog &
Hertwig 2009). See `docs/prior-art.md`.

## Varying the copies

Varying the copies does create more disagreement. On Emotion, rotated options and paraphrases split 2.3–2.5
times as many items as identical copies; on OWA, paraphrases split twice as many. But the extra disagreement
landed on items Jev was already unsure of, and it moved accuracy by less than a point either way:

| task | arm | mean-rule accuracy vs k = 1 | 95% interval |
|---|---|---|---|
| OWA | `jev-perm3` (rotated options) | +0.4 | −0.2 to +1.1 |
| OWA | `jev-para3` (paraphrased) | +0.8 | +0.0 to +1.6 |
| Emotion | `jev-perm3` | −0.1 | −0.5 to +0.4 |
| Emotion | `jev-para3` | −0.3 | −0.9 to +0.3 |

The OWA paraphrase result is the only interval that touches a gain. It is one of 16 paired comparisons on
ProofWriter, its lower bound is zero, and the same arm loses 0.3 points on Emotion. We do not read it as an effect.

## Cost

Jev bills input tokens only. Each extra copy adds the question's tokens but not the document's: on OWA, 561
tokens for one copy, 911 for three, 2,136 for ten (175 per extra copy). Latency did not grow (p50 170–185 ms at
every k). Everything in this project, both studies and both runs, cost about $2 of Jev.

## Predictions, scored

### Study 1 (`docs/preregistration.md`, identical copies)

1. **True.** `jev-k5` `vote` against `jev-k1`: OWA −0.3 (run 1) and +0.2 (run 2); CWA −0.4 and −0.1. All under
   2 points; every interval includes zero.
2. **True, weakly.** AC1 for `jev-k5` and `jev-k10` exceeds `jev-k1` on both tasks (OWA 0.957 → 0.973 and 0.977;
   CWA 0.959 → 0.964 and 0.972, `vote`). The intervals overlap.
3. **False.** There was no gain to be larger at depth 3–5. `jev-k5` `vote` minus `jev-k1`: OWA −0.2 and 0.0 at
   depth 3–5 against −0.3 and +0.4 at 0–2; CWA −0.9 and −0.1 against +0.1 and −0.1.
4. **True.** `vote` and `mean` differ by at most 0.3 points in every study 1 arm and run.
5. **True.** Two slots in one request disagree on 1.1–1.9% of items; one slot against itself in a separate
   request, 1.8–2.6%. Within a factor of 2 (1.3–1.7 times) in every arm. Copies in one request vary about as much
   as separate requests, a little less.
6. **True.** Input tokens grow by exactly 175 per extra copy on OWA; p50 latency at k = 10 is within 10 ms of k = 1 (178 vs 175, 179 vs 170).

### Study 2 (`docs/preregistration-2.md`, varied copies, one request)

1. **Partly false.** Split-answer share against `jev-k3`: Emotion `jev-perm3` 2.26 times and `jev-para3` 2.45
   times (true); OWA `jev-para3` 2.00 times (true, at the boundary: 100 items against 50); OWA `jev-perm3` 1.58
   times (false).
2. **True.** On OWA, `mean` against `jev-k1`: `jev-perm3` +0.4, `jev-para3` +0.8.
3. **True.** On Emotion, `jev-perm3` −0.1 and `jev-para3` −0.3.
4. *Withdrawn* with the `jev-sep3` arm before any data.
5. **True.** Of the items whose `mean`-pooled answer differs from `jev-k1`, the share with a `jev-k1` top-two
   margin below 0.15: OWA 59% (`jev-perm3`) and 59% (`jev-para3`); Emotion 89% and 67%.
6. **True.** Brier against `jev-k1`: OWA 0.227 and 0.220 vs 0.227; Emotion 0.666 and 0.669 vs 0.667.
7. **True.** Emotion `jev-k1` 59.2% against Few-Shot-Jev's 59.35%.

## Deviations from the preregistrations

- Study 1 run 1 began with a 20-item `jev-k10` OWA pilot sent before `jev-k1`.
- Study 1 run 2 was stopped at 1,162 `jev-k10` OWA items, then resumed later in the preregistered order.
- Study 2's `jev-sep3` arm (three requests per item) was withdrawn before any arm answered; it measured a
  different method.

## Limits

One engine and one model version. ProofWriter is synthetic and templated; Emotion's labels are noisy (distant
supervision from hashtags), which caps any method. Three fixed variants per arm, not a search, so better
paraphrases or orders are not ruled out, though the ceilings above bound what any of them could gain. Results
describe Jev as served on 2026-10-01.

## Compared with Decision-Flywheel

On Emotion's validation split, Few-Shot-Jev reported +9.9 macro-F1 points from 384 labelled examples in context
and +12.7 from per-target retrieval (`Decision-Flywheel-Evaluations/studies/PRIOR_EXPERIMENTS.md`). On the
2,000 test items here, pooled classifications gained nothing (macro-F1 0.500–0.502 against 0.502). The splits
differ, so this is a contrast in kind, not a paired comparison.
Pooling is cheap but cannot supply information Jev lacks; adding examples to the context can.
