from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.analytics import balanced_pick, clean_text, critics_pick, poster_url
from dashboard.data import DataSource, load_snapshot, payload_to_frame


def _layout(height: int = 420) -> dict:
    return {"template": "plotly_dark", "height": height, "margin": {"l": 12, "r": 26, "t": 20, "b": 10}, "paper_bgcolor": "#1e293b", "plot_bgcolor": "#1e293b", "font": {"color": "#f8fafc"}}


def _poster(movie: pd.Series) -> None:
    if url := poster_url(movie):
        st.image(url, width="stretch")
    else:
        st.markdown(f'<div class="empty-poster">{escape(clean_text(movie.get("title"), "TMDB Movie"))}</div>', unsafe_allow_html=True)


def _pick_card(label: str, movie: pd.Series, note: str) -> None:
    st.markdown(f'<div class="pick-card"><div class="pick-kicker">{escape(label)}</div><h3>{escape(clean_text(movie.get("title")))}</h3><p class="muted">{escape(note)}</p><p class="muted">Rating {float(movie.get("vote_average", 0) or 0):.1f}/10 | Weekly rank #{int(movie.get("trend_rank", 0))}</p></div>', unsafe_allow_html=True)
    if movie.get("tmdb_url"):
        st.link_button("View on TMDB", str(movie["tmdb_url"]))


def _spotlight(movie: pd.Series) -> None:
    st.subheader("Movie spotlight")
    poster_column, detail_column = st.columns([1, 2])
    with poster_column:
        _poster(movie)
    with detail_column:
        st.markdown('<span class="rank-badge">Balanced pick</span>', unsafe_allow_html=True)
        st.markdown(f"## {clean_text(movie.get('title'))}")
        rating, rank = st.columns(2)
        rating.metric("Rating", f"{float(movie.get('vote_average', 0) or 0):.1f} / 10")
        rank.metric("Popularity rank", f"#{int(movie.get('trend_rank', 0))}")
        runtime = movie.get("runtime")
        st.markdown(f"**{clean_text(movie.get('genres'), 'Genre unavailable')}**")
        st.caption(f"{int(runtime)} minutes" if pd.notna(runtime) else "Runtime unavailable")
        st.write(clean_text(movie.get("overview"), "No overview was supplied by TMDB."))
        if movie.get("tmdb_url"):
            st.link_button("Open movie details on TMDB", str(movie["tmdb_url"]), type="primary")


def _charts(frame: pd.DataFrame) -> None:
    left, right = st.columns(2)
    with left:
        st.subheader("What is hot right now?")
        st.caption("Top 10 movies ranked by the TMDB popularity signal.")
        top_ten = frame.nsmallest(10, "trend_rank").sort_values("popularity")
        figure = px.bar(top_ten, x="popularity", y="title", orientation="h", text="popularity", color_discrete_sequence=["#22c55e"], labels={"popularity": "TMDB popularity", "title": ""})
        figure.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
        layout = _layout(); layout["margin"] = {"l": 10, "r": 46, "t": 20, "b": 10}
        figure.update_layout(**layout, showlegend=False); figure.update_xaxes(gridcolor="#334155", zeroline=False); figure.update_yaxes(showgrid=False)
        st.plotly_chart(figure, width="stretch")
    with right:
        st.subheader("Popularity versus quality")
        st.caption("The upper-right quadrant contains this week's likely must-watch movies.")
        figure = px.scatter(frame, x="vote_average", y="popularity", size="vote_count", color="vote_average", color_continuous_scale=["#38bdf8", "#22c55e", "#facc15"], hover_name="title", hover_data={"genres": True, "runtime": True, "trend_rank": True}, labels={"vote_average": "Average rating", "popularity": "TMDB popularity", "vote_count": "Votes"})
        x_mid, y_mid = frame["vote_average"].median(), frame["popularity"].median()
        figure.add_vline(x=x_mid, line_dash="dot", line_color="#64748b"); figure.add_hline(y=y_mid, line_dash="dot", line_color="#64748b")
        figure.add_annotation(x=frame["vote_average"].max(), y=frame["popularity"].max(), text="Must watch", showarrow=False, xanchor="right", font={"color": "#86efac"})
        figure.add_annotation(x=frame["vote_average"].min(), y=frame["popularity"].max(), text="Overhyped?", showarrow=False, xanchor="left", font={"color": "#fda4af"})
        figure.add_annotation(x=frame["vote_average"].min(), y=frame["popularity"].min(), text="Hidden gems", showarrow=False, xanchor="left", font={"color": "#7dd3fc"})
        figure.update_traces(marker={"line": {"width": 1, "color": "#0f172a"}, "opacity": .88}); figure.update_layout(**_layout(), coloraxis_colorbar={"title": "Rating"}); figure.update_xaxes(gridcolor="#334155", zeroline=False); figure.update_yaxes(gridcolor="#334155", zeroline=False)
        st.plotly_chart(figure, width="stretch")


