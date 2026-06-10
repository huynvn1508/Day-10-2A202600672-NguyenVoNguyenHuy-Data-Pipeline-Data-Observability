from __future__ import annotations

import random
from datetime import timedelta

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate multiple types of data corruption on the cleaned dataframe.

    Corruption types:
    1. Drop some latest records.
    2. Blank summary on some rows.
    3. Inject noise into text.
    4. Truncate title.
    5. Make published date stale.
    6. Add duplicate rows.
    7. Rebuild text_for_embedding.
    8. Write corruption log to output_log_path.
    """
    corrupted = df.copy()
    log_entries: list[dict] = []
    random.seed(42)

    n = len(corrupted)
    if n < 5:
        raise ValueError(f"Dataset too small to corrupt meaningfully ({n} rows).")

    # --- 1. Drop latest records (top 3 by published) ---
    drop_count = min(3, n // 4)
    drop_indices = corrupted.head(drop_count).index.tolist()
    dropped_ids = corrupted.loc[drop_indices, "paper_id"].tolist()
    corrupted = corrupted.drop(drop_indices).reset_index(drop=True)
    log_entries.append({
        "action": "drop_latest_records",
        "count": drop_count,
        "paper_ids": dropped_ids,
        "detail": f"Dropped {drop_count} most recent records.",
    })

    n = len(corrupted)

    # --- 2. Blank summary ---
    blank_count = min(3, n // 3)
    blank_indices = random.sample(range(n), blank_count)
    blank_ids = corrupted.iloc[blank_indices]["paper_id"].tolist()
    for idx in blank_indices:
        corrupted.at[corrupted.index[idx], "summary"] = ""
        corrupted.at[corrupted.index[idx], "summary_chars"] = 0
    log_entries.append({
        "action": "blank_summary",
        "count": blank_count,
        "paper_ids": blank_ids,
        "detail": f"Blanked summary for {blank_count} rows.",
    })

    # --- 3. Inject noise ---
    noise_count = min(3, n // 3)
    remaining = [i for i in range(n) if i not in blank_indices]
    noise_indices = random.sample(remaining, min(noise_count, len(remaining)))
    noise_ids = corrupted.iloc[noise_indices]["paper_id"].tolist()
    for idx in noise_indices:
        original = corrupted.at[corrupted.index[idx], "summary"]
        corrupted.at[corrupted.index[idx], "summary"] = f"NOISE_XYZ {original}"
        corrupted.at[corrupted.index[idx], "summary_chars"] = len(corrupted.at[corrupted.index[idx], "summary"])
    log_entries.append({
        "action": "inject_noise",
        "count": noise_count,
        "paper_ids": noise_ids,
        "detail": f"Injected 'NOISE_XYZ' prefix into {noise_count} summaries.",
    })

    # --- 4. Truncate title ---
    trunc_count = min(3, n // 3)
    trunc_indices = random.sample(range(n), trunc_count)
    trunc_ids = corrupted.iloc[trunc_indices]["paper_id"].tolist()
    for idx in trunc_indices:
        original_title = corrupted.at[corrupted.index[idx], "title"]
        corrupted.at[corrupted.index[idx], "title"] = original_title[:15] + "..."
    log_entries.append({
        "action": "truncate_title",
        "count": trunc_count,
        "paper_ids": trunc_ids,
        "detail": f"Truncated title to 15 chars for {trunc_count} rows.",
    })

    # --- 5. Make published date stale (shift back 5 years) ---
    stale_count = min(3, n // 3)
    stale_indices = random.sample(range(n), stale_count)
    stale_ids = corrupted.iloc[stale_indices]["paper_id"].tolist()
    for idx in stale_indices:
        try:
            original_date = pd.to_datetime(corrupted.at[corrupted.index[idx], "published"])
            stale_date = original_date - timedelta(days=5 * 365)
            corrupted.at[corrupted.index[idx], "published"] = stale_date.strftime("%Y-%m-%d")
            corrupted.at[corrupted.index[idx], "age_days"] = int(corrupted.at[corrupted.index[idx], "age_days"]) + 5 * 365
        except Exception:
            pass
    log_entries.append({
        "action": "stale_dates",
        "count": stale_count,
        "paper_ids": stale_ids,
        "detail": f"Shifted published date back 5 years for {stale_count} rows.",
    })

    # --- 6. Add duplicate rows ---
    dup_count = min(2, n // 3)
    dup_rows = corrupted.head(dup_count).copy()
    dup_ids = dup_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries.append({
        "action": "add_duplicates",
        "count": dup_count,
        "paper_ids": dup_ids,
        "detail": f"Duplicated {dup_count} rows.",
    })

    # --- 7. Rebuild text_for_embedding for all rows ---
    # Ensure no NaN in text columns before concatenation
    for col in ["title", "authors_joined", "categories_joined", "summary"]:
        corrupted[col] = corrupted[col].fillna("").astype(str)
    corrupted["summary_chars"] = corrupted["summary"].str.len().astype(int)

    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"] + "\n"
        "Authors: " + corrupted["authors_joined"] + "\n"
        "Categories: " + corrupted["categories_joined"] + "\n"
        "Abstract: " + corrupted["summary"]
    )

    # --- 8. Write corruption log ---
    corruption_log = {
        "total_corruptions": len(log_entries),
        "original_rows": len(df),
        "corrupted_rows": len(corrupted),
        "actions": log_entries,
    }
    write_json(output_log_path, corruption_log)
    print(f"[corruption] Applied {len(log_entries)} corruption types → {output_log_path}")

    return corrupted
