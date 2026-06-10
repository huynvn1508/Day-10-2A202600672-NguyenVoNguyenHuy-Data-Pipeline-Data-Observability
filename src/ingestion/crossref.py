from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_html(text: str) -> str:
    """Remove HTML/XML tags from abstract text."""
    return re.sub(r"<[^>]+>", "", text)


def _parse_date_parts(date_parts: list[list[int]] | None) -> str:
    """Convert Crossref date-parts [[2024, 3, 15]] to ISO date string."""
    if not date_parts or not date_parts[0]:
        return ""
    parts = date_parts[0]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _find_pdf_url(links: list[dict] | None) -> str:
    """Extract the first PDF link from Crossref link objects."""
    if not links:
        return ""
    for link in links:
        content_type = link.get("content-type", "")
        if "pdf" in content_type.lower():
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API response payload into a list of PaperRecord objects.

    Steps:
    1. Iterate over payload["message"]["items"].
    2. Extract DOI, title, abstract, authors, subject, dates, URLs.
    3. Normalize text and skip invalid records.
    4. Return list of PaperRecord.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # --- Required fields ---
        doi = item.get("DOI", "").strip()
        raw_title = item.get("title", [])
        title = normalize_whitespace(" ".join(raw_title)) if raw_title else ""

        if not doi or not title:
            continue

        # --- Abstract ---
        raw_abstract = item.get("abstract", "")
        summary = normalize_whitespace(_strip_html(raw_abstract))

        # --- Authors ---
        raw_authors = item.get("author", [])
        authors: list[str] = []
        for author in raw_authors:
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)

        # --- Categories / subjects ---
        categories: list[str] = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        # --- Dates ---
        published = _parse_date_parts(
            item.get("published", item.get("published-print", item.get("published-online", {})))
            .get("date-parts")
            if isinstance(item.get("published", item.get("published-print", item.get("published-online"))), dict)
            else None
        )
        updated = _parse_date_parts(
            item.get("created", {}).get("date-parts")
        )

        # --- URLs ---
        abs_url = item.get("URL", "")
        pdf_url = _find_pdf_url(item.get("link"))

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment="",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Call Crossref API, save raw response, parse into records.

    Steps:
    1. Build params from settings (query, filter, rows).
    2. Call API with retry for 429/503.
    3. Save raw response to settings.paths.raw_api_response.
    4. Parse payload with parse_crossref_payload.
    5. Save records to settings.paths.raw_records_json.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "relevance",
        "order": "desc",
    }

    headers = {
        "User-Agent": "DataPipelineLab/1.0 (mailto:student@vinuni.edu.vn)",
    }

    max_retries = 3
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                CROSSREF_API_URL, params=params, headers=headers, timeout=30
            )
            if response.status_code in (429, 503):
                wait = 2 ** attempt
                print(f"[crossref] Rate-limited ({response.status_code}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Crossref API request failed after {max_retries} retries: {exc}") from exc
            time.sleep(2 ** attempt)

    if response is None:
        raise RuntimeError("Crossref API request failed: no response received.")

    payload = response.json()

    # Save raw API response
    write_json(settings.paths.raw_api_response, payload)
    print(f"[crossref] Saved raw API response → {settings.paths.raw_api_response}")

    # Parse records
    records = parse_crossref_payload(payload)
    print(f"[crossref] Parsed {len(records)} records from Crossref response.")

    # Save parsed records
    records_dicts = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dicts)
    print(f"[crossref] Saved raw records → {settings.paths.raw_records_json}")

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map each dict to a PaperRecord."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(PaperRecord(**item))
    return records
