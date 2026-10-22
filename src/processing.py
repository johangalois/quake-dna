"""Transform raw USGS GeoJSON into a clean analytical dataset."""

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "earthquakes_combined.geojson"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "earthquakes.csv"


def process_events() -> pd.DataFrame:
    """Flatten GeoJSON events into a clean, analysis-ready DataFrame."""
    with RAW_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    rows = []

    for event in payload.get("features", []):
        properties = event.get("properties") or {}
        geometry = event.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        longitude, latitude, depth = coordinates[:3]

        event_time = properties.get("time")
        event_time = (
            pd.to_datetime(event_time, unit="ms", utc=True)
            if event_time is not None
            else pd.NaT
        )

        rows.append(
            {
                "event_id": event.get("id"),
                "event_time": event_time,
                "magnitude": properties.get("mag"),
                "place": properties.get("place"),
                "longitude": longitude,
                "latitude": latitude,
                "depth_km": depth,
                "negative_depth_flag": depth is not None and depth < 0,
                "magnitude_type": properties.get("magType"),
                "status": properties.get("status"),
                "tsunami": properties.get("tsunami"),
                "felt_reports": properties.get("felt"),
                "significance": properties.get("sig"),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("No se encontraron eventos para procesar.")

    df["magnitude"] = pd.to_numeric(df["magnitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["depth_km"] = pd.to_numeric(df["depth_km"], errors="coerce")

    df = df.drop_duplicates(subset="event_id")
    df = df.sort_values("event_time").reset_index(drop=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print("=== PROCESAMIENTO COMPLETADO ===")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")
    print(f"Eventos únicos: {df['event_id'].nunique():,}")
    print(f"Fechas: {df['event_time'].min()} → {df['event_time'].max()}")
    print(f"Magnitud promedio: {df['magnitude'].mean():.2f}")
    print(f"CSV generado: {OUTPUT_PATH}")

    print("\nValores nulos por columna:")
    print(df.isna().sum().to_string())

    return df


if __name__ == "__main__":
    process_events()
