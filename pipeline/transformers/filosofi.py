"""Transformer filosofi — pivot du format SDMX long vers colonnes."""

import pandas as pd


# Mapping des mesures SDMX → noms de colonnes attendus par sources.yaml
MEASURE_RENAME = {
    "MED_SL": "MED21",
    "PR_MD60": "TP6021",
    "IR_D9_D1_SL": "GI21",
    "D1_SL": "D121",
    "D9_SL": "D921",
}


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Stripper les guillemets de toutes les colonnes string
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip('"').str.strip()

    # Filtrer sur les communes uniquement
    df = df[df["GEO_OBJECT"] == "COM"].copy()

    # Convertir OBS_VALUE en numeric
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")

    # Pivot : index=GEO, columns=FILOSOFI_MEASURE, values=OBS_VALUE
    pivot = df.pivot_table(
        index="GEO",
        columns="FILOSOFI_MEASURE",
        values="OBS_VALUE",
        aggfunc="first",
    )

    pivot = pivot.reset_index()

    # Renommer les colonnes de mesures
    pivot = pivot.rename(columns=MEASURE_RENAME)

    # Renommer GEO → CODGEO
    pivot = pivot.rename(columns={"GEO": "CODGEO"})

    # Pad CODGEO sur 5 caractères
    pivot["CODGEO"] = pivot["CODGEO"].astype(str).str.zfill(5)

    return pivot
