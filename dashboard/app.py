"""
app.py
------
Streamlit dashboard for Etsy SEO Optimizer.
Visualizes tag trends, TF-IDF keywords, and SEO gap analysis.

Usage:
    streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Etsy SEO Optimizer",
    page_icon="🛍️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_data
def load_raw_data() -> pd.DataFrame:
    files = glob.glob("data/raw/*.csv")
    if not files:
        return pd.DataFrame()
    latest = max(files, key=os.path.getctime)
    return pd.read_csv(latest)


@st.cache_data
def load_processed(name: str) -> pd.DataFrame:
    files = glob.glob(f"data/processed/{name}_*.csv")
    if not files:
        return pd.DataFrame()
    latest = max(files, key=os.path.getctime)
    return pd.read_csv(latest)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Etsy SEO Optimizer")
st.sidebar.markdown("Analyze greeting card trends and optimize your shop tags.")

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Tag Trends", "TF-IDF Keywords", "SEO Gap Analysis", "Reference Gallery"]
)

df_raw = load_raw_data()
df_tags = load_processed("tag_frequency")
df_tfidf = load_processed("tfidf_keywords")
df_gap = load_processed("seo_gap")

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

if page == "Overview":
    st.title("Etsy SEO Optimizer")
    st.markdown("### Dashboard Overview")

    if df_raw.empty:
        st.warning("No data found. Run the scraper or mock data generator first.")
    else:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Listings", len(df_raw))
        col2.metric("Unique Queries", df_raw["query"].nunique())
        col3.metric(
            "Avg Favorites",
            f"{df_raw['num_favorers'].mean():.0f}"
        )
        col4.metric(
            "Avg Price",
            f"${df_raw['price_usd'].mean():.2f}"
        )

        st.markdown("---")

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("#### Listings per query")
            query_counts = df_raw["query"].value_counts().reset_index()
            query_counts.columns = ["query", "count"]
            fig = px.bar(
                query_counts, x="query", y="count",
                color="count", color_continuous_scale="teal",
            )
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### Price distribution")
            fig2 = px.histogram(
                df_raw, x="price_usd", nbins=30,
                color_discrete_sequence=["#1D9E75"],
            )
            st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Tag Trends
# ---------------------------------------------------------------------------

elif page == "Tag Trends":
    st.title("Tag Trends")
    st.markdown("Most frequently used tags across all listings.")

    if df_tags.empty:
        st.warning("No tag data found. Run keyword analysis first.")
    else:
        top_n = st.slider("Show top N tags", 10, 30, 20)
        df_show = df_tags.head(top_n)

        fig = px.bar(
            df_show, x="count", y="tag",
            orientation="h",
            color="count",
            color_continuous_scale="teal",
            labels={"count": "Listings using this tag", "tag": ""},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Raw data")
        st.dataframe(df_show, use_container_width=True)

# ---------------------------------------------------------------------------
# TF-IDF Keywords
# ---------------------------------------------------------------------------

elif page == "TF-IDF Keywords":
    st.title("TF-IDF Keywords")
    st.markdown(
        "Keywords extracted from listing **titles** using TF-IDF. "
        "High score = distinctive and frequently used."
    )

    if df_tfidf.empty:
        st.warning("No TF-IDF data found. Run keyword analysis first.")
    else:
        fig = px.bar(
            df_tfidf, x="tfidf_score", y="keyword",
            orientation="h",
            color="tfidf_score",
            color_continuous_scale="purples",
            labels={"tfidf_score": "TF-IDF Score", "keyword": ""},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Raw data")
        st.dataframe(df_tfidf, use_container_width=True)

# ---------------------------------------------------------------------------
# SEO Gap Analysis
# ---------------------------------------------------------------------------

elif page == "SEO Gap Analysis":
    st.title("SEO Gap Analysis")
    st.markdown("Compare trending tags against your current shop tags.")

    if df_gap.empty:
        st.warning("No gap analysis data found. Run keyword analysis first.")
    else:
        missing = df_gap[df_gap["status"].str.contains("missing")]
        using = df_gap[df_gap["status"].str.contains("already")]

        col1, col2 = st.columns(2)
        col1.metric("Tags you're missing", len(missing), delta=f"-{len(missing)} opportunities")
        col2.metric("Tags already using", len(using))

        st.markdown("---")
        st.markdown("#### Missing high-value tags — consider adding these")
        fig = px.bar(
            missing.head(20), x="count", y="tag",
            orientation="h",
            color="count",
            color_continuous_scale="reds",
            labels={"count": "Used by competitors", "tag": ""},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Full gap table")
        st.dataframe(df_gap, use_container_width=True)

# ---------------------------------------------------------------------------
# Reference Gallery
# ---------------------------------------------------------------------------

elif page == "Reference Gallery":
    st.title("Reference Gallery")
    st.markdown("Top performing listings — browse for design inspiration.")

    if df_raw.empty:
        st.warning("No listing data found.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            query_filter = st.selectbox(
                "Filter by query",
                ["All"] + list(df_raw["query"].unique())
            )
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["num_favorers", "views", "price_usd"]
            )

        df_gallery = df_raw.copy()
        if query_filter != "All":
            df_gallery = df_gallery[df_gallery["query"] == query_filter]

        df_gallery = df_gallery.sort_values(sort_by, ascending=False).head(50)

        for _, row in df_gallery.iterrows():
            with st.expander(f"{row['title']} — {row['num_favorers']} favorites"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Price", f"${row['price_usd']}")
                c2.metric("Favorites", row["num_favorers"])
                c3.metric("Views", row["views"])
                st.markdown(f"**Tags:** {row['tags']}")
                st.markdown(f"[View on Etsy]({row['url']})")