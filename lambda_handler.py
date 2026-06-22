from __future__ import annotations

import os
from typing import Any

import pendulum

from src.tmdb_pipeline import DEFAULT_DASHBOARD_PREFIX, DEFAULT_S3_PREFIX, run_weekly_snapshot


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    access_token = os.environ["TMDB_ACCESS_TOKEN"]
    bucket_name = os.environ["S3_BUCKET"]
    prefix = os.getenv("S3_PREFIX", DEFAULT_S3_PREFIX)
    dashboard_prefix = os.getenv(
        "S3_DASHBOARD_PREFIX",
        f"{prefix.strip('/')}/{DEFAULT_DASHBOARD_PREFIX}",
    )
    snapshot_date = pendulum.now("UTC")

    result = run_weekly_snapshot(
        access_token=access_token,
        bucket_name=bucket_name,
        prefix=prefix,
        dashboard_prefix=dashboard_prefix,
        snapshot_date=snapshot_date,
    )
    return {
        "statusCode": 200,
        "body": result,
    }