def render_discover(frame: pd.DataFrame, payload: dict) -> None:
    trending = frame.nsmallest(1, "trend_rank").iloc[0]
    critics, balanced = critics_pick(frame), balanced_pick(frame)
    st.markdown(f'<div class="hero"><div class="hero-kicker">TMDB weekly trends</div><h1>What should I watch tonight?</h1><p>Trending movies this week, ranked with a balance of popularity, quality, and useful detail.</p><p class="hero-meta">Snapshot: {escape(str(payload.get("snapshot_date", "Unknown")))} | {len(frame)} movies tracked</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    metrics = st.columns(4)
    metrics[0].metric("Calendar snapshot", payload.get("snapshot_date", "Unknown")); metrics[1].metric("Movies tracked", len(frame)); metrics[2].metric("Average rating", f"{frame['vote_average'].mean():.1f} / 10"); metrics[3].metric("Average popularity", f"{frame['popularity'].mean():.1f}")
    st.subheader("Three ways to choose"); st.caption("Different recommendations answer different kinds of Friday-night indecision.")
    columns = st.columns(3)
    with columns[0]: _pick_card("Trending pick", trending, "The strongest popularity signal right now.")
    with columns[1]: _pick_card("Critics pick", critics, "Highest-rated film with meaningful audience support.")
    with columns[2]: _pick_card("Balanced pick", balanced, "The best blend of popularity and rating.")
    _spotlight(balanced); _charts(frame)


def render_explorer(frame: pd.DataFrame) -> None:
    st.title("Movie explorer"); st.caption("Select a title to inspect the data behind its place in this week's ranking.")
    title = st.selectbox("Choose a movie", frame["title"].fillna("Untitled").tolist()); movie = frame[frame["title"] == title].iloc[0]
    poster_column, info_column = st.columns([1, 2])
    with poster_column: _poster(movie)
    with info_column:
        st.markdown(f"# {clean_text(movie.get('title'))}")
        stats = st.columns(3); stats[0].metric("Weekly rank", f"#{int(movie.get('trend_rank', 0))}"); stats[1].metric("Rating", f"{float(movie.get('vote_average', 0) or 0):.1f} / 10")
        runtime = movie.get("runtime"); stats[2].metric("Runtime", f"{int(runtime)} min" if pd.notna(runtime) else "Unknown")
        st.markdown(f"**Genres:** {clean_text(movie.get('genres'), 'Not available')}"); st.write(clean_text(movie.get("overview"), "No overview was supplied by TMDB."))
        if movie.get("tmdb_url"): st.link_button("Open on TMDB", str(movie["tmdb_url"]), type="primary")
    st.subheader("All movies in this snapshot")
    table = frame[["trend_rank", "title", "genres", "runtime", "vote_average", "popularity", "vote_count"]].rename(columns={"trend_rank": "Rank", "title": "Title", "genres": "Genres", "runtime": "Runtime (min)", "vote_average": "Rating", "popularity": "Popularity", "vote_count": "Votes"})
    st.dataframe(table, width="stretch", hide_index=True, height=450)


def render_historical(source: DataSource, weeks: list[dict]) -> None:
    st.title("Historical analytics"); st.caption("This section grows automatically as the scheduled pipeline stores more Friday snapshots.")
    if len(weeks) < 2:
        st.info("Only one weekly snapshot exists so far. The next successful Friday run will unlock trend lines and rank movement."); return
    frames = []
    for week in weeks[:12]:
        try:
            payload = load_snapshot(source, week); frame = payload_to_frame(payload); frame["snapshot_date"] = payload.get("snapshot_date", week.get("snapshot_date")); frames.append(frame)
        except Exception: continue
    history = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    titles = history.groupby("title")["snapshot_date"].nunique() if not history.empty else pd.Series(dtype=int)
    titles = titles[titles >= 2].index.tolist()
    if not titles:
        st.info("No movie appears in two snapshots yet, so rank movement is not available."); return
    title = st.selectbox("Track a returning movie", sorted(titles)); trend = history[history["title"] == title].sort_values("snapshot_date")
    left, right = st.columns(2)
    with left:
        figure = px.line(trend, x="snapshot_date", y="popularity", markers=True, title="Popularity over time"); figure.update_layout(**_layout()); figure.update_xaxes(gridcolor="#334155"); figure.update_yaxes(gridcolor="#334155"); st.plotly_chart(figure, width="stretch")
    with right:
        figure = go.Figure(go.Scatter(x=trend["snapshot_date"], y=trend["trend_rank"], mode="lines+markers", line={"color": "#22c55e", "width": 3})); figure.update_layout(**_layout(), title="Weekly rank movement", yaxis={"autorange": "reversed", "title": "Rank (1 is best)"}); figure.update_xaxes(gridcolor="#334155"); figure.update_yaxes(gridcolor="#334155"); st.plotly_chart(figure, width="stretch")
