# Retrieval Evaluation

This folder contains a small gold set for BibleSphere retrieval quality. It is
designed to make emotion-to-verse retrieval measurable instead of relying only
on manual inspection.

## Run live retrieval

```bash
./.venv/bin/python evaluation/run_retrieval_eval.py \
  --cases evaluation/retrieval_cases.json \
  --top-k 10 \
  --output evaluation/reports/retrieval_eval_latest.json
```

Live retrieval requires `SILICONFLOW_API_KEY` and the local FAISS index files.

## Score saved results

```bash
./.venv/bin/python evaluation/run_retrieval_eval.py \
  --cases evaluation/retrieval_cases.json \
  --results-file evaluation/example_results.json \
  --output evaluation/reports/retrieval_eval_latest.json
```

Saved results should be a JSON object keyed by case id. Each value is the list
of retrieval result objects and should include a `verse` field such as
`马太福音 6:34`.

## Metrics

- `hit_rate_at_k`: expected verse appears anywhere in top-k.
- `mrr_at_k`: reciprocal rank of the first expected verse.
- `avoid_rate_at_k`: avoid-listed verse appears in top-k. Lower is better.
