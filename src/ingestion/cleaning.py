from __future__ import annotations

import re
from dataclasses import asdict
from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _strip_html(text: str) -> str:
    """Remove any residual HTML tags."""
    return re.sub(r"<[^>]+>", "", text)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a DataFrame ready for embedding.

    Steps:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Compute age_days.
    4. Create helper columns:
       - authors_joined, categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates and filter bad rows.
    6. Sort by published descending and return.
    """
    if not records:
        raise ValueError("No records provided for cleaning.")

    # Convert dataclass list to DataFrame
    rows = [asdict(r) for r in records]
    df = pd.DataFrame(rows)

    # --- Normalize text fields ---
    df["title"] = df["title"].apply(lambda x: normalize_whitespace(_strip_html(str(x))) if pd.notna(x) else "")
    df["summary"] = df["summary"].apply(lambda x: normalize_whitespace(_strip_html(str(x))) if pd.notna(x) else "")

    # --- Authors: convert list → joined string ---
    df["authors_joined"] = df["authors"].apply(
        lambda authors: ", ".join(str(a) for a in authors) if isinstance(authors, list) else str(authors)
    )

    # --- Categories: convert list → joined string ---
    df["categories_joined"] = df["categories"].apply(
        lambda cats: ", ".join(str(c) for c in cats) if isinstance(cats, list) else str(cats)
    )

    # --- Parse dates ---
    df["published"] = pd.to_datetime(df["published"], errors="coerce", format="mixed")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", format="mixed")

    # Fill NaT published with updated, then with run_date
    df["published"] = df["published"].fillna(df["updated"])
    df["published"] = df["published"].fillna(pd.Timestamp(run_date))

    # --- Compute age_days ---
    run_ts = pd.Timestamp(run_date)
    if run_ts.tzinfo is not None:
        run_ts = run_ts.tz_localize(None)
    df["published"] = df["published"].dt.tz_localize(None)
    df["age_days"] = (run_ts - df["published"]).dt.days

    # --- Helper columns ---
    df["summary_chars"] = df["summary"].str.len()

    df["text_for_embedding"] = (
        "Title: " + df["title"] + "\n"
        "Authors: " + df["authors_joined"] + "\n"
        "Categories: " + df["categories_joined"] + "\n"
        "Abstract: " + df["summary"]
    )

    # --- Drop duplicates ---
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # --- Filter bad rows ---
    df = df[df["title"].str.strip().str.len() > 0]
    df = df[df["summary_chars"] >= 10]

    # --- Sort by published descending ---
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    # --- Format dates back to string for downstream JSON serialization ---
    df["published"] = df["published"].dt.strftime("%Y-%m-%d")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    df["age_days"] = df["age_days"].astype(int)
    df["summary_chars"] = df["summary_chars"].astype(int)

    print(f"[cleaning] Cleaned dataset: {len(df)} rows, {df.columns.tolist()}")
    return df
