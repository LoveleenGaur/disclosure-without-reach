# Supplementary material: Disclosure Without Reach

Data and code for the study *Disclosure Without Reach: Synthetic-Content Marking
in the Documentation of Openly Distributed Image Generation Models*.

Corpus retrieved from the Hugging Face Hub on 9 September 2026.

## Contents

    code/coding_schema.py        the context-aware coding schema (final version)
    code/audit_notebook.ipynb    retrieval, coding, and analysis notebook
    code/refetch_corpus.py       re-retrieves card text from the manifest
    data/corpus_manifest_500.csv the 500 model identifiers with retrieval metadata
    data/coded_500.csv           coding results, one row per model
    data/validation_coder1.csv   first-pass validation judgments
    data/validation_coder2.csv   second-pass validation judgments (independent coder)

## Why card text is not included

Model cards are third-party documents published under varied licences. Rather
than redistribute their text, this package provides the exact model identifiers
with retrieval metadata, plus a script that re-retrieves current card text.
`data/coded_500.csv` contains the derived coding flags and short evidence spans,
which are sufficient to inspect and audit every coding decision.

Model cards are mutable, so a refetch will not reproduce the 9 September 2026
snapshot exactly. `refetch_corpus.py` reports how many cards have changed length
since retrieval.

## Reproducing the analysis

    pip install huggingface_hub pandas matplotlib scipy
    python code/refetch_corpus.py data/corpus_manifest_500.csv refetched_cards.jsonl

Then open `code/audit_notebook.ipynb` and run it, either against a fresh
retrieval or against `refetched_cards.jsonl`.

To re-derive the reported statistics from the archived coding results without
refetching anything, use `data/coded_500.csv` directly.

## Validation

Both validation files carry a `correct` column, coded 1 where the schema's
decision was judged correct and 0 where it was not. `validation_coder2.csv`
covers all 127 rows of the stratified sample drawn from the final corpus and is
the basis for the precision figures reported in the paper.

## Licence

Code: MIT. Data files in `data/`: CC BY 4.0.
