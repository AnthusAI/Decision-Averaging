# Preregistration: pooling repeated questions in one Jev request

Written before any arm has answered an item. Scored against these predictions word for word.

## Design (frozen)

- **Items:** the ProofWriter samples from Hard-Decisions commit `eb7cc28` (`tasks/SOURCE.md`): 1,800 OWA
  (true / false / unknown) and 1,800 CWA (true / false) items, depths 0 to 5.
- **Engine:** Jev (`typesafe-sdk`), model version recorded per row.
- **Arms:** k = 1, 3, 5, 10 identical copies of the task's question (same wording and option order as
  Hard-Decisions) in one request per item, named `Decision_0` ... `Decision_{k-1}`. Every slot's answer is
  recorded.
- **Runs:** two full runs per arm and task. Order: run 1 goes k = 1, 3, 5, 10; run 2 goes k = 10, 5, 3, 1, so
  time-of-day effects are not confounded with k. Four requests at a time; latency and token usage recorded per
  request.
- **Pooling rules (offline, from the same records):** `vote`, the option chosen by the most slots, with a tie
  going to the tied option with the higher mean probability, then option order; `mean`, the option with the
  highest mean probability across slots. For k = 1, the single slot's choice.
- **Primary metric:** accuracy of `jev-k5` under `vote` against `jev-k1`, paired on the same items within the
  same run, with a 95% percentile bootstrap interval (seed 0, 1,000 resamples), overall and by proof depth.
- **Secondary:** every other arm and rule the same way; test-retest percent agreement and Gwet's AC1 (run 1 vs
  run 2) per arm and rule; within-request slot disagreement against same-slot disagreement across runs; input
  tokens and latency per request.

## Predictions

1. Pooling raises accuracy only slightly: `jev-k5` `vote` beats `jev-k1` by less than 2 points overall on each
   task, and the paired interval may include zero.
2. Pooling raises test-retest agreement: AC1 for `jev-k5` and `jev-k10` exceeds AC1 for `jev-k1` on both tasks.
3. The gain, if any, is larger at depth 3 to 5 than at depth 0 to 2, where Jev's answers rarely change.
4. `vote` and `mean` differ by less than 1 point of accuracy for every arm.
5. Slots within one request disagree about as often as one slot disagrees with itself across runs (the two
   rates within a factor of 2), so in-request copies behave like independent draws.
6. Input tokens grow by about 175 per extra copy, and latency grows by less than 2x from k = 1 to k = 10.

## What would count against us

Pooling that lowers accuracy, or leaves agreement unchanged, is reported as such. If slots within a request are
identical, or far more alike than separate requests (prediction 5 false), pooling within a request cannot help
and the result says so.

## Caveats stated in advance

One engine, one dataset. ProofWriter is synthetic and templated. Results describe Jev's behaviour as served
during the runs, under the model version recorded per row.
