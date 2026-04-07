"""Transformer QPV : flag binaire + nombre de QPV par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Le CSV a un séparateur ; — recharger correctement si besoin
    if "insee_com" not in df.columns and len(df.columns) <= 2:
        from pipeline.config import raw_path_for_source
        path = raw_path_for_source(source)
        df = pd.read_csv(path, sep=";")

    # La colonne commune est insee_com (code INSEE 5 chiffres, parfois sans leading 0)
    df["code_commune"] = df["insee_dep"].astype(str).str.zfill(2) + df["insee_com"].astype(str).str.zfill(3)

    # Compter le nombre de QPV par commune
    qpv_count = df.groupby("code_commune").size().reset_index(name="nb_qpv")
    qpv_count["flag_qpv"] = 1

    return qpv_count
