import logging
from datetime import timedelta
from typing import Any

import pendulum
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.sdk import Variable, dag, task
from src.tmdb_pipeline import (
    DEFAULT_S3_PREFIX,
    build_enriched_records,
    build_s3_key,
    build_snapshot_frame,
    build_tmdb_session,
    dataframe_to_parquet_bytes,
    fetch_trending_movies,
    rank_trending_movies,
)

log = logging.getLogger(__name__)

DAG_ID = "tmdb_weekly_trending_movies"
DEFAULT_AWS_CONN_ID = "aws_default"


@dag(
    dag_id=DAG_ID,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule="0 18 * * 5",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["tmdb", "movies", "etl", "s3"],
    description="Fetch weekly trending movies from TMDB and store a parquet snapshot in S3.",
)
def tmdb_weekly_trending_movies():
    @task(
        task_id="extract_trending_movies",
        execution_timeout=timedelta(minutes=5),
    )
    def extract_trending_movies() -> list[dict[str, Any]]:
        access_token = Variable.get("tmdb_access_token")
        with build_tmdb_session() as session:
            trending_movies = fetch_trending_movies(access_token, session)

        if not trending_movies:
            raise ValueError("TMDB returned no weekly trending movies.")

        return rank_trending_movies(trending_movies)

    @task(
        task_id="transform_movie_details",
        execution_timeout=timedelta(minutes=10),
    )
    def transform_movie_details(
        trending_movies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        access_token = Variable.get("tmdb_access_token")
        records = build_enriched_records(trending_movies, access_token)
        if not records:
            raise ValueError("TMDB detail enrichment returned no records.")
        return records

    @task(
        task_id="load_weekly_snapshot",
        execution_timeout=timedelta(minutes=10),
    )
    def load_weekly_snapshot(
        records: list[dict[str, Any]],
        *,
        data_interval_start=None,
    ) -> dict[str, Any]:
        bucket_name = Variable.get("tmdb_s3_bucket")
        prefix = Variable.get("tmdb_s3_prefix_weekly", default=DEFAULT_S3_PREFIX).strip("/")
        aws_conn_id = Variable.get("tmdb_aws_conn_id", default=DEFAULT_AWS_CONN_ID)

        frame = build_snapshot_frame(records)
        parquet_bytes = dataframe_to_parquet_bytes(frame)
        object_key = build_s3_key(prefix, data_interval_start)
        S3Hook(aws_conn_id=aws_conn_id).load_bytes(
            bytes_data=parquet_bytes,
            key=object_key,
            bucket_name=bucket_name,
            replace=True,
        )

        row_count = len(frame)
        log.info("Saved %s rows to s3://%s/%s", row_count, bucket_name, object_key)
        return {
            "bucket": bucket_name,
            "key": object_key,
            "row_count": row_count,
        }

    load_weekly_snapshot(transform_movie_details(extract_trending_movies()))


dag = tmdb_weekly_trending_movies()
