"""Transformer rp_logement — agrégation du TD_LOG1 par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Filtrer communes uniquement
    df = df[df["NIVGEO"] == "COM"].copy()

    # Convertir NB en float, TYPLR en str
    df["NB"] = pd.to_numeric(df["NB"], errors="coerce")
    df["TYPLR"] = df["TYPLR"].astype(str).str.strip()

    # Total RP (toutes catégories)
    rp_total = df.groupby("CODGEO")["NB"].sum().rename("P21_RP")

    # Propriétaires : TYPLR == "1"
    rp_prop = (
        df[df["TYPLR"] == "1"]
        .groupby("CODGEO")["NB"]
        .sum()
        .rename("P21_RP_PROP")
    )

    # Locataires : TYPLR == "2"
    rp_loc = (
        df[df["TYPLR"] == "2"]
        .groupby("CODGEO")["NB"]
        .sum()
        .rename("P21_RP_LOC")
    )

    # Joindre
    result = pd.concat([rp_total, rp_prop, rp_loc], axis=1).reset_index()

    # Pad CODGEO sur 5 caractères
    result["CODGEO"] = result["CODGEO"].astype(str).str.zfill(5)

    return result
