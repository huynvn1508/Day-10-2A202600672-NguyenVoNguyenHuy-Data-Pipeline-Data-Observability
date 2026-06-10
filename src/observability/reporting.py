from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt_metric(value: Any) -> str:
    """Format a metric value for display in markdown."""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _quality_table(quality: dict[str, Any]) -> str:
    """Render quality checks as a markdown table."""
    lines = [
        "| Check | Passed | Detail |",
        "|-------|--------|--------|",
    ]
    checks = quality.get("checks", {})
    for name, info in checks.items():
        passed = "✅" if info["passed"] else "❌"
        detail = info.get("detail", "")
        lines.append(f"| {name} | {passed} | {detail} |")
    return "\n".join(lines)


def _freshness_section(freshness: dict[str, Any]) -> str:
    """Render freshness report as a markdown section."""
    status = "🟢 Fresh" if freshness.get("is_fresh") else "🔴 Stale"
    return (
        f"| Latest Published | {freshness.get('latest_published', 'N/A')} |\n"
        f"| Oldest Published | {freshness.get('oldest_published', 'N/A')} |\n"
        f"| Stale Rows | {freshness.get('stale_rows', '?')}/{freshness.get('total_rows', '?')} |\n"
        f"| Threshold | {freshness.get('freshness_threshold_days', '?')} days |\n"
        f"| Status | {status} |"
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate a markdown report for the baseline phase.

    Sections:
    1. Source Summary (API, query, record count)
    2. Evaluation Metrics (retrieval_hit_rate, mean_token_f1, etc.)
    3. Data Quality (check results table)
    4. Freshness Report
    """
    md_parts: list[str] = []

    # --- Header ---
    md_parts.append("# Phase 1 — Baseline Report\n")

    # --- Source Summary ---
    md_parts.append("## Source Summary\n")
    md_parts.append(f"- **API**: {source_summary.get('api', 'Crossref REST API')}")
    md_parts.append(f"- **Query**: `{source_summary.get('query', 'N/A')}`")
    md_parts.append(f"- **Filter**: `{source_summary.get('filter', 'N/A')}`")
    md_parts.append(f"- **Records fetched**: {source_summary.get('raw_count', '?')}")
    md_parts.append(f"- **Records after cleaning**: {source_summary.get('clean_count', '?')}")
    md_parts.append("")

    # --- Evaluation Metrics ---
    md_parts.append("## Evaluation Metrics\n")
    md_parts.append("| Metric | Value |")
    md_parts.append("|--------|-------|")
    for key in ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        if key in metrics:
            md_parts.append(f"| {key} | {_fmt_metric(metrics[key])} |")
    ragas = metrics.get("ragas", {})
    if ragas and not ragas.get("skipped"):
        for rk, rv in ragas.items():
            if rk != "error":
                md_parts.append(f"| ragas_{rk} | {_fmt_metric(rv)} |")
    elif ragas.get("skipped"):
        md_parts.append(f"| ragas | _{ragas['skipped']}_ |")
    md_parts.append("")

    # --- Data Quality ---
    md_parts.append("## Data Quality\n")
    overall = "✅ All Passed" if quality.get("all_passed") else "⚠️ Some Failed"
    md_parts.append(f"**Overall**: {overall} ({quality.get('passed_checks', '?')}/{quality.get('total_checks', '?')})\n")
    md_parts.append(_quality_table(quality))
    md_parts.append("")

    # --- Freshness ---
    md_parts.append("## Freshness\n")
    md_parts.append("| Field | Value |")
    md_parts.append("|-------|-------|")
    md_parts.append(_freshness_section(freshness))
    md_parts.append("")

    report_text = "\n".join(md_parts)
    write_text(report_path, report_text)
    print(f"[report] Phase 1 report → {report_path}")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate a markdown comparison report for baseline vs corrupted vs repaired."""
    md_parts: list[str] = []

    # --- Header ---
    md_parts.append("# Corruption Comparison Report\n")

    # --- Metrics Comparison ---
    md_parts.append("## Metrics Comparison\n")
    md_parts.append("| Metric | Baseline | Corrupted | Repaired | Δ Corrupted | Δ Repaired |")
    md_parts.append("|--------|----------|-----------|----------|-------------|------------|")
    metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    for key in metric_keys:
        bv = baseline_metrics.get(key, 0)
        cv = corrupted_metrics.get(key, 0)
        rv = repaired_metrics.get(key, 0)
        if isinstance(bv, (int, float)) and isinstance(cv, (int, float)) and isinstance(rv, (int, float)):
            delta_c = cv - bv
            delta_r = rv - bv
            dc_symbol = "📉" if delta_c < -0.01 else ("📈" if delta_c > 0.01 else "➡️")
            dr_symbol = "📈" if delta_r > -0.01 and delta_r >= delta_c else "📉" if delta_r < -0.01 else "➡️"
            md_parts.append(
                f"| {key} | {_fmt_metric(bv)} | {_fmt_metric(cv)} | {_fmt_metric(rv)} "
                f"| {dc_symbol} {delta_c:+.4f} | {dr_symbol} {delta_r:+.4f} |"
            )
        else:
            md_parts.append(f"| {key} | {_fmt_metric(bv)} | {_fmt_metric(cv)} | {_fmt_metric(rv)} | — | — |")
    md_parts.append("")

    # --- Data Quality Comparison ---
    md_parts.append("## Data Quality Comparison\n")
    md_parts.append("### Corrupted Data Quality\n")
    md_parts.append(_quality_table(corrupted_quality))
    md_parts.append("")
    md_parts.append("### Repaired Data Quality\n")
    md_parts.append(_quality_table(repaired_quality))
    md_parts.append("")

    # --- Freshness Comparison ---
    md_parts.append("## Freshness Comparison\n")
    md_parts.append("### Corrupted Freshness\n")
    md_parts.append("| Field | Value |")
    md_parts.append("|-------|-------|")
    md_parts.append(_freshness_section(corrupted_freshness))
    md_parts.append("")
    md_parts.append("### Repaired Freshness\n")
    md_parts.append("| Field | Value |")
    md_parts.append("|-------|-------|")
    md_parts.append(_freshness_section(repaired_freshness))
    md_parts.append("")

    # --- Analysis ---
    md_parts.append("## Analysis\n")

    bhr = baseline_metrics.get("retrieval_hit_rate", 0)
    chr_ = corrupted_metrics.get("retrieval_hit_rate", 0)
    rhr = repaired_metrics.get("retrieval_hit_rate", 0)

    if isinstance(bhr, (int, float)) and isinstance(chr_, (int, float)):
        if chr_ < bhr:
            md_parts.append(
                f"- **Corruption impact**: Retrieval hit rate dropped from {bhr:.4f} to {chr_:.4f} "
                f"({(chr_ - bhr):.4f}), demonstrating that data corruption degrades agent performance."
            )
        else:
            md_parts.append("- **Corruption impact**: Retrieval hit rate was not significantly affected.")

    if isinstance(rhr, (int, float)) and isinstance(bhr, (int, float)):
        if rhr >= bhr - 0.05:
            md_parts.append(
                f"- **Repair effectiveness**: After repair, retrieval hit rate recovered to {rhr:.4f} "
                f"(baseline: {bhr:.4f}), confirming that proper data repair restores performance."
            )
        else:
            md_parts.append(
                f"- **Repair effectiveness**: Retrieval hit rate after repair ({rhr:.4f}) did not fully "
                f"recover to baseline ({bhr:.4f}). Some data quality issues may persist."
            )

    cq_passed = corrupted_quality.get("all_passed", True)
    rq_passed = repaired_quality.get("all_passed", True)
    if not cq_passed and rq_passed:
        md_parts.append("- **Quality checks**: Corrupted data failed quality checks; repaired data passed all checks.")
    elif not cq_passed and not rq_passed:
        md_parts.append("- **Quality checks**: Both corrupted and repaired data had quality check failures.")

    md_parts.append("")

    report_text = "\n".join(md_parts)
    write_text(report_path, report_text)
    print(f"[report] Corruption comparison report → {report_path}")
