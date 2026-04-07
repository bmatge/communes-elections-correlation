"""Transformer ic_logement — agrégation IRIS → commune (base IC logement 2021)."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    numeric_cols = [c for c in df.columns if c not in ("IRIS", "COM", "TYP_IRIS", "LAB_IRIS")]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = remap_arrondissements(df, col="COM")

    agg = df.groupby("COM")[numeric_cols].sum().reset_index()
    agg = agg.rename(columns={"COM": "CODGEO"})
    agg["CODGEO"] = agg["CODGEO"].astype(str).str.zfill(5)

    return agg
