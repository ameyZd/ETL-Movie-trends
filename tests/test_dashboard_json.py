from datetime import datetime, timezone
import json

import pandas as pd

from src.tmdb_pipeline import (
    build_dashboard_keys,
    dataframe_to_dashboard_payload,
    dashboard_payload_to_json_bytes,
    update_dashboard_manifest,
)


def test_dashboard_keys_use_latest_manifest_and_weekly_snapshot():
    keys = build_dashboard_keys("tmdb/trending/weekly/dashboard", datetime(2026, 6, 19, tzinfo=timezone.utc))

    assert keys == {
        "latest": "tmdb/trending/weekly/dashboard/latest.json",
        "manifest": "tmdb/trending/weekly/dashboard/manifest.json",
        "weekly": "tmdb/trending/weekly/dashboard/weeks/2026-06-19.json",
    }


def test_dashboard_payload_is_json_serializable():
    frame = pd.DataFrame(
        [
            {
                "id": 1,
                "trend_rank": 1,
                "title": "Example Movie",
                "popularity": 99.5,
                "runtime": None,
                "poster_url": "https://image.tmdb.org/t/p/w500/example.jpg",
            }
        ]
    )

    payload = dataframe_to_dashboard_payload(
        frame,
        snapshot_date=datetime(2026, 6, 19, tzinfo=timezone.utc),
        parquet_key="tmdb/trending/weekly/year=2026/week=25/trending_movies_2026-06-19.parquet",
    )
    decoded = json.loads(dashboard_payload_to_json_bytes(payload))

    assert decoded["schema_version"] == 1
    assert decoded["snapshot_date"] == "2026-06-19"
    assert decoded["row_count"] == 1
    assert decoded["movies"][0]["title"] == "Example Movie"
    assert decoded["movies"][0]["runtime"] is None
    assert decoded["movies"][0]["poster_url"].endswith("example.jpg")


def test_dashboard_manifest_replaces_same_week_and_sorts_latest_first():
    manifest = update_dashboard_manifest(
        {"schema_version": 1, "weeks": []},
        snapshot_date=datetime(2026, 6, 12, tzinfo=timezone.utc),
        weekly_key="dashboard/weeks/2026-06-12.json",
        row_count=20,
        parquet_key="weekly/2026-06-12.parquet",
    )
    manifest = update_dashboard_manifest(
        manifest,
        snapshot_date=datetime(2026, 6, 19, tzinfo=timezone.utc),
        weekly_key="dashboard/weeks/2026-06-19.json",
        row_count=20,
        parquet_key="weekly/2026-06-19.parquet",
    )
    manifest = update_dashboard_manifest(
        manifest,
        snapshot_date=datetime(2026, 6, 12, tzinfo=timezone.utc),
        weekly_key="dashboard/weeks/2026-06-12.json",
        row_count=19,
        parquet_key="weekly/2026-06-12-rerun.parquet",
    )

    assert manifest["latest_snapshot_date"] == "2026-06-19"
    assert [week["snapshot_date"] for week in manifest["weeks"]] == [
        "2026-06-19",
        "2026-06-12",
    ]
    assert manifest["weeks"][1]["row_count"] == 19
    assert len(manifest["weeks"]) == 2
