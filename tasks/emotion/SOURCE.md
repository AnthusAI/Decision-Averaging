The full official test split of `dair-ai/emotion` at revision `cab853a1dbdf4c42c2b3ef2173804746df8825fe`, 2,000 rows,
ids `test-<index>`, built by `scripts/build_emotion.py`. These are the same rows as Few-Shot-Jev's Emotion test run
(`Jev-AGNews-Fewshot/results/emotion_responses.jsonl`, zero-shot accuracy 59.35%) and the Emotion scoreboard of
Decision-Flywheel-Evaluations (`studies/manifests/emotion.json`). Labels come from the dataset and are known to be
noisy (distant supervision from hashtags), which caps any method's measured accuracy.
