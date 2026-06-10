from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build and run the corruption → evaluate → repair → compare flow.

    Steps:
    1. Load settings and baseline artifacts.
    2. Create corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index and evaluate.
    5. Run quality checks/freshness on corrupted data.
    6. Repair from raw records.
    7. Evaluate repaired dataset.
    8. Generate comparison report.
    """
    print("=" * 60)
    print("  Phase 2 — Corruption Flow")
    print("=" * 60)

    # 1. Load settings and baseline
    settings = load_settings()
    paths = settings.paths

    if not paths.baseline_metrics.exists():
        raise RuntimeError("Baseline metrics not found. Run Phase 1 first (script/run_phase1.py).")

    baseline_metrics = read_json(paths.baseline_metrics)
    print(f"[corruption] Baseline metrics loaded: hit_rate={baseline_metrics.get('retrieval_hit_rate', '?')}")

    if not paths.clean_csv.exists():
        raise RuntimeError("Clean CSV not found. Run Phase 1 first.")

    df_clean = pd.read_csv(paths.clean_csv)
    # Ensure text columns have no NaN
    for col in ["title", "summary", "authors_joined", "categories_joined", "text_for_embedding"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna("").astype(str)
    print(f"[corruption] Loaded baseline clean dataset: {len(df_clean)} rows.")

    # 2. Create corrupted dataframe
    print("[corruption] Applying corruption...")
    df_corrupted = corrupt_clean_dataframe(df_clean, paths.corruption_log)
    print(f"[corruption] Corrupted dataset: {len(df_corrupted)} rows.")

    # 3. Save corrupted artifacts
    write_csv(df_corrupted, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    print(f"[corruption] Saved → {paths.corrupted_clean_csv}")

    # 4. Rebuild index and evaluate on corrupted data
    print("[corruption] Building corrupted embedding index...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted, settings, embeddings_output_path=paths.corrupted_embeddings_json
    )

    print("[corruption] Evaluating corrupted pipeline...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"[corruption] Corrupted metrics: hit_rate={corrupted_metrics.get('retrieval_hit_rate', '?'):.4f}")

    # 5. Run quality checks/freshness on corrupted data
    print("[corruption] Quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, paths.quality_dir / "corrupted_freshness.json"
    )

    # 6. Repair from raw records
    print("[corruption] Repairing from raw records...")
    if not paths.raw_records_json.exists():
        raise RuntimeError("Raw records not found. Cannot repair without source data.")
    raw_records = load_raw_records(paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, now_utc())
    write_csv(df_repaired, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    print(f"[corruption] Repaired dataset: {len(df_repaired)} rows.")

    # 7. Rebuild index and evaluate repaired data
    print("[corruption] Building repaired embedding index...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired, settings, embeddings_output_path=paths.repaired_embeddings_json
    )

    print("[corruption] Evaluating repaired pipeline...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"[corruption] Repaired metrics: hit_rate={repaired_metrics.get('retrieval_hit_rate', '?'):.4f}")

    # 8. Run quality/freshness on repaired data
    print("[corruption] Quality checks on repaired data...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, paths.quality_dir / "repaired_freshness.json"
    )

    # 9. Generate comparison report
    print("[corruption] Generating comparison report...")
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # Done
    print("=" * 60)
    print("  Phase 2 Complete!")
    print(f"  Comparison Report: {paths.comparison_report}")
    print("=" * 60)
