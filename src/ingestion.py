"""Extract earthquake events from the USGS FDSN Event API."""

import json
import time
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
MIN_MAGNITUDE = 2.5
LIMIT = 20_000
START_DATE = date(2025, 10, 22)
END_DATE = date(2026, 10, 22)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def next_month_start(current: date) -> date:
    """Return the first day of the following month."""
    if current.month == 12:
        return date(current.year + 1, 1, 1)
    return date(current.year, current.month + 1, 1)


def extract_events() -> list[dict]:
    """Download monthly GeoJSON responses and return unique events."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    events_by_id = {}

    current = START_DATE

    while current < END_DATE:
        period_end = min(next_month_start(current), END_DATE)

        params = {
            "format": "geojson",
            "starttime": current.isoformat(),
            "endtime": period_end.isoformat(),
            "minmagnitude": MIN_MAGNITUDE,
            "limit": LIMIT,
            "orderby": "time-asc",
        }

        print(f"Consultando USGS: {current} a {period_end}...")

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("type") != "FeatureCollection":
            raise ValueError("La respuesta no es una FeatureCollection GeoJSON.")

        features = payload.get("features", [])

        if len(features) >= LIMIT:
            raise RuntimeError(
                f"El periodo {current} a {period_end} alcanzó el límite "
                f"de {LIMIT} eventos. Hay que dividirlo en intervalos menores."
            )

        filename = (
            f"earthquakes_{current.isoformat()}_to_"
            f"{period_end.isoformat()}.geojson"
        )
        raw_path = RAW_DIR / filename

        with raw_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)

        for event in features:
            event_id = event.get("id")
            if event_id:
                events_by_id[event_id] = event

        print(f"  Eventos recibidos: {len(features)}")
        current = period_end
        time.sleep(0.2)

    events = list(events_by_id.values())

    combined_path = RAW_DIR / "earthquakes_combined.geojson"
    combined_payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "USGS FDSN Event API",
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "minimum_magnitude": MIN_MAGNITUDE,
            "unique_event_count": len(events),
        },
        "features": events,
    }

    with combined_path.open("w", encoding="utf-8") as file:
        json.dump(combined_payload, file, ensure_ascii=False)

    print(f"\nTotal de eventos únicos: {len(events)}")
    print(f"Archivo consolidado: {combined_path}")

    return events


if __name__ == "__main__":
    extract_events()
