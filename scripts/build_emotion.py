"""Build the Emotion task: the full official test split of dair-ai/emotion (2,000 rows).

Writes ``tasks/emotion/items.jsonl`` (ids and labels, committed; enough for ``da replay``) and
``tasks/emotion/texts.jsonl`` (the tweet text, gitignored, as in the sibling projects; needed only to send
requests with ``da answer``).

Same rows and ids (``test-<index>``) as Few-Shot-Jev's Emotion test run and Decision-Flywheel-Evaluations'
Emotion scoreboard, so results line up item for item. Reads the pinned revision's Arrow file from a local
Hugging Face cache; pass its path, or let it default to the Flywheel project's cache.

    python scripts/build_emotion.py [path/to/emotion-test.arrow]

Without a path it reads the Decision-Flywheel-Evaluations cache if present, else downloads the pinned
revision with ``datasets`` (``pip install -e '.[emotion]'``).
"""
import json
import sys
from pathlib import Path

from datasets import Dataset

REVISION = "cab853a1dbdf4c42c2b3ef2173804746df8825fe"
LABELS = ("sadness", "joy", "love", "anger", "fear", "surprise")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT = (ROOT.parent / "Decision-Flywheel-Evaluations" / ".data" / "huggingface" / "dair-ai___emotion" / "split"
           / "0.0.0" / REVISION / "emotion-test.arrow")


def load_rows():
    if len(sys.argv) > 1 or DEFAULT.exists():
        return Dataset.from_file(str(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
    from datasets import load_dataset
    return load_dataset("dair-ai/emotion", revision=REVISION, split="test")


def main() -> None:
    rows = load_rows()
    folder = ROOT / "tasks" / "emotion"
    with open(folder / "items.jsonl", "w", encoding="utf-8") as items, \
            open(folder / "texts.jsonl", "w", encoding="utf-8") as texts:
        for index, row in enumerate(rows):
            item_id = f"test-{index}"
            items.write(json.dumps({"id": item_id, "metadata": {
                "split": "test", "source_index": index, "revision": REVISION,
                "reference_label": LABELS[int(row["label"])]}}, sort_keys=True) + "\n")
            texts.write(json.dumps({"id": item_id, "text": row["text"]}, sort_keys=True) + "\n")
    print(f"wrote {len(rows)} items to tasks/emotion/items.jsonl and their text to tasks/emotion/texts.jsonl")


if __name__ == "__main__":
    main()
