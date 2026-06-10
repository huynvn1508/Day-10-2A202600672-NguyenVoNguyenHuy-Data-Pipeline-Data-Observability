from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build an evaluation test set from the cleaned dataframe.

    Steps:
    1. Check minimum document count.
    2. Select representative papers.
    3. Generate multiple question types:
       - summary, authors, date, categories
    4. Each row has: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Write JSON to output_path.
    """
    if len(df) < 2:
        raise ValueError(f"Need at least 2 documents to build test set, got {len(df)}.")

    # Select up to 8 representative papers spread across the dataset
    sample_size = min(8, len(df))
    step = max(1, len(df) // sample_size)
    indices = list(range(0, len(df), step))[:sample_size]
    sample_df = df.iloc[indices]

    test_set: list[dict[str, Any]] = []
    question_id = 0

    for _, row in sample_df.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row.get("summary", "")
        authors_joined = row.get("authors_joined", "")
        published = str(row.get("published", ""))
        categories_joined = row.get("categories_joined", "")

        # --- Question type: summary ---
        question_id += 1
        test_set.append(
            {
                "id": f"q{question_id:03d}",
                "question_type": "summary",
                "question": f"What is the main contribution of '{title}'?",
                "ground_truth": first_sentence(summary) if summary else title,
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # --- Question type: authors ---
        question_id += 1
        test_set.append(
            {
                "id": f"q{question_id:03d}",
                "question_type": "authors",
                "question": f"Who authored '{title}'?",
                "ground_truth": authors_joined if authors_joined else "Unknown",
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # --- Question type: date ---
        question_id += 1
        test_set.append(
            {
                "id": f"q{question_id:03d}",
                "question_type": "date",
                "question": f"When was '{title}' published?",
                "ground_truth": published if published else "Unknown",
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # --- Question type: categories ---
        if categories_joined:
            question_id += 1
            test_set.append(
                {
                    "id": f"q{question_id:03d}",
                    "question_type": "categories",
                    "question": f"What categories does '{title}' belong to?",
                    "ground_truth": categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, test_set)
    print(f"[testset] Built {len(test_set)} questions from {sample_size} papers → {output_path}")
    return test_set
