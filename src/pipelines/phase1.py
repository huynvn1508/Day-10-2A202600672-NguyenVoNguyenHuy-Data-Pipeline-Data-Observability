from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build and run the baseline pipeline end-to-end.

    Steps:
    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Build or load evaluation set.
    7. Evaluate.
    8. Run quality checks and freshness report.
    9. Generate markdown report.
    10. (Optional) Demo agent on sample questions.
    """
    print("=" * 60)
    print("  Phase 1 — Baseline Pipeline")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()
    print(f"[phase1] Settings loaded. Provider={settings.llm_provider}, Model={settings.model_name}")

    # 2. Load or fetch raw records
    if settings.refresh_source or not paths.raw_records_json.exists():
        print("[phase1] Fetching fresh data from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"[phase1] Loading cached raw records from {paths.raw_records_json}")
        records = load_raw_records(paths.raw_records_json)
    raw_count = len(records)
    print(f"[phase1] Raw records: {raw_count}")

    # 3. Clean data
    print("[phase1] Cleaning data...")
    df = build_clean_dataframe(records, run_date)
    clean_count = len(df)
    print(f"[phase1] Cleaned records: {clean_count}")

    # 4. Save clean CSV/JSON
    write_csv(df, paths.clean_csv)
    clean_records = df.to_dict(orient="records")
    write_json(paths.clean_json, clean_records)
    print(f"[phase1] Saved → {paths.clean_csv}, {paths.clean_json}")

    # 5. Build Chroma index
    print("[phase1] Building embedding index...")
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)
    print(f"[phase1] Index built: {len(index.documents)} documents.")

    # 6. Build or load evaluation set
    if settings.refresh_test_set or not paths.eval_testset.exists():
        print("[phase1] Building evaluation test set...")
        test_set = build_test_set(df, paths.eval_testset)
    else:
        print(f"[phase1] Loading cached test set from {paths.eval_testset}")
        test_set = read_json(paths.eval_testset)
    print(f"[phase1] Test set: {len(test_set)} questions.")

    # 7. Evaluate
    print("[phase1] Evaluating pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"[phase1] Metrics: hit_rate={metrics.get('retrieval_hit_rate', '?'):.4f}, "
          f"f1={metrics.get('mean_token_f1', '?'):.4f}, "
          f"judge_acc={metrics.get('judge_accuracy', '?'):.4f}")

    # 8. Run quality checks and freshness report
    print("[phase1] Running data quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")

    print("[phase1] Building freshness report...")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    # 9. Generate markdown report
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_count": raw_count,
        "clean_count": clean_count,
    }
    print("[phase1] Generating baseline report...")
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)

    # Done
    print("=" * 60)
    print("  Phase 1 Complete!")
    print(f"  Report: {paths.baseline_report}")
    print(f"  Metrics: {paths.baseline_metrics}")
    print("=" * 60)
