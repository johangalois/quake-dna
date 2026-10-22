

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_source import fetch_recent_events


# ============================================================
# 1. CONFIGURATION & VISUAL THEME
# ============================================================

st.set_page_config(
    page_title="Quake DNA | Earthquake Intelligence",
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded",
)

BG = "#0B1120"
PANEL = "#121C2F"
BORDER = "#26354D"
TEXT = "#E5EDF8"
MUTED = "#91A4BF"
CYAN = "#35D0E8"
BLUE = "#5799FF"
PURPLE = "#A78BFA"
ORANGE = "#FFB454"
RED = "#FF6B6B"
GREEN = "#49D7A0"

PALETTE = [
    CYAN,
    BLUE,
    PURPLE,
    ORANGE,
    RED,
    GREEN,
    "#F472B6",
    "#A3E635",
]

CHART_TEMPLATE = "plotly_dark"

st.markdown(
    f"""
    <style>
    .stApp {{
        background: {BG};
        color: {TEXT};
    }}

    [data-testid="stHeader"] {{
        background: rgba(11, 17, 32, 0.94);
    }}

    [data-testid="stSidebar"] {{
        background: #0E1728;
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stMetric"] {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 17px 18px;
    }}

    [data-testid="stMetricLabel"] {{
        color: {MUTED};
        font-size: 0.86rem;
    }}

    [data-testid="stMetricValue"] {{
        color: {TEXT};
        font-weight: 700;
    }}

    div[data-testid="stPlotlyChart"] {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 8px;
        background: {PANEL};
    }}

    .hero {{
        background: linear-gradient(115deg, #14243B 0%, #102B3A 55%, #172341 100%);
        border: 1px solid #29445F;
        border-radius: 18px;
        padding: 25px 28px;
        margin-bottom: 22px;
    }}

    .hero-title {{
        color: {TEXT};
        font-size: 2.05rem;
        font-weight: 800;
        letter-spacing: -0.8px;
        margin: 0;
    }}

    .hero-subtitle {{
        color: {MUTED};
        font-size: 1rem;
        margin-top: 8px;
    }}

    .eyebrow {{
        color: {CYAN};
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}

    .section-note {{
        color: {MUTED};
        font-size: 0.88rem;
        margin-top: -8px;
        margin-bottom: 14px;
    }}

    .status-pill {{
        display: inline-block;
        border: 1px solid #276B69;
        background: #103B3C;
        color: #7CE8C4;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
    }}

    footer {{
        visibility: hidden;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. DATA LOADING
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Loading earthquake data from USGS...")
def load_data():
    df = fetch_recent_events(days=365).copy()

    required = {
        "event_id",
        "event_time",
        "magnitude",
        "place",
        "longitude",
        "latitude",
        "depth_km",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns in the USGS dataset: {sorted(missing)}"
        )

    df["event_time"] = pd.to_datetime(
        df["event_time"], errors="coerce", utc=True
    )

    # Use timezone-naive UTC timestamps for consistent date filtering.
    df["event_time"] = df["event_time"].dt.tz_localize(None)

    numeric_columns = [
        "magnitude",
        "longitude",
        "latitude",
        "depth_km",
        "felt_reports",
        "significance",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["place"] = df["place"].fillna("Unknown location").astype(str)

    df = df.dropna(
        subset=[
            "event_id",
            "event_time",
            "magnitude",
            "longitude",
            "latitude",
        ]
    )

    df = df[
        df["longitude"].between(-180, 180)
        & df["latitude"].between(-90, 90)
    ].copy()

    df = df.drop_duplicates(subset="event_id")

    # Geographic region estimated from latitude/longitude.
    df["region"] = df.apply(
        lambda row: classify_region(row["latitude"], row["longitude"]),
        axis=1,
    )

    # USGS location description is not a standardized country field.
    # This extracts its final comma-separated component as a rough area label.
    df["reported_area"] = df["place"].apply(extract_reported_area)

    df["depth_category"] = df["depth_km"].apply(classify_depth)

    df["event_date"] = df["event_time"].dt.date
    df["event_month"] = df["event_time"].dt.to_period("M").astype(str)

    return df.sort_values("event_time").reset_index(drop=True)


def classify_region(latitude, longitude):
    """Estimate a broad geographic region from event coordinates."""

    lat = float(latitude)
    lon = float(longitude)

    if lat >= 66.5:
        return "Arctic"
    if lat <= -60:
        return "Antarctic"

    if -170 <= lon <= -30 and lat >= 7:
        return "North America"

    if -120 <= lon <= -55 and -5 <= lat < 7:
        return "Central America & Caribbean"

    if -85 <= lon <= -30 and lat < -5:
        return "South America"

    if -30 <= lon <= 60 and lat >= 35:
        return "Europe"

    if -20 <= lon <= 55 and 0 <= lat < 35:
        return "Africa & Middle East"

    if 55 < lon <= 100 and lat >= 5:
        return "Central & South Asia"

    if 100 < lon <= 150 and lat >= 15:
        return "East Asia"

    if 90 <= lon <= 155 and -12 <= lat < 15:
        return "Southeast Asia"

    if 110 <= lon <= 180 and lat < 0:
        return "Oceania"

    if lon > 150 or lon < -150:
        return "Pacific & Remote Islands"

    if -30 < lon < 60 and lat < 0:
        return "Africa & Indian Ocean"

    return "Other / Mixed Region"


def extract_reported_area(place):
    """Extract a useful grouping label from the USGS place description."""

    if not isinstance(place, str) or not place.strip():
        return "Unknown area"

    parts = [part.strip() for part in place.split(",") if part.strip()]

    if len(parts) >= 2:
        return parts[-1]

    return parts[0] if parts else "Unknown area"


def classify_depth(depth):
    if pd.isna(depth):
        return "Unknown"

    if depth < 0:
        return "Negative depth"

    if depth < 70:
        return "Shallow"

    if depth < 300:
        return "Intermediate"

    return "Deep"


def style_chart(fig, height=None):
    fig.update_layout(
        template=CHART_TEMPLATE,
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(
            family="Arial, sans-serif",
            color=TEXT,
            size=12,
        ),
        title_font=dict(size=16, color=TEXT),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED),
        ),
        margin=dict(l=20, r=20, t=55, b=25),
        hoverlabel=dict(
            bgcolor="#18263D",
            bordercolor=BORDER,
            font_color=TEXT,
        ),
    )

    fig.update_xaxes(
        gridcolor=BORDER,
        zerolinecolor=BORDER,
        title_font_color=MUTED,
        tickfont_color=MUTED,
    )

    fig.update_yaxes(
        gridcolor=BORDER,
        zerolinecolor=BORDER,
        title_font_color=MUTED,
        tickfont_color=MUTED,
    )

    if height:
        fig.update_layout(height=height)

    return fig


# ============================================================
# 3. LOAD DATA
# ============================================================

try:
    df = load_data()
except Exception as exc:
    st.error(f"Unable to load earthquake data: {exc}")
    st.info(
        "Check your internet connection and the USGS API. "
        "The data source should be available in src/data_source.py."
    )
    st.stop()

if df.empty:
    st.warning("The USGS API returned no events for the selected period.")
    st.stop()


# ============================================================
# 4. HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">EARTH SCIENCE · DATA INTELLIGENCE</div>
        <div class="hero-title">🌎 Quake DNA</div>
        <div class="hero-subtitle">
            Explore seismic activity, compare geographic regions,
            and investigate individual earthquake events.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Data source: USGS Earthquake Hazards Program · "
    "Public API · Rolling 365-day dataset · "
    "Geographic regions are approximate analytical groupings."
)


# ============================================================
# 5. SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown("## Explore the data")
st.sidebar.caption("Adjust filters to update the entire dashboard.")

if st.sidebar.button("↻ Refresh data from USGS", use_container_width=True):
    load_data.clear()
    st.rerun()

min_date = df["event_date"].min()
max_date = df["event_date"].max()

date_selection = st.sidebar.date_input(
    "Event date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
    start_date, end_date = date_selection
else:
    start_date = date_selection[0] if isinstance(date_selection, (tuple, list)) else date_selection
    end_date = start_date

min_mag = float(df["magnitude"].min())
max_mag = float(df["magnitude"].max())

mag_low = max(0.0, min_mag)
mag_high = max(max_mag, mag_low + 0.1)

mag_range = st.sidebar.slider(
    "Magnitude range",
    min_value=float(mag_low),
    max_value=float(mag_high),
    value=(float(mag_low), float(mag_high)),
    step=0.1,
)

depth_options = [
    "All depths",
    "Shallow",
    "Intermediate",
    "Deep",
    "Negative depth",
    "Unknown",
]

selected_depth = st.sidebar.selectbox(
    "Depth category",
    depth_options,
    index=0,
)

region_options = ["All regions"] + sorted(df["region"].dropna().unique().tolist())

selected_region = st.sidebar.selectbox(
    "Geographic region",
    region_options,
    index=0,
)

# First apply broad filters.
filtered = df[
    (df["event_date"] >= start_date)
    & (df["event_date"] <= end_date)
    & (df["magnitude"] >= mag_range[0])
    & (df["magnitude"] <= mag_range[1])
].copy()

if selected_depth != "All depths":
    filtered = filtered[filtered["depth_category"] == selected_depth]

if selected_region != "All regions":
    filtered = filtered[filtered["region"] == selected_region]

if filtered.empty:
    st.warning("No earthquakes match the selected filters.")
    st.stop()


# ============================================================
# 6. KPI SUMMARY
# ============================================================

total_events = len(filtered)
avg_magnitude = filtered["magnitude"].mean()
max_magnitude = filtered["magnitude"].max()
avg_depth = filtered["depth_km"].mean()
regions_covered = filtered["region"].nunique()

st.markdown("### Seismic overview")
st.markdown(
    '<div class="section-note">Key indicators for the current selection.</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Earthquake events", f"{total_events:,}")
k2.metric("Average magnitude", f"{avg_magnitude:.2f}")
k3.metric("Highest magnitude", f"{max_magnitude:.1f}")
k4.metric(
    "Average depth",
    f"{avg_depth:,.1f} km" if pd.notna(avg_depth) else "N/A",
)
k5.metric("Regions covered", f"{regions_covered:,}")

st.divider()


# ============================================================
# 7. TABS
# ============================================================

tab_overview, tab_regions, tab_drill, tab_events = st.tabs(
    [
        "📊 Overview",
        "🌐 Regional analysis",
        "🔎 Drill-down explorer",
        "📋 Event records",
    ]
)


# ============================================================
# 8. OVERVIEW TAB
# ============================================================

with tab_overview:
    st.markdown("### Seismic activity over time")
    st.markdown(
        '<div class="section-note">'
        "Daily event counts and the distribution of earthquake magnitudes."
        "</div>",
        unsafe_allow_html=True,
    )

    daily = (
        filtered.groupby("event_date")
        .size()
        .reset_index(name="event_count")
        .sort_values("event_date")
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_daily = px.area(
            daily,
            x="event_date",
            y="event_count",
            title="Daily earthquake activity",
            labels={
                "event_date": "Date",
                "event_count": "Events",
            },
        )

        fig_daily.update_traces(
            line_color=CYAN,
            fillcolor="rgba(53, 208, 232, 0.20)",
            hovertemplate="%{x}<br>Events: %{y:,}<extra></extra>",
        )

        style_chart(fig_daily, 350)
        st.plotly_chart(fig_daily, use_container_width=True)

    with col2:
        fig_hist = px.histogram(
            filtered,
            x="magnitude",
            nbins=30,
            title="Magnitude distribution",
            labels={"magnitude": "Magnitude"},
            color_discrete_sequence=[PURPLE],
        )

        fig_hist.update_traces(
            hovertemplate="Magnitude: %{x}<br>Events: %{y:,}<extra></extra>"
        )

        style_chart(fig_hist, 350)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("### Depth and magnitude")

    col3, col4 = st.columns(2)

    with col3:
        depth_summary = (
            filtered.groupby("depth_category")
            .size()
            .reindex(
                [
                    "Shallow",
                    "Intermediate",
                    "Deep",
                    "Negative depth",
                    "Unknown",
                ],
                fill_value=0,
            )
            .reset_index(name="events")
        )

        depth_summary = depth_summary[depth_summary["events"] > 0]

        fig_depth = px.bar(
            depth_summary,
            x="depth_category",
            y="events",
            color="depth_category",
            text="events",
            title="Events by depth category",
            labels={
                "depth_category": "Depth category",
                "events": "Events",
            },
            color_discrete_sequence=PALETTE,
        )

        fig_depth.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            cliponaxis=False,
        )

        style_chart(fig_depth, 350)
        fig_depth.update_layout(showlegend=False)
        st.plotly_chart(fig_depth, use_container_width=True)

    with col4:
        scatter_data = filtered.dropna(subset=["depth_km", "magnitude"])

        fig_scatter = px.scatter(
            scatter_data,
            x="depth_km",
            y="magnitude",
            color="region",
            hover_name="place",
            hover_data={
                "event_time": True,
                "depth_km": ":.1f",
                "magnitude": ":.2f",
                "region": True,
            },
            title="Magnitude vs. depth",
            labels={
                "depth_km": "Depth (km)",
                "magnitude": "Magnitude",
                "region": "Region",
            },
            color_discrete_sequence=PALETTE,
            opacity=0.75,
        )

        style_chart(fig_scatter, 350)
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("### Global earthquake map")
    st.markdown(
        '<div class="section-note">'
        "Spatial distribution of the selected events. "
        "This map is independent of the regional comparison charts."
        "</div>",
        unsafe_allow_html=True,
    )

    map_df = filtered.copy()

    # Limit plotted points to keep the interactive map responsive.
    if len(map_df) > 5000:
        map_df = map_df.sample(5000, random_state=42)

    fig_map = px.scatter_geo(
        map_df,
        lat="latitude",
        lon="longitude",
        color="magnitude",
        size="magnitude",
        size_max=10,
        hover_name="place",
        hover_data={
            "event_time": True,
            "magnitude": ":.2f",
            "depth_km": ":.1f",
            "region": True,
            "latitude": ":.3f",
            "longitude": ":.3f",
        },
        color_continuous_scale=[
            "#3B82F6",
            "#35D0E8",
            "#FBBF24",
            "#FF6B6B",
        ],
        projection="natural earth",
        title="Global seismic activity",
    )

    fig_map.update_geos(
        bgcolor=PANEL,
        showland=True,
        landcolor="#17263B",
        showocean=True,
        oceancolor="#0D192B",
        showcountries=True,
        countrycolor="#34445C",
        showcoastlines=True,
        coastlinecolor="#40516A",
        showframe=False,
    )

    fig_map.update_layout(
        height=570,
        coloraxis_colorbar=dict(title="Magnitude"),
    )

    style_chart(fig_map, 570)
    st.plotly_chart(fig_map, use_container_width=True)

    if len(filtered) > len(map_df):
        st.caption(
            f"The map displays a representative sample of {len(map_df):,} "
            f"events out of {len(filtered):,} filtered events. "
            "All filtered records remain available in the tables and exports."
        )


# ============================================================
# 9. REGIONAL ANALYSIS TAB
# ============================================================

with tab_regions:
    st.markdown("### Compare geographic regions")
    st.markdown(
        '<div class="section-note">'
        "Compare event frequency, magnitude, depth and temporal patterns. "
        "Regions are estimated from coordinates and are not official USGS fields."
        "</div>",
        unsafe_allow_html=True,
    )

    region_summary = (
        filtered.groupby("region")
        .agg(
            events=("event_id", "count"),
            avg_magnitude=("magnitude", "mean"),
            max_magnitude=("magnitude", "max"),
            avg_depth_km=("depth_km", "mean"),
            median_depth_km=("depth_km", "median"),
        )
        .reset_index()
    )

    region_summary["share_pct"] = (
        region_summary["events"] / region_summary["events"].sum() * 100
    )

    region_summary = region_summary.sort_values(
        "events", ascending=False
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_region_count = px.bar(
            region_summary,
            x="region",
            y="events",
            text="events",
            color="region",
            title="Earthquake count by region",
            labels={"region": "Region", "events": "Events"},
            color_discrete_sequence=PALETTE,
        )

        fig_region_count.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            cliponaxis=False,
        )

        fig_region_count.update_layout(
            showlegend=False,
            xaxis_tickangle=-25,
        )

        style_chart(fig_region_count, 430)
        st.plotly_chart(fig_region_count, use_container_width=True)

    with col2:
        fig_region_magnitude = px.bar(
            region_summary.sort_values("avg_magnitude", ascending=False),
            x="region",
            y="avg_magnitude",
            text="avg_magnitude",
            color="avg_magnitude",
            color_continuous_scale=["#35D0E8", "#5799FF", "#FFB454", "#FF6B6B"],
            title="Average magnitude by region",
            labels={
                "region": "Region",
                "avg_magnitude": "Average magnitude",
            },
        )

        fig_region_magnitude.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside",
            cliponaxis=False,
        )

        fig_region_magnitude.update_layout(
            coloraxis_showscale=False,
            xaxis_tickangle=-25,
        )

        style_chart(fig_region_magnitude, 430)
        st.plotly_chart(fig_region_magnitude, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig_region_depth = px.bar(
            region_summary.sort_values("avg_depth_km", ascending=False),
            x="region",
            y="avg_depth_km",
            text="avg_depth_km",
            title="Average depth by region",
            labels={
                "region": "Region",
                "avg_depth_km": "Average depth (km)",
            },
            color="avg_depth_km",
            color_continuous_scale=["#35D0E8", "#A78BFA", "#FFB454"],
        )

        fig_region_depth.update_traces(
            texttemplate="%{text:.1f} km",
            textposition="outside",
            cliponaxis=False,
        )

        fig_region_depth.update_layout(
            coloraxis_showscale=False,
            xaxis_tickangle=-25,
        )

        style_chart(fig_region_depth, 400)
        st.plotly_chart(fig_region_depth, use_container_width=True)

    with col4:
        fig_region_share = px.pie(
            region_summary,
            names="region",
            values="events",
            hole=0.58,
            title="Share of events by region",
            color_discrete_sequence=PALETTE,
        )

        fig_region_share.update_traces(
            textposition="inside",
            textinfo="percent",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Events: %{value:,}<br>"
                "Share: %{percent}<extra></extra>"
            ),
        )

        style_chart(fig_region_share, 400)
        st.plotly_chart(fig_region_share, use_container_width=True)

    st.markdown("### Regional comparison table")

    display_summary = region_summary.rename(
        columns={
            "region": "Region",
            "events": "Events",
            "avg_magnitude": "Average magnitude",
            "max_magnitude": "Maximum magnitude",
            "avg_depth_km": "Average depth (km)",
            "median_depth_km": "Median depth (km)",
            "share_pct": "Share (%)",
        }
    )

    st.dataframe(
        display_summary.style.format(
            {
                "Average magnitude": "{:.2f}",
                "Maximum magnitude": "{:.1f}",
                "Average depth (km)": "{:.1f}",
                "Median depth (km)": "{:.1f}",
                "Share (%)": "{:.1f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download regional summary CSV",
        data=region_summary.to_csv(index=False).encode("utf-8"),
        file_name="quake_dna_regional_summary.csv",
        mime="text/csv",
    )

    # Region-level monthly trend
    st.markdown("### Monthly trend by region")

    monthly_region = (
        filtered.assign(
            month=filtered["event_time"].dt.to_period("M").astype(str)
        )
        .groupby(["month", "region"])
        .size()
        .reset_index(name="events")
    )

    fig_monthly_region = px.line(
        monthly_region,
        x="month",
        y="events",
        color="region",
        markers=True,
        title="Monthly earthquake count by region",
        labels={
            "month": "Month",
            "events": "Events",
            "region": "Region",
        },
        color_discrete_sequence=PALETTE,
    )

    style_chart(fig_monthly_region, 430)
    st.plotly_chart(fig_monthly_region, use_container_width=True)


# ============================================================
# 10. DRILL-DOWN EXPLORER
# ============================================================

with tab_drill:
    st.markdown("### Investigate a specific region")
    st.markdown(
        '<div class="section-note">'
        "Start with a region, then narrow the analysis to an area "
        "mentioned in the USGS event description."
        "</div>",
        unsafe_allow_html=True,
    )

    drill_region_options = sorted(
        filtered["region"].dropna().unique().tolist()
    )

    default_region_index = (
        drill_region_options.index(selected_region)
        if selected_region in drill_region_options
        else 0
    )

    drill_region = st.selectbox(
        "1 · Select region",
        drill_region_options,
        index=default_region_index,
        key="drill_region",
    )

    regional_data = filtered[filtered["region"] == drill_region].copy()

    area_counts = (
        regional_data["reported_area"]
        .value_counts()
        .head(100)
    )

    area_options = ["All reported areas"] + area_counts.index.tolist()

    drill_area = st.selectbox(
        "2 · Select reported area",
        area_options,
        key="drill_area",
        help=(
            "Area labels are extracted from the final component of the "
            "USGS place description. They are not a standardized country field."
        ),
    )

    drill_data = regional_data.copy()

    if drill_area != "All reported areas":
        drill_data = drill_data[
            drill_data["reported_area"] == drill_area
        ].copy()

    if drill_data.empty:
        st.info("No events match this drill-down selection.")
    else:
        st.markdown("#### Selection summary")

        d1, d2, d3, d4 = st.columns(4)

        d1.metric("Events", f"{len(drill_data):,}")
        d2.metric(
            "Average magnitude",
            f"{drill_data['magnitude'].mean():.2f}",
        )
        d3.metric(
            "Maximum magnitude",
            f"{drill_data['magnitude'].max():.1f}",
        )

        mean_depth = drill_data["depth_km"].mean()
        d4.metric(
            "Average depth",
            f"{mean_depth:.1f} km" if pd.notna(mean_depth) else "N/A",
        )

        c1, c2 = st.columns(2)

        with c1:
            area_summary = (
                drill_data.groupby("reported_area")
                .size()
                .reset_index(name="events")
                .sort_values("events", ascending=False)
                .head(15)
            )

            fig_areas = px.bar(
                area_summary.sort_values("events"),
                x="events",
                y="reported_area",
                orientation="h",
                text="events",
                title="Most frequently reported areas",
                labels={
                    "reported_area": "Reported area",
                    "events": "Events",
                },
                color_discrete_sequence=[CYAN],
            )

            fig_areas.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
            )

            style_chart(fig_areas, 420)
            st.plotly_chart(fig_areas, use_container_width=True)

        with c2:
            magnitude_bins = (
                drill_data.assign(
                    magnitude_band=pd.cut(
                        drill_data["magnitude"],
                        bins=[-float("inf"), 3, 4, 5, 6, 7, float("inf")],
                        labels=[
                            "< 3.0",
                            "3.0–3.9",
                            "4.0–4.9",
                            "5.0–5.9",
                            "6.0–6.9",
                            "7.0+",
                        ],
                        right=False,
                    )
                )
                .groupby("magnitude_band", observed=False)
                .size()
                .reset_index(name="events")
            )

            magnitude_bins = magnitude_bins[magnitude_bins["events"] > 0]

            fig_bins = px.bar(
                magnitude_bins,
                x="magnitude_band",
                y="events",
                text="events",
                title="Magnitude bands in selection",
                labels={
                    "magnitude_band": "Magnitude band",
                    "events": "Events",
                },
                color_discrete_sequence=[ORANGE],
            )

            fig_bins.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
            )

            style_chart(fig_bins, 420)
            st.plotly_chart(fig_bins, use_container_width=True)

        st.markdown("#### Recent events in this selection")

        detail_columns = [
            "event_time",
            "event_id",
            "magnitude",
            "depth_km",
            "place",
            "latitude",
            "longitude",
        ]

        detail_columns = [
            column for column in detail_columns if column in drill_data.columns
        ]

        st.dataframe(
            drill_data[detail_columns]
            .sort_values("event_time", ascending=False)
            .head(100),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download drill-down results",
            data=drill_data.to_csv(index=False).encode("utf-8"),
            file_name="quake_dna_drilldown.csv",
            mime="text/csv",
            key="download_drilldown",
        )


# ============================================================
# 11. EVENT RECORDS TAB
# ============================================================

with tab_events:
    st.markdown("### Earthquake event records")
    st.markdown(
        '<div class="section-note">'
        "Search and sort the filtered event dataset, then export it for further analysis."
        "</div>",
        unsafe_allow_html=True,
    )

    search_text = st.text_input(
        "Search event descriptions",
        placeholder="Search a place, state, or location description...",
    )

    table_data = filtered.copy()

    if search_text.strip():
        table_data = table_data[
            table_data["place"].str.contains(
                search_text.strip(),
                case=False,
                na=False,
            )
        ]

    st.caption(f"{len(table_data):,} event records match this view.")

    preferred_columns = [
        "event_time",
        "event_id",
        "magnitude",
        "magnitude_type",
        "depth_km",
        "depth_category",
        "region",
        "reported_area",
        "place",
        "latitude",
        "longitude",
        "felt_reports",
        "tsunami",
        "significance",
    ]

    visible_columns = [
        column for column in preferred_columns if column in table_data.columns
    ]

    st.dataframe(
        table_data[visible_columns].sort_values(
            "event_time",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "event_time": st.column_config.DatetimeColumn(
                "Event time (UTC)",
                format="YYYY-MM-DD HH:mm",
            ),
            "event_id": st.column_config.TextColumn("Event ID"),
            "magnitude": st.column_config.NumberColumn(
                "Magnitude",
                format="%.2f",
            ),
            "depth_km": st.column_config.NumberColumn(
                "Depth (km)",
                format="%.1f",
            ),
            "latitude": st.column_config.NumberColumn(
                "Latitude",
                format="%.3f",
            ),
            "longitude": st.column_config.NumberColumn(
                "Longitude",
                format="%.3f",
            ),
            "felt_reports": st.column_config.NumberColumn(
                "Felt reports",
                format="%d",
            ),
            "significance": st.column_config.NumberColumn(
                "Significance",
                format="%d",
            ),
        },
    )

    st.download_button(
        "Download filtered events CSV",
        data=table_data.to_csv(index=False).encode("utf-8"),
        file_name="quake_dna_filtered_events.csv",
        mime="text/csv",
    )


# ============================================================
# 12. FOOTER
# ============================================================

st.divider()

st.markdown(
    f"""
    <div style="text-align:center; color:{MUTED}; padding:12px 0 20px 0;">
        <strong style="color:{TEXT};">Quake DNA</strong>
        &nbsp;·&nbsp; Earthquake data exploration
        <br>
        <span style="font-size:0.8rem;">
            Source: USGS Earthquake Hazards Program.
            Geographic region labels are approximate.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)