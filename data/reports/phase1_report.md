# Phase 1 — Baseline Report

## Source Summary

- **API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Filter**: `from-pub-date:2025-12-12,has-abstract:true`
- **Records fetched**: 24
- **Records after cleaning**: 23

## Evaluation Metrics

| Metric | Value |
|--------|-------|
| samples | 24 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |
| ragas | _Set RUN_RAGAS=1 to enable the slower Ragas pass._ |

## Data Quality

**Overall**: ✅ All Passed (5/5)

| Check | Passed | Detail |
|-------|--------|--------|
| row_count | ✅ | 23 rows in dataset. |
| paper_id_integrity | ✅ | Null IDs: 0, Duplicate IDs: 0. |
| title_not_null | ✅ | Null/empty titles: 0. |
| summary_length | ✅ | Mean summary length: 1807 chars. Short summaries (<10 chars): 0. |
| freshness | ✅ | Fresh rows: 23/23 (100.0%). Threshold: 180 days. |

## Freshness

| Field | Value |
|-------|-------|
| Latest Published | 2026-06-02 |
| Oldest Published | 2025-12-19 |
| Stale Rows | 0/23 |
| Threshold | 180 days |
| Status | 🟢 Fresh |
