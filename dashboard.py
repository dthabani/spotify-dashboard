# Spotify Dashboard
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

# --- LOAD ENV VARIABLES ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# --- CONNECT TO MONGO ---
client = MongoClient(MONGO_URI)
db = client["spotify"]
collection = db["songs"]

# --- HELPER FUNCTIONS ---
def format_seconds_to_hms(total_seconds):
    total_seconds = int(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_number_with_space(num):
    try:
        return f"{int(num):,}".replace(",", " ")
    except Exception:
        return str(num)


def duration_to_seconds(duration_str):
    if not isinstance(duration_str, str):
        return 0
    parts = duration_str.split(":")
    if len(parts) == 2:
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except ValueError:
            return 0
    return 0


def extract_artists_list(row):
    """
    Extract a list of artist names from a record.
    Handles multiple formats:
      - 'artists': list of dicts with "name"
      - 'artists': list of strings
      - 'artist': single string (old schema)
      - fall back to 'album'
    Always returns a non-empty list of strings.
    """
    artists = []

    # Preferred: 'artists' list
    raw_artists = row.get("artists")
    if isinstance(raw_artists, list) and len(raw_artists) > 0:
        for item in raw_artists:
            if isinstance(item, dict) and "name" in item:
                name = item["name"]
                if name and str(name).strip():
                    artists.append(str(name).strip())
            elif isinstance(item, str) and item.strip():
                artists.append(item.strip())

    # Fallback: single 'artist' string (old schema)
    if not artists:
        artist = row.get("artist")
        if isinstance(artist, str) and artist.strip():
            artists.append(artist.strip())

    # Fallback: 'album' as a pseudo-artist
    if not artists:
        album = row.get("album")
        if isinstance(album, str) and album.strip():
            artists.append(album.strip())

    return artists if artists else ["Unknown Artist"]


# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Spotify Dashboard", layout="wide")

# --- CUSTOM CSS FOR LIGHT THEME ---
st.markdown(
    """
    <style>
    /* General */
    .main {
        background-color: #fff;
        color: #111;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        padding: 1rem 2rem 2rem 2rem;
    }
    /* Sidebar */
    .css-1d391kg, .st-emotion-cache-1d391kg, .st-emotion-cache-1v0mbdj, .st-emotion-cache-6qob1r, .st-emotion-cache-1v0mbdj {
        background-color: #fff !important;
        color: #111 !important;
    }
    /* Accent color */
    .css-1d391kg .st-cx, .st-emotion-cache-1d391kg .st-cx {
        color: #4CAF50 !important;
    }
    /* Sidebar header */
    .css-1d391kg .css-1v0mbdj, .st-emotion-cache-1d391kg .st-emotion-cache-1v0mbdj {
        color: #4CAF50 !important;
        font-weight: 700;
        font-size: 1.2rem;
    }
    /* Dropdowns */
    div[data-baseweb="select"] > div {
        background-color: #fff !important;
        color: #111 !important;
        border-color: #4CAF50 !important;
    }
    /* Buttons */
    button[kind="secondary"], .stButton > button {
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        font-weight: 500;
    }
    button[kind="secondary"]:hover, .stButton > button:hover {
        background-color: #81c784 !important;
        color: #111 !important;
    }
    /* Dataframe */
    .stDataFrame > div {
        background-color: #fff !important;
        color: #111 !important;
    }
    /* Table headers */
    .stDataFrame thead tr th {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    /* Metric labels */
    .stMetric label {
        color: #111 !important;
    }
    /* Divider */
    hr {
        border-color: #4CAF50 !important;
    }
    /* Tabs */
    .css-1f0n5f7, .st-emotion-cache-1f0n5f7 {
        background-color: #fff !important;
        color: #111 !important;
    }
    .css-1f0n5f7 button[aria-selected="true"], .st-emotion-cache-1f0n5f7 button[aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: 700;
    }
    /* Plotly hover label */
    .js-plotly-plot .hoverlayer .hovertext {
        background-color: #4CAF50 !important;
        color: white !important;
        border-radius: 5px !important;
    }
    /* Custom table styling for All Songs */
    .dataframe-container {
        background-color: #fff;
        color: #111;
        border: 1px solid #4CAF50;
        border-radius: 5px;
        padding: 0.5rem;
        max-height: 450px;
        overflow-y: auto;
    }
    .dataframe-container table {
        width: 100%;
        border-collapse: collapse;
    }
    .dataframe-container th {
        background-color: #4CAF50;
        color: white;
        padding: 8px;
        position: sticky;
        top: 0;
        z-index: 1;
        text-align: left;
    }
    .dataframe-container td {
        padding: 8px;
        border-bottom: 1px solid #e0e0e0;
    }
    .dataframe-container tr:hover {
        background-color: #e8f5e9;
    }
    /* Remove black backgrounds from all tabs and containers */
    .stTabs, .stTab, .st-emotion-cache-1f0n5f7, .st-emotion-cache-1d391kg {
        background-color: #fff !important;
        color: #111 !important;
    }
    /* Disabled dropdown styling */
    div[data-baseweb="select"][aria-disabled="true"] > div {
        border-color: #e0e0e0 !important;
        background-color: #f0f0f0 !important;
        color: #a0a0a0 !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
        pointer-events: none !important;
    }
    div[data-baseweb="select"][aria-disabled="true"] * {
        color: #a0a0a0 !important;
        fill: #a0a0a0 !important;
    }
    div[data-baseweb="select"][aria-disabled="true"]:hover > div {
        border-color: #e0e0e0 !important;
        background-color: #f0f0f0 !important;
    }
    div[data-baseweb="select"][aria-disabled="true"] svg {
        opacity: 0.3 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- SIDEBAR ---
st.sidebar.markdown("## Spotify Dashboard")
months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

sidebar_month_index = datetime.now().month - 1
start_year = 2024
current_year = datetime.now().year
sidebar_year_list = list(range(start_year, current_year + 1))[::-1]
selected_month = None
selected_year = None

# --- SIDEBAR CONTROLS ---
view_mode = st.sidebar.selectbox(
    "View Mode", ["All Time", "By Year", "By Month"], key="view_mode_main"
)
selected_year = st.sidebar.selectbox(
    "Select Year",
    sidebar_year_list,
    index=0,
    key="year_select_main",
    disabled=(view_mode == "All Time"),
)

# --- FETCH DATA ---
data = list(collection.find())

if not data:
    st.warning("No data found in MongoDB. Make sure your Lambda has inserted documents.")
    df = pd.DataFrame()
else:
    df = pd.DataFrame(data)

# --- NORMALIZE & CLEAN ---
if not df.empty:
    # played_at
    if "played_at" in df.columns:
        df["played_at"] = pd.to_datetime(df["played_at"], errors="coerce")

    # track_name
    if "title" in df.columns:
        df.rename(columns={"title": "track_name"}, inplace=True)

    # artists list
    df["artists"] = df.apply(extract_artists_list, axis=1)
    # also keep a display string for UI / sorting
    df["artist_display"] = df["artists"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else str(x)
    )

    # played duration
    if "time_taken" in df.columns and not df["time_taken"].isnull().all():
        df["played_duration_sec"] = df["time_taken"].apply(duration_to_seconds)
    else:
        df["played_duration_sec"] = 0
    df["played_duration_sec"] = pd.to_numeric(
        df["played_duration_sec"], errors="coerce"
    ).fillna(0)

    # --- DYNAMIC YEAR LIST AND FILTERING BASED ON VIEW MODE ---
    if "played_at" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["played_at"]):
            df["played_at"] = pd.to_datetime(df["played_at"], errors="coerce")

        valid_years = sorted(df["played_at"].dropna().dt.year.unique())
        if len(valid_years) > 0:
            sidebar_year_list = valid_years[::-1]
        else:
            selected_year = current_year
            selected_month = months[sidebar_month_index]

        df = df.sort_values("played_at", ascending=False)

        # Month selection control
        if view_mode == "By Month":
            try:
                month_number = months.index(months[sidebar_month_index]) + 1
            except Exception:
                month_number = None

            if selected_month is None:
                selected_month = months[sidebar_month_index]

            if selected_year == 2024:
                months_available = ["December"]
            else:
                months_available = months

            if selected_year == 2024:
                default_month_index = months_available.index("December")
            else:
                default_month_index = (
                    sidebar_month_index
                    if sidebar_month_index < len(months_available)
                    else 0
                )

            selected_month = st.sidebar.selectbox(
                "Select Month",
                months_available,
                index=default_month_index,
                key="month_select_main",
                disabled=(view_mode in ["All Time", "By Year"]),
            )
        else:
            selected_month = st.sidebar.selectbox(
                "Select Month",
                months,
                index=sidebar_month_index,
                key="month_select_main",
                disabled=True,
            )

        # Apply filters
        if view_mode == "All Time":
            filtered_df = df.copy()
            if filtered_df.empty:
                st.warning("No data found for all time.")
            else:
                st.success(f"Showing all available data ({len(filtered_df)} songs total).")

        elif view_mode == "By Year":
            filtered_df = df[df["played_at"].dt.year == selected_year]
            if filtered_df.empty:
                st.warning(f"No data found for {selected_year}.")
                filtered_df = pd.DataFrame(columns=df.columns)
            else:
                st.success(
                    f"Showing data for {selected_year} with {len(filtered_df)} songs."
                )

        elif view_mode == "By Month":
            try:
                month_number = months.index(selected_month) + 1
            except Exception:
                month_number = None

            if selected_year == 2024:
                months_available = ["December"]
            else:
                months_available = months

            if month_number is not None:
                filtered_df = df[
                    (df["played_at"].dt.year == selected_year)
                    & (df["played_at"].dt.month == month_number)
                ]
            else:
                filtered_df = pd.DataFrame(columns=df.columns)

            if filtered_df.empty:
                st.warning(f"No data found for {selected_month} {selected_year}.")
                filtered_df = pd.DataFrame(columns=df.columns)
            else:
                st.success(
                    f"Showing data for {selected_month} {selected_year} with {len(filtered_df)} songs."
                )

        else:
            filtered_df = pd.DataFrame(columns=df.columns)

        df = filtered_df

    else:
        st.warning("No 'played_at' column found in dataset.")
        df = pd.DataFrame()

# --- TABS ---
tabs = st.tabs(
    ["Overview", "Top Artists", "Top Songs", "All Songs", "Visualisations"]
)

# --- OVERVIEW TAB ---
with tabs[0]:
    st.markdown("#### Overview Metrics")

    if df.empty:
        st.info("No data available for the current selection.")
    else:
        total_seconds = df.get(
            "played_duration_sec", pd.Series(dtype=float)
        ).sum()
        total_songs_val = len(df)

        # Unique artists from list column
        unique_artists = set()
        if "artists" in df.columns:
            for artists_list in df["artists"]:
                if isinstance(artists_list, list):
                    unique_artists.update(artists_list)
        total_artists_val = len(unique_artists)

        total_minutes = format_seconds_to_hms(total_seconds)
        total_songs = format_number_with_space(total_songs_val)
        total_artists = format_number_with_space(total_artists_val)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Listening Time", total_minutes)
        c2.metric("Total Songs Played", total_songs)
        c3.metric("Total Artists", total_artists)
        st.divider()

# --- TOP ARTISTS TAB ---
with tabs[1]:
    st.markdown("### Top 10 Artists")

    if df.empty or "artists" not in df.columns:
        if view_mode == "All Time":
            st.info("No artist data available for all time.")
        elif view_mode == "By Year":
            st.info("No artist data available for the selected year.")
        elif view_mode == "By Month":
            st.info("No artist data available for the selected month.")
    else:
        if "played_duration_sec" not in df.columns:
            df["played_duration_sec"] = 0
        df["played_duration_sec"] = pd.to_numeric(
            df["played_duration_sec"], errors="coerce"
        ).fillna(0)

        # Explode so each artist gets full credit for each play
        df_exploded = df.explode("artists", ignore_index=False).reset_index(drop=True)

        grouped = (
            df_exploded.groupby("artists", dropna=False)
            .agg(
                Play_Count=("artists", "count"),
                Total_Minutes=(
                    "played_duration_sec",
                    lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()
                    / 60,
                ),
            )
            .reset_index()
        )

        grouped = grouped.sort_values("Play_Count", ascending=False).head(10)
        grouped["Artist"] = grouped["artists"].astype(str).str.title()
        grouped["Formatted_Time"] = grouped["Total_Minutes"].apply(
            lambda x: format_seconds_to_hms(x * 60)
        )
        display_df = grouped[
            ["Artist", "Play_Count", "Formatted_Time"]
        ].rename(
            columns={
                "Play_Count": "Play Count",
                "Formatted_Time": "Total Listening Time",
            }
        )

        def render_table(dataframe):
            table_html = '<div class="dataframe-container"><table><thead><tr>'
            for col in dataframe.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr></thead><tbody>"
            for _, row in dataframe.iterrows():
                table_html += "<tr>"
                for col in dataframe.columns:
                    cell = row[col]
                    table_html += f"<td>{str(cell)}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

        render_table(display_df)

# --- TOP SONGS TAB ---
with tabs[2]:
    st.markdown("### Top 10 Songs")

    if df.empty or "track_name" not in df.columns:
        if view_mode == "All Time":
            st.info("No song data available for all time.")
        elif view_mode == "By Year":
            st.info("No song data available for the selected year.")
        elif view_mode == "By Month":
            st.info("No song data available for the selected month.")
    else:
        if "played_duration_sec" not in df.columns:
            df["played_duration_sec"] = 0
        df["played_duration_sec"] = pd.to_numeric(
            df["played_duration_sec"], errors="coerce"
        ).fillna(0)

        # Group by track_name + artist_display so songs
        # with same title but different artists are separated.
        grouped = (
            df.groupby(["track_name", "artist_display"], dropna=False)
            .agg(
                Play_Count=("track_name", "count"),
                Total_Minutes=(
                    "played_duration_sec",
                    lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()
                    / 60,
                ),
            )
            .reset_index()
        )

        grouped = grouped.sort_values(
            ["Play_Count", "Total_Minutes"], ascending=[False, False]
        ).head(10)

        grouped["Song"] = grouped["track_name"].astype(str)
        grouped["Artist(s)"] = grouped["artist_display"].astype(str)
        grouped["Formatted_Time"] = grouped["Total_Minutes"].apply(
            lambda x: format_seconds_to_hms(x * 60)
        )

        display_df = grouped[
            ["Song", "Artist(s)", "Play_Count", "Formatted_Time"]
        ].rename(
            columns={
                "Play_Count": "Play Count",
                "Formatted_Time": "Total Listening Time",
            }
        )

        def render_table(dataframe):
            table_html = '<div class="dataframe-container"><table><thead><tr>'
            for col in dataframe.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr></thead><tbody>"
            for _, row in dataframe.iterrows():
                table_html += "<tr>"
                for col in dataframe.columns:
                    cell = row[col]
                    table_html += f"<td>{str(cell)}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

        render_table(display_df)

# --- ALL SONGS TAB ---
with tabs[3]:
    st.markdown("### All Songs")

    filtered_all_songs_df = df.copy()

    if filtered_all_songs_df.empty:
        if view_mode == "All Time":
            st.info("No song data available for all time.")
        elif view_mode == "By Year":
            st.info("No song data available for the selected year.")
        elif view_mode == "By Month":
            st.info("No song data available for the selected month.")
    else:
        MAX_ROWS = 200
        INITIAL_ROWS = 50

        sort_by_options = ["played_at", "track_name", "artist_display"]
        sort_by_labels = {
            "played_at": "Played At",
            "track_name": "Title",
            "artist_display": "Artist",
        }

        if "all_songs_sort_by" not in st.session_state:
            st.session_state["all_songs_sort_by"] = "played_at"
        if "all_songs_sort_order" not in st.session_state:
            st.session_state["all_songs_sort_order"] = "Descending"

        sort_by = st.selectbox(
            "Sort by",
            options=sort_by_options,
            index=sort_by_options.index(st.session_state["all_songs_sort_by"]),
            format_func=lambda x: sort_by_labels[x],
            key="all_songs_sort_by_select",
        )

        sort_order = st.selectbox(
            "Order",
            options=["Ascending", "Descending"],
            index=0
            if st.session_state["all_songs_sort_order"] == "Ascending"
            else 1,
            key="all_songs_sort_order_select",
        )

        ascending = sort_order == "Ascending"
        st.session_state["all_songs_sort_by"] = sort_by
        st.session_state["all_songs_sort_order"] = sort_order

        display_columns = [
            "played_at",
            "track_name",
            "artist_display",
            "album",
            "time_taken",
        ]
        missing_cols = [
            col for col in display_columns if col not in filtered_all_songs_df.columns
        ]
        for col in missing_cols:
            filtered_all_songs_df[col] = ""

        cache_needs_reset = (
            "cached_rows" not in st.session_state
            or "cached_sort_by" not in st.session_state
            or "cached_sort_order" not in st.session_state
            or st.session_state["cached_sort_by"] != sort_by
            or st.session_state["cached_sort_order"] != sort_order
            or "cached_all_songs_view_mode" not in st.session_state
            or st.session_state["cached_all_songs_view_mode"] != view_mode
            or (
                view_mode == "By Year"
                and (
                    "cached_all_songs_year" not in st.session_state
                    or st.session_state["cached_all_songs_year"] != selected_year
                )
            )
        )

        if cache_needs_reset:
            display_df = filtered_all_songs_df[display_columns].copy()
            display_df = display_df.sort_values(by=sort_by, ascending=ascending)

            display_df["Played At"] = pd.to_datetime(
                display_df["played_at"], errors="coerce"
            ).dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
            display_df["Title"] = display_df["track_name"].fillna("")
            display_df["Artist"] = display_df["artist_display"].fillna("")
            display_df["Album"] = display_df["album"].fillna("")
            display_df["Time Taken"] = display_df["time_taken"].apply(
                lambda x: "" if pd.isna(x) else x
            )

            formatted_df = display_df[
                ["Played At", "Title", "Artist", "Album", "Time Taken"]
            ]

            cached_rows = formatted_df.head(MAX_ROWS).reset_index(drop=True)
            st.session_state["cached_rows"] = cached_rows
            st.session_state["cached_sort_by"] = sort_by
            st.session_state["cached_sort_order"] = sort_order
            st.session_state["rows_displayed"] = INITIAL_ROWS
            st.session_state["cached_all_songs_view_mode"] = view_mode

            if view_mode == "By Year":
                st.session_state["cached_all_songs_year"] = selected_year
        else:
            cached_rows = st.session_state["cached_rows"]
            if "rows_displayed" not in st.session_state:
                st.session_state["rows_displayed"] = INITIAL_ROWS

        n_rows = min(st.session_state["rows_displayed"], len(st.session_state["cached_rows"]))
        to_display = st.session_state["cached_rows"].iloc[:n_rows]

        def render_table(dataframe):
            table_html = '<div class="dataframe-container"><table><thead><tr>'
            for col in dataframe.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr></thead><tbody>"
            for _, row in dataframe.iterrows():
                table_html += "<tr>"
                for col in dataframe.columns:
                    cell = row[col]
                    table_html += f"<td>{str(cell)}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

        if not to_display.empty:
            render_table(to_display)

            if n_rows < len(st.session_state["cached_rows"]):
                if st.button("Show 50 more", key="show_50_more"):
                    st.session_state["rows_displayed"] = min(
                        st.session_state["rows_displayed"] + 50,
                        len(st.session_state["cached_rows"]),
                    )
                if st.session_state["rows_displayed"] >= len(
                    st.session_state["cached_rows"]
                ):
                    st.info("You’ve reached the 200-song limit for this view.")
            elif len(st.session_state["cached_rows"]) == MAX_ROWS and len(
                filtered_all_songs_df
            ) > MAX_ROWS:
                st.info("You’ve reached the 200-song limit for this view.")

# --- LISTENING BY HOUR & DAY TAB ---
with tabs[4]:
    st.markdown("### Listening by Hour of the Day")

    if "played_at" in df.columns and not df.empty:
        if not pd.api.types.is_datetime64_any_dtype(df["played_at"]):
            df["played_at"] = pd.to_datetime(df["played_at"], errors="coerce")

        if df["played_at"].isna().all():
            if view_mode == "All Time":
                st.info("No listening data available for all time.")
            else:
                st.info("No listening data available for the selected period.")
        else:
            df["hour"] = df["played_at"].dt.hour

            hourly_counts = df.groupby("hour").size().reset_index(name="Play Count")
            full_hours = pd.DataFrame({"hour": range(24)})
            hourly_counts = (
                pd.merge(full_hours, hourly_counts, on="hour", how="left")
                .fillna(0)
            )

            hourly_counts["Hour"] = hourly_counts["hour"].apply(
                lambda x: f"{x:02d}:00"
            )
            hourly_counts["Play Count"] = hourly_counts["Play Count"].astype(int)

            if view_mode == "All Time":
                chart_title = "Listening Activity by Hour - All Time"
            elif view_mode == "By Year":
                chart_title = f"Listening Activity by Hour - {selected_year}"
            elif view_mode == "By Month":
                chart_title = f"Listening Activity by Hour - {selected_month} {selected_year}"
            else:
                chart_title = "Listening Activity by Hour"

            fig = px.bar(
                hourly_counts,
                x="Hour",
                y="Play Count",
                title=chart_title,
                labels={"Play Count": "Songs Played", "Hour": "Hour of Day"},
                color="Play Count",
                color_continuous_scale="Greens",
            )
            fig.update_layout(
                xaxis=dict(tickmode="linear", tick0=0, dtick=1),
                plot_bgcolor="#fff",
                paper_bgcolor="#fff",
                font=dict(color="#111"),
            )
            st.plotly_chart(fig, use_container_width=True)

            hourly_counts["Cumulative Plays"] = hourly_counts["Play Count"].cumsum()

            if view_mode == "All Time":
                cum_title = "Cumulative Listening Activity by Hour - All Time"
            elif view_mode == "By Year":
                cum_title = f"Cumulative Listening Activity by Hour - {selected_year}"
            elif view_mode == "By Month":
                cum_title = f"Cumulative Listening Activity by Hour - {selected_month} {selected_year}"
            else:
                cum_title = "Cumulative Listening Activity by Hour"

            fig = px.line(
                hourly_counts,
                x="Hour",
                y="Cumulative Plays",
                title=cum_title,
                markers=True,
                color_discrete_sequence=["#4CAF50"],
            )
            fig.update_layout(
                xaxis=dict(
                    tickmode="linear",
                    tick0=0,
                    dtick=1,
                    range=[-0.5, 23.5],
                    showline=False,
                    zeroline=True,
                    zerolinecolor="#e0e0e0",
                    gridcolor="#e0e0e0",
                ),
                yaxis=dict(
                    rangemode="tozero",
                    showline=False,
                    zeroline=True,
                    zerolinecolor="#e0e0e0",
                    gridcolor="#e0e0e0",
                ),
                margin=dict(l=40, r=40, t=60, b=40),
                plot_bgcolor="#fff",
                paper_bgcolor="#fff",
                font=dict(color="#111"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        if view_mode == "All Time":
            st.info("No listening data available for all time.")
        elif view_mode == "By Year":
            st.info("No listening data available for the selected year.")
        elif view_mode == "By Month":
            st.info("No listening data available for the selected month.")

    st.markdown("### Listening by Day of the Week")

    if "played_at" in df.columns and not df.empty:
        if not pd.api.types.is_datetime64_any_dtype(df["played_at"]):
            df["played_at"] = pd.to_datetime(df["played_at"], errors="coerce")

        if df["played_at"].isna().all():
            st.info("No listening data available for the selected period.")
        else:
            df["day_of_week"] = df["played_at"].dt.dayofweek

            days_order = [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ]
            days_map = {
                0: "Monday",
                1: "Tuesday",
                2: "Wednesday",
                3: "Thursday",
                4: "Friday",
                5: "Saturday",
                6: "Sunday",
            }
            df["Day"] = df["day_of_week"].map(days_map)

            daily_counts = (
                df.groupby("Day")
                .size()
                .reindex(days_order)
                .reset_index(name="Play Count")
            )
            daily_counts["Day"] = pd.Categorical(
                daily_counts["Day"], categories=days_order, ordered=True
            )
            daily_counts = daily_counts.sort_values("Day")

            max_play = daily_counts["Play Count"].max()
            min_play = daily_counts["Play Count"].min()
            intensity = (daily_counts["Play Count"] - min_play) / (
                max_play - min_play + 1e-9
            )

            from plotly.colors import sample_colorscale

            color_map = sample_colorscale("Greens", intensity)

            if view_mode == "All Time":
                pie_title = "Listening Share by Day - All Time"
            elif view_mode == "By Year":
                pie_title = f"Listening Share by Day - {selected_year}"
            elif view_mode == "By Month":
                pie_title = f"Listening Share by Day - {selected_month} {selected_year}"
            else:
                pie_title = "Listening Share by Day"

            fig_day_donut = px.pie(
                daily_counts,
                names="Day",
                values="Play Count",
                title=pie_title,
                hole=0.4,
            )
            fig_day_donut.update_traces(
                marker=dict(colors=color_map, line=dict(color="#2e7d32", width=0.8)),
                textposition="inside",
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Plays: %{value}<extra></extra>",
                sort=False,
            )

            fig_day_donut.update_layout(
                plot_bgcolor="#fff",
                paper_bgcolor="#fff",
                font=dict(color="#111"),
                showlegend=False,
                margin=dict(l=40, r=40, t=60, b=40),
            )

            st.plotly_chart(fig_day_donut, use_container_width=True)
    else:
        st.info("No listening data available for the selected period.")