import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_autorefresh import st_autorefresh

SUPABASE_URL = st.secrets["https://fesljajdsbxodzrlqnno.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlc2xqYWpkc2J4b2R6cmxxbm5vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwMTkxNjgsImV4cCI6MjA4ODU5NTE2OH0.iR8ilbhRwhPTVi0fo6KgGlFPVrupS8b-1RHE6nf01c0"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Operation Handbasket", layout="wide")

st.title("🔥 Operation Handbasket")
st.caption("Real-Time +EV Betting Scanner")

# Auto refresh every 15 seconds
st_autorefresh(interval=15000, key="refresh")

data = (
    supabase.table("edge_candidates")
    .select("*")
    .order("created_at", desc=True)
    .limit(2000)
    .execute()
)

df = pd.DataFrame(data.data)

if not df.empty:
    numeric_cols = [
        "american_odds",
        "win_probability",
        "implied_probability",
        "edge_percent",
        "expected_value"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    st.sidebar.header("Filters")

    # Sport checkboxes
    sport_options = sorted(df["sport"].dropna().unique().tolist())
    select_all_sports = st.sidebar.checkbox("Select All Sports", value=True)

    selected_sports = []
    for sport in sport_options:
        if st.sidebar.checkbox(
            sport,
            value=select_all_sports,
            key=f"sport_checkbox_{sport}"
        ):
            selected_sports.append(sport)

    # Sportsbook checkboxes
    st.sidebar.markdown("---")

    book_options = sorted(df["sportsbook"].dropna().unique().tolist())
    select_all_books = st.sidebar.checkbox("Select All Sportsbooks", value=True)

    selected_books = []
    for book in book_options:
        if st.sidebar.checkbox(
            book,
            value=select_all_books,
            key=f"book_checkbox_{book}"
        ):
            selected_books.append(book)

    # Other filters
    st.sidebar.markdown("---")

    only_qualifies = st.sidebar.checkbox("Only qualifying bets", value=True)

    min_ev = st.sidebar.slider(
        "Minimum EV",
        min_value=0.0,
        max_value=0.20,
        value=0.01,
        step=0.005
    )

    filtered_df = df.copy()

    if selected_sports:
        filtered_df = filtered_df[filtered_df["sport"].isin(selected_sports)]
    else:
        filtered_df = filtered_df.iloc[0:0]

    if selected_books:
        filtered_df = filtered_df[filtered_df["sportsbook"].isin(selected_books)]
    else:
        filtered_df = filtered_df.iloc[0:0]

    if only_qualifies and "qualifies" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["qualifies"] == True]

    if "expected_value" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["expected_value"] >= min_ev]
        filtered_df = filtered_df.sort_values("expected_value", ascending=False)

    columns_to_show = [
        "sport",
        "away_team",
        "home_team",
        "team",
        "sportsbook",
        "american_odds",
        "edge_percent",
        "expected_value",
        "created_at"
    ]

    existing_columns = [c for c in columns_to_show if c in filtered_df.columns]
    display_df = filtered_df[existing_columns].copy()

    if "expected_value" in display_df.columns:
        display_df["expected_value"] = display_df["expected_value"].round(4)

    if "edge_percent" in display_df.columns:
        display_df["edge_percent"] = display_df["edge_percent"].round(4)

    st.subheader("⭐ Top 10 Best Bets")
    top_10 = display_df.head(10)
    st.dataframe(top_10, use_container_width=True)

    def highlight_ev(val):
        if pd.isna(val):
            return ""
        if val >= 0.08:
            return "background-color:#00aa55;color:white;font-weight:bold"
        elif val >= 0.05:
            return "background-color:#66dd99"
        elif val >= 0.03:
            return "background-color:#c9f7d8"
        return ""

    styled_df = (
        display_df.style.map(highlight_ev, subset=["expected_value"])
        if "expected_value" in display_df.columns
        else display_df
    )

    st.subheader("All Filtered Bets")
    st.dataframe(styled_df, use_container_width=True)

    st.write(f"Showing {len(display_df)} bets")

else:
    st.info("No bets found yet. The scanner may still be running.")
