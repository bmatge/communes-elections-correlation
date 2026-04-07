"""Transformer rp_mobilite — calcul sédentarité depuis les flux résidentiels."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Convertir le flux en numeric
    df["NBFLUX_C22_POP01P"] = pd.to_numeric(df["NBFLUX_C22_POP01P"], errors="coerce")

    # Remapper arrondissements PLM avant agrégation
    df = remap_arrondissements(df, col="CODGEO")
    df = remap_arrondissements(df, col="DCRAN")

    # Population totale par commune d'origine
    pop_totale = (
        df.groupby("CODGEO")["NBFLUX_C22_POP01P"]
        .sum()
        .rename("pop_totale")
    )

    # Flux sédentaires : commune d'origine == commune de destination
    sedentaires = (
        df[df["CODGEO"] == df["DCRAN"]]
        .groupby("CODGEO")["NBFLUX_C22_POP01P"]
        .sum()
        .rename("pop_sedentaire")
    )

    # Joindre
    result = pd.concat([pop_totale, sedentaires], axis=1).reset_index()

    # Calculer les pourcentages
    result["pct_sedentaire"] = result["pop_sedentaire"] / result["pop_totale"] * 100
    result["pct_arrivee_5ans"] = 100 - result["pct_sedentaire"]

    # Pad CODGEO sur 5 caractères
    result["CODGEO"] = result["CODGEO"].astype(str).str.zfill(5)

    # Renommer CODGEO pour correspondre au join_key attendu
    result = result.rename(columns={"CODGEO": "code_commune"})

    return result[["code_commune", "pct_sedentaire", "pct_arrivee_5ans"]].copy()
