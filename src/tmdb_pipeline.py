from __future__ import annotations

import io
import json
import logging
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError
import pandas as pd
import pendulum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

TMDB_LANGUAGE = "en-US"
TMDB_TRENDING_URL = "https://api.themoviedb.org/3/trending/movie/week"
TMDB_MOVIE_DETAILS_URL = "https://api.themoviedb.org/3/movie/{movie_id}"
DEFAULT_S3_PREFIX = "trending-movies/"
DEFAULT_DASHBOARD_PREFIX = "dashboard"
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_BACKOFF_SECONDS = 0.25


def build_tmdb_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_trending_movies(
    access_token: str,
    session: requests.Session,
) -> list[dict[str, Any]]:
    response = session.get(
        TMDB_TRENDING_URL,
        params={"language": TMDB_LANGUAGE},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("results", [])


def fetch_movie_details(
    movie_id: int,
    access_token: str,
    session: requests.Session,
) -> dict[str, Any]:
    response = session.get(
        TMDB_MOVIE_DETAILS_URL.format(movie_id=movie_id),
        params={"language": TMDB_LANGUAGE},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def rank_trending_movies(trending_movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": movie["id"],
            "trend_rank": rank,
        }
        for rank, movie in enumerate(trending_movies, start=1)
    ]


def build_enriched_records(
    trending_movies: list[dict[str, Any]],
    access_token: str,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    fetched_at = pendulum.now("UTC").to_iso8601_string()

    with build_tmdb_session() as session:
        for movie in trending_movies:
            movie_id = movie["id"]
            try:
                details = fetch_movie_details(movie_id, access_token, session)
                enriched.append(
                    {
                        "id": movie_id,
                        "trend_rank": movie["trend_rank"],
                        "title": details.get("title", ""),
                        "release_date": details.get("release_date", ""),
                        "runtime": details.get("runtime"),
                        "genres": ", ".join(
                            genre["name"] for genre in details.get("genres", [])
                        ),
                        "budget": details.get("budget"),
                        "revenue": details.get("revenue"),
                        "popularity": details.get("popularity"),
                        "vote_average": details.get("vote_average"),
                        "vote_count": details.get("vote_count"),
                        "original_language": details.get("original_language"),
                        "overview": details.get("overview", ""),
                        "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}",
                        "fetched_at": fetched_at,
                    }
                )
                log.info("Fetched %s (%s)", details.get("title", movie_id), movie_id)
            except requests.RequestException as exc:
                log.warning("Skipping movie %s because TMDB request failed: %s", movie_id, exc)

            time.sleep(REQUEST_BACKOFF_SECONDS)

    return enriched


def build_s3_key(prefix: str, data_interval_start: Any) -> str:
    interval_start = pendulum.instance(data_interval_start).in_timezone("UTC")
    iso_calendar = interval_start.date().isocalendar()
    partition_date = interval_start.to_date_string()
    normalized_prefix = prefix.strip("/")
    return (
        f"{normalized_prefix}/year={iso_calendar.year}/week={iso_calendar.week:02d}/"
        f"trending_movies_{partition_date}.parquet"
    )


def build_snapshot_date(snapshot_date: Any) -> str:
    return pendulum.instance(snapshot_date).in_timezone("UTC").to_date_string()


def normalize_s3_prefix(prefix: str) -> str:
    return prefix.strip("/")


def build_dashboard_keys(prefix: str, snapshot_date: Any) -> dict[str, str]:
    normalized_prefix = normalize_s3_prefix(prefix)
    partition_date = build_snapshot_date(snapshot_date)
    return {
        "latest": f"{normalized_prefix}/latest.json",
        "manifest": f"{normalized_prefix}/manifest.json",
        "weekly": f"{normalized_prefix}/weeks/{partition_date}.json",
    }


def build_snapshot_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(records).sort_values("trend_rank").reset_index(drop=True)


def dataframe_to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    parquet_buffer = io.BytesIO()
    frame.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    return parquet_buffer.getvalue()


def dataframe_to_dashboard_payload(
    frame: pd.DataFrame,
    *,
    snapshot_date: Any,
    parquet_key: str,
) -> dict[str, Any]:
    clean_frame = frame.astype(object).where(pd.notna(frame), None)
    return {
        "schema_version": 1,
        "snapshot_date": build_snapshot_date(snapshot_date),
        "generated_at": pendulum.now("UTC").to_iso8601_string(),
        "row_count": len(clean_frame),
        "parquet_key": parquet_key,
        "movies": clean_frame.to_dict(orient="records"),
    }


def dashboard_payload_to_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def parse_dashboard_manifest(manifest_text: str | None) -> dict[str, Any]:
    if not manifest_text:
        return {"schema_version": 1, "weeks": []}
    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError:
        log.warning("Existing dashboard manifest is invalid JSON; rebuilding it.")
        return {"schema_version": 1, "weeks": []}

    if not isinstance(manifest, dict):
        return {"schema_version": 1, "weeks": []}
    if not isinstance(manifest.get("weeks"), list):
        manifest["weeks"] = []
    return manifest


def update_dashboard_manifest(
    manifest: dict[str, Any],
    *,
    snapshot_date: Any,
    weekly_key: str,
    row_count: int,
    parquet_key: str,
) -> dict[str, Any]:
    partition_date = build_snapshot_date(snapshot_date)
    weeks_by_date = {
        week.get("snapshot_date"): week
        for week in manifest.get("weeks", [])
        if isinstance(week, dict) and week.get("snapshot_date")
    }
    weeks_by_date[partition_date] = {
        "snapshot_date": partition_date,
        "key": weekly_key,
        "row_count": row_count,
        "parquet_key": parquet_key,
    }
    weeks = sorted(
        weeks_by_date.values(),
        key=lambda week: week["snapshot_date"],
        reverse=True,
    )
    return {
        "schema_version": 1,
        "updated_at": pendulum.now("UTC").to_iso8601_string(),
        "latest_snapshot_date": weeks[0]["snapshot_date"] if weeks else None,
        "latest_key": weeks[0]["key"] if weeks else None,
        "weeks": weeks,
    }


def upload_parquet_bytes_to_s3(
    parquet_bytes: bytes,
    bucket_name: str,
    object_key: str,
    *,
    boto3_session: boto3.session.Session | None = None,
) -> None:
    session = boto3_session or boto3.session.Session()
    s3_client = session.client("s3")
    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=parquet_bytes,
        ContentType="application/octet-stream",
    )


def upload_dashboard_json_to_s3(
    *,
    payload: dict[str, Any],
    bucket_name: str,
    dashboard_prefix: str,
    snapshot_date: Any,
    boto3_session: boto3.session.Session | None = None,
) -> dict[str, str]:
    session = boto3_session or boto3.session.Session()
    s3_client = session.client("s3")
    keys = build_dashboard_keys(dashboard_prefix, snapshot_date)

    manifest_text: str | None = None
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=keys["manifest"])
        manifest_text = response["Body"].read().decode("utf-8")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {"NoSuchKey", "404"}:
            raise

    manifest = update_dashboard_manifest(
        parse_dashboard_manifest(manifest_text),
        snapshot_date=snapshot_date,
        weekly_key=keys["weekly"],
        row_count=payload["row_count"],
        parquet_key=payload["parquet_key"],
    )

    weekly_bytes = dashboard_payload_to_json_bytes(payload)
    manifest_bytes = dashboard_payload_to_json_bytes(manifest)
    for key, body in (
        (keys["weekly"], weekly_bytes),
        (keys["latest"], weekly_bytes),
        (keys["manifest"], manifest_bytes),
    ):
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

    return keys


