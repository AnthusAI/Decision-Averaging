# Preregistration 2 (DRAFT, not frozen): pooling varied questions

**Status: draft for review.** It freezes when a commit changes this line to "Frozen", and that commit must come
before any arm below answers an item. Study 1 (`docs/preregistration.md`) is unchanged.

## Why a second study

Study 1 run 1 found that identical copies in one request almost always agree (copies differ on 2–4% of items,
while 10–16% of answers are wrong), so pooling them leaves accuracy within about ±0.6 points of k = 1. Prior
art (`docs/prior-art.md`) says gains need members that make different mistakes. This study gives Jev three
ways to disagree with itself and asks whether any of them buys accuracy, at matched cost.

## Design

- **Tasks:** ProofWriter OWA (the same 1,800 items) and Emotion (`dair-ai/emotion`, six labels).
  *Open:* which 2,000 Emotion items. Preferred: the Decision-Flywheel-Evaluations Emotion scoreboard items, so
  the result lines up with Flywheel's context search.
- **Baselines (reused from study 1 on ProofWriter; new on Emotion):** `jev-k1` and `jev-k3` (identical copies).
- **Arms, all with three answers pooled per item:**
  - `jev-sep3`: three separate requests, one question each.
  - `jev-perm3`: one request, three copies with the options in three fixed rotations (the task's order and its two
    cyclic shifts; for six labels, shifts 0, 2, 4).
  - `jev-para3`: one request, three paraphrases of the question, written and committed in
    `tasks/<task>/variants.yaml` with this file, never chosen by looking at test answers.
- **Pooling:** `vote` and `mean`, offline, as in study 1. Probabilities from permuted copies are mapped back to
  option names before pooling.
- **One run per arm.** Arms run in a randomized order fixed by seed 0, recorded in the manifest.
- **Primary metric:** accuracy (Emotion: macro-F1 too) of each arm under `mean` against `jev-k1`, paired on the
  same items, 95% percentile bootstrap (seed 0, 1,000 resamples).
- **Secondary:** share of items where the three answers disagree; accuracy ceiling if any member is right;
  results split by `jev-k1` top-two margin (below / above 0.15); Brier score and ECE (15 bins) of the pooled
  probabilities; input tokens per item.
- **Spend:** about 1,500 input tokens or fewer per item per arm; under $2 for everything at $42 per billion
  input tokens. Each `da answer` call is capped with `--max-requests`.

## Predictions (to be edited before freezing)

1. Each varied arm disagrees with itself on at least twice as many items as `jev-k3`.
2. On ProofWriter, no varied arm beats `jev-k1` by 2 points or more.
3. On Emotion, at least one varied arm beats `jev-k1` on macro-F1, and the interval excludes zero.
4. `jev-sep3` behaves like `jev-k3`: accuracy within 1 point, disagreement rate within a factor of 2.
5. Gains, where present, come from items with a `jev-k1` margin below 0.15; above it, pooling changes almost
   nothing.
6. `mean` has a lower Brier score than `vote` for every arm.

## What would count against us

If varied copies disagree no more than identical ones, pooling cannot help Jev on these tasks, and the
write-up says so. If they disagree more and accuracy still does not move, the extra disagreement is noise
rather than independent evidence.
