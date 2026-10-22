"""Interactive dashboard for Quake DNA."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.processing import process_events


st.set_page_config(
    page_title="Quake DNA | Earthquake Explorer",
    page_icon="🌎",
    layout="wide",
)


@st.cache_data(show_spinner="Loading and processing earthquake data...")
def load_data():
    df = process_events()
    df = df.copy()
    df["event_time"] = pd.to_datetime(
        df["event_time"], utc=True, errors="coerce"
    )
    for column in ["magnitude", "longitude", "latitude", "depth_km"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(
        subset=["event_time", "magnitude", "longitude", "latitude"]
    )
    df = df[
        df["longitude"].between(-180, 180)
        & df["latitude"].between(-90, 90)
    ]
    return df.sort_values("event_time")


st.title("🌎 Quake DNA")
st.subheader("Earthquake Explorer")
st.caption(
    "Explore seismic activity through interactive maps, "
    "magnitude distributions, and temporal trends."
)

try:
    data = load_data()
except Exception as exc:
    st.error(f"Unable to load earthquake data: {exc}")
    st.stop()

if data.empty:
    st.warning("No valid earthquake records are available.")
    st.stop()

st.sidebar.header("Filters")

min_date = data["event_time"].min().date()
max_date = data["event_time"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

min_mag = float(data["magnitude"].min())
max_mag = float(data["magnitude"].max())

if min_mag < max_mag:
    magnitude_range = st.sidebar.slider(
        "Magnitude range",
        min_value=min_mag,
        max_value=max_mag,
        value=(min_mag, max_mag),
        step=0.1,
    )
else:
    magnitude_range = (min_mag, max_mag)
    st.sidebar.caption(f"All events have magnitude {min_mag:.1f}")

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

start_time = pd.Timestamp(start_date, tz="UTC")
end_time = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)

filtered = data[
    data["event_time"].ge(start_time)
    & data["event_time"].lt(end_time)
    & data["magnitude"].between(*magnitude_range)
].copy()

st.sidebar.caption(f"{len(filtered):,} events match your filters.")

if filtered.empty:
    st.warning("No earthquakes match the selected filters.")
    st.stop()

st.markdown("### Key metrics")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Earthquakes", f"{len(filtered):,}")
k2.metric("Average magnitude", f"{filtered['magnitude'].mean():.2f}")
k3.metric("Maximum magnitude", f"{filtered['magnitude'].max():.2f}")

valid_depths = filtered["depth_km"].dropna()
k4.metric(
    "Average depth",
    f"{valid_depths.mean():.1f} km" if not valid_depths.empty else "N/A",
)

st.divider()

left, right = st.columns(2)

with left:
    st.markdown("### Seismic activity over time")
    daily = (
        filtered.set_index("event_time")
        .resample("D")
        .size()
        .rename("Earthquakes")
        .reset_index()
    )
    fig_time = px.line(
        daily,
        x="event_time",
        y="Earthquakes",
        labels={
            "event_time": "Date",
            "Earthquakes": "Number of earthquakes",
        },
        template="plotly_white",
    )
    fig_time.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_time, use_container_width=True)

with right:
    st.markdown("### Magnitude distribution")
    fig_mag = px.histogram(
        filtered,
        x="magnitude",
        nbins=30,
        labels={"magnitude": "Magnitude", "count": "Events"},
        template="plotly_white",
    )
    fig_mag.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_mag, use_container_width=True)

st.divider()
st.markdown("### Global earthquake map")

map_data = filtered.copy()
if len(map_data) > 5000:
    map_data = map_data.sample(n=5000, random_state=42)

fig_map = px.scatter_geo(
    map_data,
    lat="latitude",
    lon="longitude",
    color="magnitude",
    size="magnitude",
    hover_name="place" if "place" in map_data.columns else None,
    hover_data={
        "event_time": True,
        "depth_km": True,
        "latitude": False,
        "longitude": False,
    },
    color_continuous_scale="YlOrRd",
    projection="natural earth",
    labels={
        "magnitude": "Magnitude",
        "event_time": "Time (UTC)",
        "depth_km": "Depth (km)",
    },
)
fig_map.update_layout(
    height=560,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig_map, use_container_width=True)

st.divider()
st.markdown("### Earthquake records")

display_columns = [
    col for col in [
        "event_time",
        "event_id",
        "magnitude",
        "place",
        "latitude",
        "longitude",
        "depth_km",
        "negative_depth_flag",
    ]
    if col in filtered.columns
]

st.dataframe(
    filtered[display_columns].sort_values("event_time", ascending=False),
    use_container_width=True,
    hide_index=True,
)

csv = filtered[display_columns].to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered data (CSV)",
    data=csv,
    file_name="quake_dna_filtered.csv",
    mime="text/csv",
)

st.caption(
    "Quake DNA · Data source: USGS Earthquake Catalog · "
    "Map displays up to 5,000 randomly sampled events when datasets are large."
)
