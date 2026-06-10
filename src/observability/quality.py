from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run a suite of data quality checks on the cleaned dataframe.

    Checks:
    1. Row count >= 1.
    2. paper_id not null and unique.
    3. title not null.
    4. summary length (mean summary_chars >= 50).
    5. Freshness — fraction of rows with age_days <= threshold.
    """
    checks: dict[str, Any] = {}

    # Check 1: Row count
    row_count = len(df)
    checks["row_count"] = {
        "passed": row_count >= 1,
        "detail": f"{row_count} rows in dataset.",
    }

    # Check 2: paper_id not null and unique
    null_ids = int(df["paper_id"].isna().sum())
    duplicate_ids = int(df["paper_id"].duplicated().sum())
    checks["paper_id_integrity"] = {
        "passed": null_ids == 0 and duplicate_ids == 0,
        "detail": f"Null IDs: {null_ids}, Duplicate IDs: {duplicate_ids}.",
    }

    # Check 3: title not null
    null_titles = int(df["title"].isna().sum()) + int((df["title"].str.strip() == "").sum())
    checks["title_not_null"] = {
        "passed": null_titles == 0,
        "detail": f"Null/empty titles: {null_titles}.",
    }

    # Check 4: summary length
    if "summary_chars" in df.columns:
        mean_summary_chars = float(df["summary_chars"].mean())
        short_summaries = int((df["summary_chars"] < 10).sum())
    else:
        mean_summary_chars = float(df["summary"].str.len().mean()) if "summary" in df.columns else 0.0
        short_summaries = int((df["summary"].str.len() < 10).sum()) if "summary" in df.columns else len(df)
    checks["summary_length"] = {
        "passed": mean_summary_chars >= 50,
        "detail": f"Mean summary length: {mean_summary_chars:.0f} chars. Short summaries (<10 chars): {short_summaries}.",
    }

    # Check 5: Freshness
    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns:
        fresh_rows = int((df["age_days"] <= threshold).sum())
        stale_rows = row_count - fresh_rows
        freshness_ratio = fresh_rows / row_count if row_count > 0 else 0.0
    else:
        fresh_rows = 0
        stale_rows = row_count
        freshness_ratio = 0.0
    checks["freshness"] = {
        "passed": freshness_ratio >= 0.5,
        "detail": f"Fresh rows: {fresh_rows}/{row_count} ({freshness_ratio:.1%}). Threshold: {threshold} days.",
    }

    # Overall
    all_passed = all(check["passed"] for check in checks.values())
    result = {
        "report_name": report_name,
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks.values() if c["passed"]),
        "all_passed": all_passed,
        "checks": checks,
    }

    # Save to quality directory
    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, result)
    print(f"[quality] {result['passed_checks']}/{result['total_checks']} checks passed → {output_path}")

    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build a freshness report summarizing data recency.

    Produces:
    - latest_published, oldest_published
    - stale_rows, total_rows
    - is_fresh (True if < 50% of rows are stale)
    """
    threshold = settings.freshness_threshold_days
    total_rows = len(df)

    if "published" in df.columns:
        pub_dates = pd.to_datetime(df["published"], errors="coerce")
        latest = pub_dates.max()
        oldest = pub_dates.min()
        latest_published = str(latest.date()) if pd.notna(latest) else "N/A"
        oldest_published = str(oldest.date()) if pd.notna(oldest) else "N/A"
    else:
        latest_published = "N/A"
        oldest_published = "N/A"

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold).sum())
    else:
        stale_rows = total_rows

    is_fresh = (stale_rows / total_rows) < 0.5 if total_rows > 0 else False

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    write_json(report_path, payload)
    print(f"[freshness] Fresh={is_fresh}, Stale={stale_rows}/{total_rows} → {report_path}")

    return payload
