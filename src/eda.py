"""Exploratory data analysis for the USGS earthquake dataset."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "earthquakes.csv"


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["event_time"])

    print("=== 1. DIMENSIONES ===")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")

    print("\n=== 2. ESTADÍSTICAS DE MAGNITUD ===")
    print(df["magnitude"].describe().round(2).to_string())

    print("\n=== 3. DISTRIBUCIÓN POR RANGO DE MAGNITUD ===")
    bins = [2.5, 3, 4, 5, 6, 7, float("inf")]
    labels = ["2.5–<3", "3–<4", "4–<5", "5–<6", "6–<7", "7+"]
    magnitude_groups = pd.cut(
        df["magnitude"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True,
    )
    print(magnitude_groups.value_counts(sort=False).to_string())

    print("\n=== 4. EVENTOS POR MES (UTC) ===")
    monthly = (
        df.assign(month=df["event_time"].dt.strftime("%Y-%m"))
        .groupby("month")
        .size()
    )
    print(monthly.to_string())

    print("\n=== 5. ESTADÍSTICAS DE PROFUNDIDAD (KM) ===")
    print(df["depth_km"].describe().round(2).to_string())

    print("\n=== 6. EVENTOS POR CATEGORÍA DE PROFUNDIDAD ===")
    depth_bins = [-float("inf"), 70, 300, float("inf")]
    depth_labels = ["Superficial (<70 km)", "Intermedio (70–300 km)", "Profundo (>300 km)"]
    depth_groups = pd.cut(
        df["depth_km"],
        bins=depth_bins,
        labels=depth_labels,
        right=False,
    )
    print(depth_groups.value_counts(sort=False).to_string())

    print("\n=== 7. EVENTOS DE MAGNITUD >= 5 ===")
    significant = df.loc[df["magnitude"] >= 5].copy()
    print(f"Total: {len(significant):,}")
    if not significant.empty:
        columns = ["event_time", "magnitude", "place", "depth_km"]
        print(
            significant.nlargest(10, "magnitude")[columns]
            .to_string(index=False)
        )

    print("\n=== 8. UBICACIONES MÁS REPETIDAS ===")
    print(
        df["place"]
        .value_counts()
        .head(10)
        .to_string()
    )

    print("\n=== 9. VALIDACIONES ADICIONALES ===")
    print(f"IDs duplicados: {df['event_id'].duplicated().sum():,}")
    print(f"Magnitudes inferiores a 2.5: {(df['magnitude'] < 2.5).sum():,}")
    print(f"Profundidades negativas: {(df['depth_km'] < 0).sum():,}")
    print(f"Latitudes fuera de rango: {(~df['latitude'].between(-90, 90)).sum():,}")
    print(f"Longitudes fuera de rango: {(~df['longitude'].between(-180, 180)).sum():,}")
    print(f"Reportes felt ausentes: {df['felt_reports'].isna().sum():,}")


if __name__ == "__main__":
    main()
