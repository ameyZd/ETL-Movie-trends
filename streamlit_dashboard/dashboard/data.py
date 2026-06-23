from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
import pandas as pd
import requests
import streamlit as st

LOCAL_SECRETS_PATH = Path(__file__).parents[1] / ".streamlit" / "secrets.toml"


@dataclass(frozen=True)
class DataSource:
    mode: str
    latest_url: str | None = None
    manifest_url: str | None = None
    bucket: str | None = None
    latest_key: str | None = None
    manifest_key: str | None = None
    region_name: str | None = None


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets.get(name)
    except st.errors.StreamlitSecretNotFoundError:
        value = None
    if value is not None:
        return str(value)
    if environment_value := os.getenv(name):
        return environment_value
    if LOCAL_SECRETS_PATH.exists():
        with LOCAL_SECRETS_PATH.open("rb") as file:
            value = tomllib.load(file).get(name)
        if value is not None:
            return str(value)
    return default


def get_data_source() -> DataSource:
    mode = (get_secret("DATA_MODE", "public_url") or "public_url").lower()
    if mode == "s3_private":
        return DataSource(
            mode=mode,
            bucket=get_secret("S3_BUCKET"),
            latest_key=get_secret("S3_LATEST_KEY", "tmdb/trending/weekly/dashboard/latest.json"),
            manifest_key=get_secret("S3_MANIFEST_KEY", "tmdb/trending/weekly/dashboard/manifest.json"),
            region_name=get_secret("AWS_REGION", "us-east-1"),
        )
    return DataSource(mode="public_url", latest_url=get_secret("LATEST_JSON_URL"), manifest_url=get_secret("MANIFEST_JSON_URL"))


@st.cache_data(ttl=900)
def _fetch_public_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=900)
def _fetch_s3_json(bucket: str, key: str, region: str, access_key: str | None, secret_key: str | None) -> dict[str, Any]:
    options: dict[str, Any] = {"region_name": region}
    if access_key and secret_key:
        options.update(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    response = boto3.client("s3", **options).get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def _fetch_json(source: DataSource, *, key: str | None = None, url: str | None = None) -> dict[str, Any]:
    if source.mode == "s3_private":
        if not source.bucket:
            raise ValueError("S3_BUCKET is required when DATA_MODE is s3_private.")
        return _fetch_s3_json(source.bucket, key or source.latest_key or "", source.region_name or "us-east-1", get_secret("AWS_ACCESS_KEY_ID"), get_secret("AWS_SECRET_ACCESS_KEY"))
    resolved_url = url or source.latest_url
    if not resolved_url:
        raise ValueError("Set LATEST_JSON_URL and MANIFEST_JSON_URL in Streamlit secrets.")
    return _fetch_public_json(resolved_url)


def load_weeks(source: DataSource) -> list[dict[str, Any]]:
    try:
        manifest = _fetch_json(source, key=source.manifest_key, url=source.manifest_url)
    except Exception:
        return []
    weeks = manifest.get("weeks", [])
    return weeks if isinstance(weeks, list) else []


def load_snapshot(source: DataSource, week: dict[str, Any] | None) -> dict[str, Any]:
    if not week:
        return _fetch_json(source)
    if source.mode == "s3_private":
        return _fetch_json(source, key=week["key"])
    parsed = urlparse(source.manifest_url or "")
    return _fetch_json(source, url=f"{parsed.scheme}://{parsed.netloc}/{week['key']}")


def payload_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(payload.get("movies", []))
    if frame.empty:
        return frame
    for column in ("trend_rank", "runtime", "popularity", "vote_average", "vote_count", "budget", "revenue"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("genres", "overview", "title", "poster_url", "tmdb_url"):
        if column not in frame:
            frame[column] = None
    return frame.sort_values("trend_rank").reset_index(drop=True)
