from analysis.trend_analysis import compare_weeks, get_new_tags, get_tag_frequency, split_tags


def test_split_tags_cleans_case_spaces_and_blanks():
    assert split_tags(" Birthday Card, FUNNY ,, ") == ["birthday card", "funny"]


def test_tag_frequency_counts_and_pct(listings):
    df = listings(["a, b", "a", "a, c"])
    freq = get_tag_frequency(df, top_n=None).set_index("tag")
    assert freq.loc["a", "count"] == 3
    assert freq.loc["a", "pct"] == 100.0
    assert freq.loc["b", "pct"] == 33.3


def test_compare_weeks_flags_rising_and_falling(listings):
    last = listings(["old"] * 10 + ["steady"] * 10)
    this = listings(["new"] * 10 + ["steady"] * 10)
    result = compare_weeks(this, last).set_index("tag")
    assert result.loc["new", "trend"] == "🔥 rising"
    assert result.loc["old", "trend"] == "📉 falling"
    assert result.loc["steady", "trend"] == "➡️ stable"


def test_compare_weeks_uses_full_counts_not_top_50(listings):
    # 60 filler tags outrank "edge" both weeks, pushing it outside a top-50 cut-off.
    # Its count is unchanged, so it must not be reported as rising or falling.
    filler = ", ".join(f"filler{i}" for i in range(60))
    week = listings([filler] * 20 + ["edge"] * 10)
    result = compare_weeks(week, week, top_n=200).set_index("tag")
    assert result.loc["edge", "delta"] == 0
    assert result.loc["edge", "trend"] == "➡️ stable"


def test_get_new_tags(listings):
    assert get_new_tags(listings(["a, b"]), listings(["a"])) == ["b"]
