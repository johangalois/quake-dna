
"""Efficient earthquake data ingestion from the public USGS API."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

MIN_MAGNITUDE = 2.5
REQUEST_WINDOW_DAYS = 90
MAX_WORKERS = 4
REQUEST_TIMEOUT = 45
MAX_EVENTS_PER_REQUEST = 20000


def _fetch_interval(start, end):
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": MIN_MAGNITUDE,
        "eventtype": "earthquake",
        "orderby": "time-asc",
        "limit": MAX_EVENTS_PER_REQUEST,
    }

    response = requests.get(
        USGS_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    features = response.json().get("features", [])

    if len(features) >= MAX_EVENTS_PER_REQUEST:
        raise RuntimeError(
            "A USGS request reached the 20,000-event limit. "
            "Reduce REQUEST_WINDOW_DAYS to avoid incomplete results."
        )

    return features


def _parse_features(features):
    rows = []

    for event in features:
        properties = event.get("properties") or {}
        geometry = event.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        if len(coordinates) < 3:
            continue

        longitude, latitude, depth = coordinates[:3]

        rows.append({
            "event_id": event.get("id"),
            "event_time": properties.get("time"),
            "magnitude": properties.get("mag"),
            "place": properties.get("place"),
            "longitude": longitude,
            "latitude": latitude,
            "depth_km": depth,
            "negative_depth_flag": (
                depth is not None and depth < 0
            ),
            "magnitude_type": properties.get("magType"),
            "status": properties.get("status"),
            "tsunami": properties.get("tsunami"),
            "felt_reports": properties.get("felt"),
            "significance": properties.get("sig"),
        })

    return rows


def fetch_recent_events(days=365):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    intervals = []
    interval_start = start

    while interval_start < end:
        interval_end = min(
            interval_start + timedelta(days=REQUEST_WINDOW_DAYS),
            end,
        )

        intervals.append((interval_start, interval_end))
        interval_start = interval_end

    all_features = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_fetch_interval, interval_start, interval_end)
            for interval_start, interval_end in intervals
        ]

        for future in as_completed(futures):
            all_features.extend(future.result())

    rows = _parse_features(all_features)
    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("The USGS API returned no earthquake events.")

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        unit="ms",
        utc=True,
        errors="coerce",
    )

    numeric_columns = [
        "magnitude",
        "longitude",
        "latitude",
        "depth_km",
        "felt_reports",
        "significance",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.drop_duplicates(subset="event_id")

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
    ]

    return df.sort_values("event_time").reset_index(drop=True)
