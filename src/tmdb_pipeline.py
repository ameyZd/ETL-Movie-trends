from __future__ import annotations

import io
import logging
import time
from typing import Any

import boto3
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


def build_snapshot_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(records).sort_values("trend_rank").reset_index(drop=True)


def dataframe_to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    parquet_buffer = io.BytesIO()
    frame.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    return parquet_buffer.getvalue()


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


def run_weekly_snapshot(
    *,
    access_token: str,
    bucket_name: str,
    prefix: str = DEFAULT_S3_PREFIX,
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
    upload_parquet_bytes_to_s3(
        parquet_bytes,
        bucket_name,
        object_key,
        boto3_session=boto3_session,
    )

    row_count = len(frame)
    log.info("Saved %s rows to s3://%s/%s", row_count, bucket_name, object_key)
    return {
        "bucket": bucket_name,
        "key": object_key,
        "row_count": row_count,
    }
