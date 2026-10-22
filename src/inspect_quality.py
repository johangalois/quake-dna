"""Inspect suspicious depth values without modifying the dataset."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "earthquakes.csv"


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["event_time"])

    negative = df.loc[df["depth_km"] < 0].copy()

    print("=== PROFUNDIDADES NEGATIVAS ===")
    print(f"Registros: {len(negative):,}")

    if negative.empty:
        print("No se encontraron registros.")
        return

    columns = [
        "event_id",
        "event_time",
        "magnitude",
        "place",
        "depth_km",
        "magnitude_type",
        "status",
        "longitude",
        "latitude",
    ]

    print("\nEjemplos de registros:")
    print(
        negative[columns]
        .sort_values("depth_km")
        .head(20)
        .to_string(index=False)
    )

    print("\nEstadísticas de profundidad negativa:")
    print(negative["depth_km"].describe().round(3).to_string())

    print("\nRegistros por estado:")
    print(negative["status"].value_counts(dropna=False).to_string())

    print("\nRegistros por tipo de magnitud:")
    print(
        negative["magnitude_type"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nDistribución de profundidades en todo el dataset:")
    print(
        df["depth_km"]
        .quantile([0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1])
        .round(3)
        .to_string()
    )


if __name__ == "__main__":
    main()
