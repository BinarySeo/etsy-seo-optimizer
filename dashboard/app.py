"""
app.py
------
Streamlit dashboard for Etsy SEO Optimizer.

Usage:
    python -m streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import EtsyDB
from analysis.trend_analysis import get_trending_summary, get_tag_frequency
from analysis.ai_briefing import run_briefing, get_upcoming_events

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Etsy SEO Optimizer",
    page_icon="🌿",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_resource
def get_db():
    return EtsyDB()

@st.cache_data(ttl=300)
def load_all_listings():
    db = get_db()
    return db.get_listings()

@st.cache_data(ttl=300)
def load_runs():
    db = get_db()
    return db.get_runs()

@st.cache_data(ttl=300)
def load_trend_summary():
    db = get_db()
    return get_trending_summary(db)

@st.cache_data(ttl=300)
def load_latest_briefing():
    files = glob.glob("data/processed/briefing_*.txt")
    if not files:
        return None
    latest = max(files, key=os.path.getctime)
    with open(latest, "r") as f:
        return f.read()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

upcoming = get_upcoming_events(within_days=90)

with st.sidebar:
    st.title("🌿 Etsy SEO Optimizer")
    st.caption("Handmade Card Analytics")
    st.divider()

    page = st.radio(
        "Navigate",
        ["🏠 Weekly Briefing", "📈 Trend Analysis", "🎯 SEO Optimizer", "🖼️ Reference Gallery"],
        label_visibility="collapsed"
    )

    st.divider()

    runs = load_runs()
    if not runs.empty:
        st.markdown("**Run History**")
        for _, run in runs.iterrows():
            st.caption(f"📅 {run['run_date']} — {run['total_rows']} listings analyzed")

    st.divider()

    if upcoming:
        st.markdown("**Upcoming Events**")
        for event in upcoming[:3]:
            st.info(f"🗓️ {event['name']} — in {event['days_away']} days")

# ---------------------------------------------------------------------------
# Page: Weekly Briefing
# ---------------------------------------------------------------------------

if page == "🏠 Weekly Briefing":
    st.title("🏠 Weekly Briefing")

    df_all = load_all_listings()
    summary = load_trend_summary()

    if df_all.empty:
        st.warning("No data found. Run `python -m scraper.mock_data` first.")
        st.stop()

    latest_run = df_all["run_date"].max()
    df_latest = df_all[df_all["run_date"] == latest_run]
    new_tags_count = len(summary.get("new_tags", [])) if summary else 0
    next_event = upcoming[0] if upcoming else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Listings Analyzed", f"{len(df_latest):,}")
    col2.metric("Avg Favorites", f"{df_latest['num_favorers'].mean():.0f}")
    col3.metric("New Keywords This Week", new_tags_count)
    col4.metric(
        "Next Big Event",
        next_event["name"] if next_event else "—",
        delta=f"in {next_event['days_away']} days" if next_event else None
    )

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🤖 AI Weekly Briefing")
        briefing = load_latest_briefing()
        if briefing:
            st.markdown(briefing)
        else:
            st.info("No briefing generated yet.")
            if st.button("Generate This Week's Briefing"):
                with st.spinner("Analyzing trends with GPT..."):
                    briefing = run_briefing()
                    st.cache_data.clear()
                    st.rerun()

    with col_right:
        st.subheader("🔥 Trending Up This Week")
        if summary and not summary["rising"].empty:
            rising = summary["rising"].head(8).copy()
            rising = rising.rename(columns={
                "tag": "Keyword",
                "delta": "Gained listings"
            })
            fig = px.bar(
                rising,
                x="Gained listings",
                y="Keyword",
                orientation="h",
                color="Gained listings",
                color_continuous_scale="reds",
            )
            fig.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=0, b=0),
                height=280,
            )
            fig.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("✨ Brand New Keywords")
        if summary and summary["new_tags"]:
            st.write(" · ".join([f"`{tag}`" for tag in summary["new_tags"]]))
        else:
            st.caption("No brand new keywords this week.")

# ---------------------------------------------------------------------------
# Page: Trend Analysis
# ---------------------------------------------------------------------------

elif page == "📈 Trend Analysis":
    st.title("📈 Trend Analysis")
    st.caption("See how keywords are rising or falling week over week")

    df_all = load_all_listings()
    summary = load_trend_summary()

    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    run_dates = sorted(df_all["run_date"].unique())

    records = []
    for run_date in run_dates:
        df_run = df_all[df_all["run_date"] == run_date]
        freq = get_tag_frequency(df_run, top_n=20)
        for _, row in freq.iterrows():
            records.append({
                "run_date": run_date,
                "tag": row["tag"],
                "count": row["count"],
            })

    df_trend = pd.DataFrame(records)
    all_tags = df_trend["tag"].unique().tolist()
    default_tags = [t for t in summary["rising"]["tag"].head(5).tolist() if t in all_tags] if summary else all_tags[:5]

    selected_tags = st.multiselect(
        "Select keywords to track",
        options=all_tags,
        default=default_tags
    )

    if selected_tags:
        df_filtered = df_trend[df_trend["tag"].isin(selected_tags)]
        fig = px.line(
            df_filtered,
            x="run_date", y="count", color="tag",
            markers=True,
            labels={
                "run_date": "Week",
                "count": "Number of listings using this keyword",
                "tag": "Keyword",
            },
            title="Keyword usage over time",
        )
        fig.update_layout(height=400, legend_title="Keyword")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    if summary:
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("🔥 Rising This Week")
            st.caption("These keywords are being used more than last week")
            rising = summary["rising"].copy()
            rising = rising.rename(columns={
                "tag": "Keyword",
                "count_this": "This Week",
                "count_last": "Last Week",
                "delta": "Change",
            })
            fig_r = px.bar(
                rising[["Keyword", "Change"]],
                x="Change", y="Keyword",
                orientation="h",
                color="Change",
                color_continuous_scale="reds",
                labels={"Change": "Listings gained"},
            )
            fig_r.update_layout(
                height=320, showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=0, b=0),
            )
            fig_r.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_r, use_container_width=True)

        with col_r:
            st.subheader("📉 Losing Steam")
            st.caption("These keywords are being used less than last week")
            falling = summary["falling"].copy()
            falling = falling.rename(columns={
                "tag": "Keyword",
                "count_this": "This Week",
                "count_last": "Last Week",
                "delta": "Change",
            })
            fig_f = px.bar(
                falling[["Keyword", "Change"]],
                x="Change", y="Keyword",
                orientation="h",
                color="Change",
                color_continuous_scale="blues",
                labels={"Change": "Listings lost"},
            )
            fig_f.update_layout(
                height=320, showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=0, b=0),
            )
            fig_f.update_yaxes(categoryorder="total ascending", title="")
            st.plotly_chart(fig_f, use_container_width=True)

# ---------------------------------------------------------------------------
# Page: SEO Optimizer
# ---------------------------------------------------------------------------

elif page == "🎯 SEO Optimizer":
    st.title("🎯 SEO Optimizer")
    st.caption("Find the best keywords to add to your listings right now")

    df_all = load_all_listings()
    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    latest_run = df_all["run_date"].max()
    df_latest = df_all[df_all["run_date"] == latest_run]

    freq = get_tag_frequency(df_latest, top_n=50)
    freq["recommendation_score"] = (
        freq["count"] / freq["count"].max() * 100
    ).round(1)
    freq["how_competitive"] = freq["count"].apply(
        lambda x: "🔴 Very competitive" if x > 100 else (
            "🟡 Moderately competitive" if x > 60 else "🟢 Less competitive"
        )
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📊 Keyword Recommendation Map")
        st.caption("Bigger bubble = used by more listings. Higher = stronger recommendation.")
        display_df = freq.head(30).rename(columns={
            "tag": "Keyword",
            "count": "Used by listings",
            "recommendation_score": "Recommendation Score",
        })
        fig = px.scatter(
            display_df,
            x="Used by listings",
            y="Recommendation Score",
            text="Keyword",
            size="Used by listings",
            color="Recommendation Score",
            color_continuous_scale="oranges",
        )
        fig.update_traces(textposition="top center", textfont_size=9)
        fig.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏷️ Top 13 Tags to Use Now")
        st.caption("Etsy allows 13 tags per listing. Copy and paste these:")
        top_tags = freq.head(13)["tag"].tolist()
        st.code(", ".join(top_tags), language=None)

    st.divider()
    st.subheader("📋 Full Keyword Table")
    display_full = freq.rename(columns={
        "tag": "Keyword",
        "count": "Used by # listings",
        "pct": "% of listings",
        "how_competitive": "Competition Level",
        "recommendation_score": "Recommendation Score",
    })
    st.dataframe(
        display_full[["Keyword", "Used by # listings", "% of listings", "Competition Level", "Recommendation Score"]],
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Page: Reference Gallery
# ---------------------------------------------------------------------------

elif page == "🖼️ Reference Gallery":
    st.title("🖼️ Reference Gallery")
    st.caption("Browse top performing listings for design inspiration")

    df_all = load_all_listings()
    if df_all.empty:
        st.warning("No data found.")
        st.stop()

    latest_run = df_all["run_date"].max()
    df_latest = df_all[df_all["run_date"] == latest_run].copy()
    df_latest["saves_per_view"] = (
        df_latest["num_favorers"] / df_latest["views"].replace(0, 1)
    ).round(4)

    col1, col2, col3 = st.columns(3)
    with col1:
        query_filter = st.selectbox(
            "Filter by search term",
            ["All"] + list(df_latest["query"].unique())
        )
    with col2:
        sort_options = {
            "num_favorers": "Most Favorited",
            "saves_per_view": "Best Conversion",
            "views": "Most Viewed",
            "price_usd": "Price",
        }
        sort_by = st.selectbox("Sort by", options=list(sort_options.keys()), format_func=lambda x: sort_options[x])
    with col3:
        top_n = st.slider("How many to show", 10, 50, 20)

    df_gallery = df_latest.copy()
    if query_filter != "All":
        df_gallery = df_gallery[df_gallery["query"] == query_filter]
    df_gallery = df_gallery.sort_values(sort_by, ascending=False).head(top_n)

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Favorites", f"{df_gallery['num_favorers'].mean():.0f}")
    col2.metric("Avg Saves per View", f"{df_gallery['saves_per_view'].mean():.3f}")
    col3.metric("Avg Price", f"${df_gallery['price_usd'].mean():.2f}")

    st.divider()

    display_gallery = df_gallery.rename(columns={
        "title": "Title",
        "price_usd": "Price ($)",
        "num_favorers": "Favorites",
        "views": "Views",
        "saves_per_view": "Saves per View",
        "tags": "Tags",
        "url": "Link",
    })
    st.dataframe(
        display_gallery[["Title", "Price ($)", "Favorites", "Views", "Saves per View", "Tags", "Link"]],
        use_container_width=True,
        hide_index=True,
    )