def run_weekly_snapshot(
    *,
    access_token: str,
    bucket_name: str,
    prefix: str = DEFAULT_S3_PREFIX,
    dashboard_prefix: str | None = None,
    snapshot_date: Any | None = None,
    boto3_session: boto3.session.Session | None = None,
) -> dict[str, Any]:
    snapshot_point = snapshot_date or pendulum.now("UTC")

    with build_tmdb_session() as session:
        trending_movies = fetch_trending_movies(access_token, session)

    if not trending_movies:
        raise ValueError("TMDB returned no weekly trending movies.")

    ranked_movies = rank_trending_movies(trending_movies)
    records = build_enriched_records(ranked_movies, access_token)
    if not records:
        raise ValueError("TMDB detail enrichment returned no records.")

    frame = build_snapshot_frame(records)
    parquet_bytes = dataframe_to_parquet_bytes(frame)
    object_key = build_s3_key(prefix, snapshot_point)
    effective_dashboard_prefix = (
        dashboard_prefix or f"{normalize_s3_prefix(prefix)}/{DEFAULT_DASHBOARD_PREFIX}"
    )
    upload_parquet_bytes_to_s3(
        parquet_bytes,
        bucket_name,
        object_key,
        boto3_session=boto3_session,
    )
    dashboard_payload = dataframe_to_dashboard_payload(
        frame,
        snapshot_date=snapshot_point,
        parquet_key=object_key,
    )
    dashboard_keys = upload_dashboard_json_to_s3(
        payload=dashboard_payload,
        bucket_name=bucket_name,
        dashboard_prefix=effective_dashboard_prefix,
        snapshot_date=snapshot_point,
        boto3_session=boto3_session,
    )

    row_count = len(frame)
    log.info("Saved %s rows to s3://%s/%s", row_count, bucket_name, object_key)
    log.info(
        "Saved dashboard JSON to s3://%s/%s and s3://%s/%s",
        bucket_name,
        dashboard_keys["latest"],
        bucket_name,
        dashboard_keys["manifest"],
    )
    return {
        "bucket": bucket_name,
        "key": object_key,
        "dashboard_keys": dashboard_keys,
        "row_count": row_count,
    }
