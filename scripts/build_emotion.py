"""Build tasks/emotion/items.jsonl: the full official test split of dair-ai/emotion (2,000 rows).

Same rows and ids (``test-<index>``) as Few-Shot-Jev's Emotion test run and Decision-Flywheel-Evaluations'
Emotion scoreboard, so results line up item for item. Reads the pinned revision's Arrow file from a local
Hugging Face cache; pass its path, or let it default to the Flywheel project's cache.

    python scripts/build_emotion.py [path/to/emotion-test.arrow]
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


def main() -> None:
    rows = Dataset.from_file(str(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
    out = ROOT / "tasks" / "emotion" / "items.jsonl"
    with open(out, "w", encoding="utf-8") as handle:
        for index, row in enumerate(rows):
            handle.write(json.dumps({"id": f"test-{index}", "text": row["text"],
                                     "metadata": {"split": "test", "source_index": index, "revision": REVISION,
                                                  "reference_label": LABELS[int(row["label"])]}},
                                    sort_keys=True) + "\n")
    print(f"wrote {len(rows)} items to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
