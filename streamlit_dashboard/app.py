"""Streamlit entry point. Page rendering and data concerns live in dashboard/."""

import sys
from pathlib import Path

import streamlit as st

APP_DIRECTORY = Path(__file__).parent
if str(APP_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(APP_DIRECTORY))

from dashboard.analytics import filter_movies, split_genres
from dashboard.data import get_data_source, load_snapshot, load_weeks, payload_to_frame
from dashboard.styles import apply_styles
from dashboard.views import render_discover, render_explorer, render_historical


def main() -> None:
    st.set_page_config(page_title="TMDB Weekly Trends", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
    apply_styles()
    source = get_data_source()
    weeks = load_weeks(source)
    week_labels = [week["snapshot_date"] for week in weeks if week.get("snapshot_date")]

    with st.sidebar:
        st.markdown("## TMDB Weekly Trends")
        page = st.radio("Navigate", ["Discover", "Movie Explorer", "Historical Analytics"])
        st.divider(); st.markdown("### Snapshot filters")
        selected_label = st.selectbox("Week", week_labels, index=0) if week_labels else None
        selected_week = next((week for week in weeks if week.get("snapshot_date") == selected_label), None)
        title_query = st.text_input("Search title")
        minimum_rating = st.slider("Minimum rating", 0.0, 10.0, 0.0, 0.5)

    try:
        payload = load_snapshot(source, selected_week)
    except Exception as exc:
        st.error("Could not load the dashboard JSON from S3."); st.exception(exc); st.stop()
    frame = payload_to_frame(payload)
    if frame.empty:
        st.warning("No movie records were found in this snapshot."); st.stop()

    genres = sorted({genre for value in frame["genres"] for genre in split_genres(value)})
    with st.sidebar:
        selected_genres = st.multiselect("Genres", genres)
    filtered = filter_movies(frame, title_query, minimum_rating, selected_genres)
    if filtered.empty and page in {"Discover", "Movie Explorer"}:
        st.warning("No movies match these filters. Try a lower rating or remove a genre."); st.stop()

    if page == "Discover":
        render_discover(filtered, payload)
    elif page == "Movie Explorer":
        render_explorer(filtered)
    else:
        render_historical(source, weeks)


if __name__ == "__main__":
    main()
