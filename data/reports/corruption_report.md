# Corruption Comparison Report

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corrupted | Δ Repaired |
|--------|----------|-----------|----------|-------------|------------|
| retrieval_hit_rate | 1.0000 | 0.6250 | 1.0000 | 📉 -0.3750 | 📈 +0.0000 |
| mean_token_f1 | 1.0000 | 0.5905 | 1.0000 | 📉 -0.4095 | 📈 +0.0000 |
| judge_accuracy | 1.0000 | 0.5833 | 1.0000 | 📉 -0.4167 | 📈 +0.0000 |
| mean_judge_score | 5 | 3.3333 | 5 | 📉 -1.6667 | 📈 +0.0000 |

## Data Quality Comparison

### Corrupted Data Quality

| Check | Passed | Detail |
|-------|--------|--------|
| row_count | ✅ | 22 rows in dataset. |
| paper_id_integrity | ❌ | Null IDs: 0, Duplicate IDs: 2. |
| title_not_null | ✅ | Null/empty titles: 0. |
| summary_length | ✅ | Mean summary length: 1451 chars. Short summaries (<10 chars): 4. |
| freshness | ✅ | Fresh rows: 18/22 (81.8%). Threshold: 180 days. |

### Repaired Data Quality

| Check | Passed | Detail |
|-------|--------|--------|
| row_count | ✅ | 23 rows in dataset. |
| paper_id_integrity | ✅ | Null IDs: 0, Duplicate IDs: 0. |
| title_not_null | ✅ | Null/empty titles: 0. |
| summary_length | ✅ | Mean summary length: 1807 chars. Short summaries (<10 chars): 0. |
| freshness | ✅ | Fresh rows: 23/23 (100.0%). Threshold: 180 days. |

## Freshness Comparison

### Corrupted Freshness

| Field | Value |
|-------|-------|
| Latest Published | 2026-05-06 |
| Oldest Published | 2020-12-31 |
| Stale Rows | 4/22 |
| Threshold | 180 days |
| Status | 🟢 Fresh |

### Repaired Freshness

| Field | Value |
|-------|-------|
| Latest Published | 2026-06-02 |
| Oldest Published | 2025-12-19 |
| Stale Rows | 0/23 |
| Threshold | 180 days |
| Status | 🟢 Fresh |

## Analysis

- **Corruption impact**: Retrieval hit rate dropped from 1.0000 to 0.6250 (-0.3750), demonstrating that data corruption degrades agent performance.
- **Repair effectiveness**: After repair, retrieval hit rate recovered to 1.0000 (baseline: 1.0000), confirming that proper data repair restores performance.
- **Quality checks**: Corrupted data failed quality checks; repaired data passed all checks.
