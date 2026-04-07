"""Transformer DVF : prix médian au m² par commune."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Filtrer sur les communes uniquement
    df = df[df["echelle_geo"] == "commune"].copy()
    df = df.rename(columns={"code_geo": "code_commune"})

    df = remap_arrondissements(df, col="code_commune")

    result = df[["code_commune"]].copy()

    # Prix médian appartements
    if "med_prix_m2_whole_appartement" in df.columns:
        result["prix_median_m2_appart"] = pd.to_numeric(
            df["med_prix_m2_whole_appartement"], errors="coerce"
        )

    # Prix médian maisons
    if "med_prix_m2_whole_maison" in df.columns:
        result["prix_median_m2_maison"] = pd.to_numeric(
            df["med_prix_m2_whole_maison"], errors="coerce"
        )

    # Nombre de ventes (proxy de dynamisme du marché)
    if "nb_ventes_whole_apt_maison" in df.columns:
        result["nb_ventes_immo"] = pd.to_numeric(
            df["nb_ventes_whole_apt_maison"], errors="coerce"
        )

    # Agréger les arrondissements PLM (médiane pour les prix, somme pour les ventes)
    if result["code_commune"].duplicated().any():
        agg_dict = {}
        for col in result.columns:
            if col == "code_commune":
                continue
            if "prix" in col:
                agg_dict[col] = "median"
            else:
                agg_dict[col] = "sum"
        result = result.groupby("code_commune", as_index=False).agg(agg_dict)

    return result
