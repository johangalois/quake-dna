"""Validate the combined raw USGS earthquake dataset."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "earthquakes_combined.geojson"


def main():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    features = payload.get("features", [])

    ids = [event.get("id") for event in features]
    valid_ids = [event_id for event_id in ids if event_id]

    magnitudes = []
    missing_magnitudes = 0
    missing_coordinates = 0
    invalid_coordinates = 0
    missing_dates = 0

    for event in features:
        properties = event.get("properties") or {}
        geometry = event.get("geometry") or {}
        coordinates = geometry.get("coordinates")

        magnitude = properties.get("mag")
        if magnitude is None:
            missing_magnitudes += 1
        else:
            magnitudes.append(magnitude)

        if not isinstance(coordinates, list) or len(coordinates) < 3:
            missing_coordinates += 1
        else:
            longitude, latitude, depth = coordinates[:3]

            if (
                longitude is None
                or latitude is None
                or depth is None
                or not (-180 <= longitude <= 180)
                or not (-90 <= latitude <= 90)
            ):
                invalid_coordinates += 1

        if properties.get("time") is None:
            missing_dates += 1

    print("=== VALIDACIÓN DEL DATASET ===")
    print(f"Tipo GeoJSON: {payload.get('type')}")
    print(f"Eventos totales: {len(features):,}")
    print(f"IDs únicos: {len(set(valid_ids)):,}")
    print(f"Eventos sin ID: {len(features) - len(valid_ids):,}")
    print(f"Magnitudes válidas: {len(magnitudes):,}")
    print(f"Eventos sin magnitud: {missing_magnitudes:,}")
    print(f"Eventos sin coordenadas completas: {missing_coordinates:,}")
    print(f"Eventos con coordenadas inválidas: {invalid_coordinates:,}")
    print(f"Eventos sin fecha: {missing_dates:,}")

    if magnitudes:
        print(f"Magnitud mínima: {min(magnitudes)}")
        print(f"Magnitud máxima: {max(magnitudes)}")
        print(f"Magnitud promedio: {sum(magnitudes) / len(magnitudes):.2f}")

    print("\nMetadatos:")
    print(json.dumps(payload.get("metadata", {}), indent=2, ensure_ascii=False))

    if len(features) != len(set(valid_ids)):
        print("\nADVERTENCIA: hay IDs faltantes o duplicados.")
    else:
        print("\nOK: todos los eventos tienen IDs únicos.")


if __name__ == "__main__":
    main()
