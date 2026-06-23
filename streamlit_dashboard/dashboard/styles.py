import streamlit as st


def apply_styles() -> None:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 88% 3%,rgba(34,197,94,.15),transparent 26rem),radial-gradient(circle at 9% 18%,rgba(56,189,248,.1),transparent 24rem),#0f172a; color:#f8fafc; }
    [data-testid="stHeader"] { background:rgba(15,23,42,.78); } [data-testid="stSidebar"] { background:#111c31; } [data-testid="stSidebar"] * { color:#f8fafc!important; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,[data-testid="stSidebar"] input { background:#1e293b!important;border-color:#475569!important; }
    [data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label { color:#f8fafc; }
    [data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3 { font-family:Georgia,'Times New Roman',serif;letter-spacing:-.02em; }
    [data-testid="stMetric"],[data-testid="stPlotlyChart"],.pick-card,.empty-poster { background:#1e293b;border:1px solid #334155;border-radius:16px;box-shadow:0 12px 25px rgba(0,0,0,.15); }
    [data-testid="stMetric"] { padding:1rem; } [data-testid="stMetricLabel"] p { color:#94a3b8!important;font-size:.78rem!important; } [data-testid="stMetricValue"] { color:#f8fafc!important; }
    [data-testid="stPlotlyChart"] { padding:.45rem; }
    .hero { overflow:hidden;padding:2.6rem;border:1px solid #334155;border-radius:24px;background:radial-gradient(circle at 92% 14%,rgba(34,197,94,.36) 0 2rem,transparent 2.1rem),radial-gradient(circle at 86% 27%,rgba(34,197,94,.16) 0 5rem,transparent 5.1rem),linear-gradient(120deg,#172554,#0f3b35 68%,#12312b);box-shadow:0 22px 45px rgba(0,0,0,.25); }
    .hero-kicker,.pick-kicker { color:#86efac!important;font-size:.76rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase; } .hero h1 { color:#fff!important;font-size:clamp(2.4rem,5vw,4.3rem)!important;margin:.45rem 0!important; } .hero p { color:#dbeafe!important; } .hero-meta { color:#bbf7d0!important;font-weight:700; }
    .section-gap { height:.9rem; } .pick-card { padding:1.1rem;min-height:11.8rem; } .pick-card h3 { color:#fff!important;margin:.55rem 0 .3rem!important;font-size:1.36rem!important; } .muted { color:#a8b5c8!important; }
    .empty-poster { aspect-ratio:2/3;min-height:260px;display:flex;align-items:end;padding:1.1rem;background:linear-gradient(155deg,#14532d,#172554 62%,#0f172a);color:#fff!important;font-family:Georgia,serif;font-size:1.4rem;font-weight:700; }
    .rank-badge { display:inline-block;background:#22c55e;color:#06220f!important;border-radius:999px;padding:.2rem .6rem;font-size:.82rem;font-weight:800; } [data-testid="stLinkButton"] { margin-top:.55rem; } [data-testid="stLinkButton"] a { background:#22c55e!important;color:#06220f!important;border:0!important;font-weight:800!important; }
    </style>
    """, unsafe_allow_html=True)
