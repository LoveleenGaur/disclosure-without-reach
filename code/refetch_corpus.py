#!/usr/bin/env python3
"""Re-retrieve the model card corpus from the manifest.

The manifest lists the 500 model identifiers in the study sample with their
retrieval metadata. Card text itself is not redistributed here, because model
cards are third-party documents under varied licences. This script fetches the
current card text for every identifier so the coder can be rerun.

Card contents change over time, so a refetch will not reproduce the original
snapshot exactly. Cards whose text has changed since retrieval are reported.

    pip install huggingface_hub pandas
    python refetch_corpus.py corpus_manifest_500.csv refetched_cards.jsonl
"""
import sys
import time
import pandas as pd
from huggingface_hub import ModelCard


def main(manifest_path, out_path):
    man = pd.read_csv(manifest_path)
    rows, changed, missing = [], 0, 0
    for i, r in man.iterrows():
        if i % 50 == 0:
            print(f"  {i}/{len(man)}")
        try:
            text = ModelCard.load(r["model_id"]).text
        except Exception:
            text = None
            missing += 1
        if text is not None and abs(len(text) - int(r["card_chars"])) > 50:
            changed += 1
        rows.append({
            "model_id": r["model_id"],
            "org": r["org"],
            "downloads": r["downloads"],
            "tags": r["tags"],
            "card_text": text,
            "card_chars_at_retrieval": int(r["card_chars"]),
        })
        time.sleep(0.1)
    pd.DataFrame(rows).to_json(out_path, orient="records", lines=True)
    print(f"wrote {out_path}")
    print(f"no longer retrievable: {missing} of {len(man)}")
    print(f"card length changed by more than 50 characters: {changed}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
