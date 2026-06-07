from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import httpx

from generate_nail_taxonomy_from_dir import (
    build_canonical_records,
    build_image_mapping,
    collect_profiles,
    read_existing_display_names,
)


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "ai-service/.env"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def supabase_config() -> tuple[str, str]:
    env_file = load_env(ENV_PATH)
    supabase_url = (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        or env_file.get("SUPABASE_URL")
        or env_file.get("NEXT_PUBLIC_SUPABASE_URL")
    )
    api_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or env_file.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or env_file.get("SUPABASE_ANON_KEY")
        or env_file.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    if not supabase_url or not api_key:
        raise RuntimeError("Supabase URL or API key is missing. Check ai-service/.env.")
    return supabase_url.rstrip("/"), api_key


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: Any | None = None,
    prefer: str | None = None,
) -> Any:
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    try:
        response = httpx.request(method, url, headers=headers, json=payload, timeout=20.0)
        response.raise_for_status()
        return response.json() if response.content else None
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Supabase {method} failed: HTTP {exc.response.status_code} {exc.response.text}"
        ) from exc


def records_for_db(records: list[dict]) -> list[dict]:
    return [
        {
            "id": record["id"],
            "name": record["name"],
            "color": record["color"],
            "finish": record["finish"],
            "occasion": record["occasion"],
            "tags": record["tags"],
            "palette": record["palette"],
            "prompt": record["prompt"],
            "difficulty": record["difficulty"],
            "price_level": record["price_level"],
            "image_url": record["image_url"],
            "stock_total": record["stock_total"],
            "stock_reserved": record["stock_reserved"],
            "nail_length": record["nail_length"],
            "taxonomy": record["taxonomy"],
            "source_batch": "six-dimensional-taxonomy",
        }
        for record in records
    ]


def available_columns(base_url: str, api_key: str, candidates: list[str]) -> set[str]:
    available: set[str] = set()
    for column in candidates:
        url = f"{base_url}/rest/v1/nail_styles?select={column}&limit=1"
        try:
            request_json("GET", url, api_key)
            available.add(column)
        except RuntimeError:
            continue
    return available


def filter_columns(records: list[dict], columns: set[str]) -> list[dict]:
    return [{key: value for key, value in record.items() if key in columns} for record in records]


def hide_stale_rows(base_url: str, api_key: str, canonical_ids: set[str], columns: set[str]) -> list[str]:
    url = f"{base_url}/rest/v1/nail_styles?select=id&order=id.asc"
    rows = request_json("GET", url, api_key)
    if not isinstance(rows, list):
        return []

    stale_ids: list[str] = []
    for row in rows:
        style_id = str(row.get("id", ""))
        is_old_catalog = (
            style_id.startswith("library-20260514-")
            or style_id.startswith("seed-")
            or style_id.startswith("cherry-mirror-")
            or style_id == "fixed-target-red-black-spider"
        )
        if is_old_catalog and style_id not in canonical_ids:
            stale_ids.append(style_id)

    for start in range(0, len(stale_ids), 50):
        chunk = stale_ids[start : start + 50]
        encoded = ",".join(urllib.parse.quote(item, safe="-_") for item in chunk)
        patch_url = f"{base_url}/rest/v1/nail_styles?id=in.({encoded})"
        patch_payload = filter_columns(
            [
                {
                    "stock_total": 0,
                    "stock_reserved": 0,
                    "tags": ["deprecated"],
                    "occasion": ["隐藏"],
                    "taxonomy": {},
                    "source_batch": "hidden-stale-catalog",
                }
            ],
            columns,
        )[0]
        if patch_payload:
            request_json("PATCH", patch_url, api_key, patch_payload, prefer="return=minimal")

    return stale_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", help="Path to the six-dimensional taxonomy directory")
    args = parser.parse_args()

    source_root = Path(args.source_dir).expanduser().resolve()
    existing_names = read_existing_display_names()
    source_to_library, unmatched_library_ids = build_image_mapping(source_root)
    profiles = collect_profiles(source_root)
    records = build_canonical_records(existing_names, profiles, source_to_library)
    db_records = records_for_db(records)
    canonical_ids = {record["id"] for record in db_records}

    base_url, api_key = supabase_config()
    candidate_columns = [
        "id",
        "name",
        "color",
        "finish",
        "occasion",
        "tags",
        "palette",
        "prompt",
        "difficulty",
        "price_level",
        "image_url",
        "stock_total",
        "stock_reserved",
        "nail_length",
        "taxonomy",
        "source_batch",
    ]
    columns = available_columns(base_url, api_key, candidate_columns)
    missing_columns = sorted(set(candidate_columns) - columns)
    db_records = filter_columns(db_records, columns)
    upsert_url = f"{base_url}/rest/v1/nail_styles?on_conflict=id"
    request_json(
        "POST",
        upsert_url,
        api_key,
        db_records,
        prefer="resolution=merge-duplicates,return=minimal",
    )
    stale_ids = hide_stale_rows(base_url, api_key, canonical_ids, columns)

    sample_id = "library-20260514-007"
    sample_select = ",".join([column for column in ["id", "name", "tags", "taxonomy", "nail_length", "image_url", "stock_total", "stock_reserved"] if column in columns])
    sample_url = (
        f"{base_url}/rest/v1/nail_styles?"
        f"select={sample_select}&id=eq.{sample_id}"
    )
    sample = request_json("GET", sample_url, api_key)

    print(
        json.dumps(
            {
                "synced_canonical_styles": len(db_records),
                "hidden_stale_styles": len(stale_ids),
                "missing_columns": missing_columns,
                "unmatched_library_ids": unmatched_library_ids,
                "sample": sample,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
