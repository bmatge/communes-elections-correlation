"""Transformer ZRR : flag binaire commune en ZRR."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Lire la bonne feuille avec skip des headers
    path = source.get("_raw_path")  # Sera passé par le pipeline
    if path is None:
        from pipeline.config import raw_path_for_source
        path = raw_path_for_source(source)

    df = pd.read_excel(path, sheet_name="Classement ZRR (COG 2021)", skiprows=5, engine="xlrd")

    df = df.rename(columns={"CODGEO": "code_commune"})
    df["flag_zrr"] = (df["ZRR_SIMP"] != "NC - Commune non classée").astype(int)

    return df[["code_commune", "flag_zrr"]]
