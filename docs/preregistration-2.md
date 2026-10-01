# Preregistration 2: pooling varied questions

**Status: Frozen.** Committed before any arm below answered an item. Study 1 (`docs/preregistration.md`) is
unchanged. Scored against these predictions word for word.

## Why a second study

Study 1 run 1 found that identical copies in one request almost always agree. Copies differ on 2–4% of items
while 10–16% of answers are wrong, and pooling leaves accuracy within about ±0.6 points of k = 1. Even always
picking a right slot when one exists would reach only 85.3–85.9% on OWA (k = 1: 84.2%). Prior art
(`docs/prior-art.md`) says gains need members that make different mistakes. This study gives Jev three ways to
disagree with itself and asks whether any of them buys accuracy.

## Information used to write this, stated in advance

- Study 1 run 1 on both ProofWriter tasks (all four arms), and the first 1,162 items of its run 2.
- Few-Shot-Jev's zero-shot answers on the same 2,000 Emotion items, with a different question wording
  (`Jev-AGNews-Fewshot/results/emotion_responses.jsonl`): 59.35% accuracy, macro-F1 0.500. In those answers 6.2%
  of items have a top-two margin below 0.15, and 67% of errors have a margin of 0.5 or more.
- No answer from any arm below, on any item.

## Design (frozen)

- **Tasks:**
  - ProofWriter OWA: the same 1,800 items as study 1.
  - Emotion: the full official test split of `dair-ai/emotion` at revision
    `cab853a1dbdf4c42c2b3ef2173804746df8825fe`, 2,000 items with ids `test-<index>` (`tasks/emotion/SOURCE.md`).
    These are the same rows Few-Shot-Jev and Decision-Flywheel-Evaluations scored. Six options in the dataset's
    order: sadness, joy, love, anger, fear, surprise. Question in `tasks/emotion/question.yaml`.
- **Engine:** Jev (`typesafe-sdk`), model version recorded per row.
- **Baselines:** on ProofWriter, study 1's `jev-k1` and `jev-k3` run 1. On Emotion, new `jev-k1` and `jev-k3`
  (identical copies).
- **Arms, three answers pooled per item:**
  - `jev-sep3`: three separate requests, one identical question each, sent concurrently.
  - `jev-perm3`: one request, three copies with the options in cyclic rotations of the task's order (OWA shifts
    0, 1, 2; Emotion shifts 0, 2, 4). Each option keeps its own description.
  - `jev-para3`: one request, the three wordings in `tasks/<task>/variants.yaml`. Wording 0 is the task's own
    question; options and descriptions are unchanged. The wordings were written once and have not been tried.
- **Pooling:** `vote` and `mean`, offline, as in study 1.
- **One run per arm**, recorded as run 1. Order fixed by `random.Random(0).shuffle` over the eight cells:
  emotion `jev-k3`, OWA `jev-perm3`, emotion `jev-sep3`, OWA `jev-para3`, OWA `jev-sep3`, emotion `jev-k1`,
  emotion `jev-para3`, emotion `jev-perm3`. Four requests at a time.
- **Primary metric:** accuracy of each varied arm under `mean` against `jev-k1`, paired on the same items, with a
  95% percentile bootstrap interval (seed 0, 1,000 resamples). On Emotion, macro-F1 is reported beside it.
- **Secondary:**
  - Share of items whose three answers are not all the same.
  - Share of items where at least one of the three answers is right (the ceiling for any pooling rule).
  - Brier score and ECE (15 bins) of the `mean`-pooled probabilities.
  - Input tokens per item.
  - The same results split by `jev-k1` top-two margin (below 0.15, 0.15 or above), computed offline.
- **Spend:** about $0.72 for all eight cells at $42 per billion input tokens (dry-run estimate; Emotion estimates
  are conservative). Every `da answer` call is capped with `--max-requests`.

## Predictions

1. Each varied arm has a higher share of items with split answers than `jev-k3` on the same task, by at least a
   factor of 2 for `jev-perm3` and `jev-para3`.
2. On ProofWriter OWA, no varied arm changes accuracy against `jev-k1` by 2 points or more in either direction
   under `mean`.
3. On Emotion, no varied arm raises accuracy against `jev-k1` by 2 points or more under `mean`. Most errors are
   confident, so pooling can reach few of them.
4. `jev-sep3` behaves like `jev-k3`: accuracy within 1 point, and split-answer share within a factor of 2.
5. Wherever an arm changes accuracy, most of the changed items (more than half) have a `jev-k1` top-two margin
   below 0.15.
6. Under `mean`, every varied arm's Brier score is no worse than `jev-k1`'s by more than 0.01.
7. On Emotion, `jev-k1` with this study's wording lands within 5 points of Few-Shot-Jev's 59.35%.

## What would count against us

If varied copies disagree no more than identical ones (prediction 1 false), pooling cannot help Jev on these
tasks, and the write-up says so. If they disagree more and accuracy still does not move, the extra disagreement
is noise rather than independent evidence. If a varied arm gains 2 points or more, predictions 2 or 3 were wrong
and that is the headline.

## Caveats stated in advance

One engine. Three variants per arm, not a search over variants, so a null result does not rule out better
variants. Emotion labels are noisy (distant supervision from hashtags), which caps measured accuracy. Paraphrases
can change the question's meaning; the ProofWriter wordings keep every rule of the original.
