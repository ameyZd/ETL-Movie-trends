from __future__ import annotations

from typing import Any

import pandas as pd


def split_genres(value: Any) -> list[str]:
    return [genre.strip() for genre in value.split(",") if genre.strip()] if isinstance(value, str) else []


def clean_text(value: Any, fallback: str = "Not available") -> str:
    if value is None or pd.isna(value):
        return fallback
    return str(value).strip() or fallback


def poster_url(movie: pd.Series) -> str | None:
    value = movie.get("poster_url")
    if value is None or pd.isna(value):
        return None
    url = str(value).strip()
    return url if url.startswith("https://") else None


def filter_movies(frame: pd.DataFrame, title_query: str, minimum_rating: float, genres: list[str]) -> pd.DataFrame:
    filtered = frame[frame["vote_average"].fillna(0) >= minimum_rating].copy()
    if title_query:
        filtered = filtered[filtered["title"].str.contains(title_query, case=False, na=False)]
    if genres:
        selected = set(genres)
        filtered = filtered[filtered["genres"].apply(lambda value: bool(set(split_genres(value)) & selected))]
    return filtered.reset_index(drop=True)


def critics_pick(frame: pd.DataFrame) -> pd.Series:
    candidates = frame[frame["vote_count"] >= frame["vote_count"].median()]
    return candidates.sort_values(["vote_average", "vote_count"], ascending=False).iloc[0]


def balanced_pick(frame: pd.DataFrame) -> pd.Series:
    scored = frame.copy()
    for column, score in (("vote_average", "rating_score"), ("popularity", "popularity_score")):
        value_range = scored[column].max() - scored[column].min()
        scored[score] = (scored[column] - scored[column].min()) / value_range if value_range else 1
    scored["score"] = 0.55 * scored["rating_score"] + 0.45 * scored["popularity_score"]
    return scored.sort_values("score", ascending=False).iloc[0]
