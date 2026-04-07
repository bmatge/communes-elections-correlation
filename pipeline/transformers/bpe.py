"""Transformer bpe — pivot du format SDMX par domaine d'équipement."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


# Mapping des domaines d'équipement
DOM_NAMES = {
    "A": "nb_equip_services",
    "B": "nb_equip_enseignement",
    "C": "nb_equip_sante",
    "D": "nb_equip_transport",
    "E": "nb_equip_loisirs",
    "F": "nb_equip_tourisme",
    "G": "nb_equip_sports",
}


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Stripper les guillemets de toutes les colonnes string
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip('"').str.strip()

    # Filtrer sur les communes uniquement
    df = df[df["GEO_OBJECT"] == "COM"].copy()

    # Filtrer sur la mesure FACILITIES
    df = df[df["BPE_MEASURE"] == "FACILITIES"].copy()

    # Convertir OBS_VALUE en numeric
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")

    # Total par commune
    total = df.groupby("GEO")["OBS_VALUE"].sum().rename("nb_equipements_total")

    # Par domaine
    dom_pivot = (
        df.groupby(["GEO", "FACILITY_DOM"])["OBS_VALUE"]
        .sum()
        .unstack(fill_value=0)
    )
    dom_pivot = dom_pivot.rename(columns=DOM_NAMES)

    # Supprimer la colonne résiduelle _T (total SDMX, redondant avec nb_equipements_total)
    dom_pivot = dom_pivot.drop(columns=["_T"], errors="ignore")

    # Joindre
    result = pd.concat([total, dom_pivot], axis=1).reset_index()

    # Renommer GEO → code_commune
    result = result.rename(columns={"GEO": "code_commune"})

    # Pad code_commune sur 5 caractères
    result["code_commune"] = result["code_commune"].astype(str).str.zfill(5)

    # Remapper arrondissements PLM
    result = remap_arrondissements(result, col="code_commune")
    if result["code_commune"].duplicated().any():
        numeric_cols = [c for c in result.columns if c != "code_commune"]
        result = result.groupby("code_commune", as_index=False)[numeric_cols].sum()

    # Normaliser pour 1 000 habitants
    from pipeline.config import DATA_PROCESSED_DIR

    pop_path = DATA_PROCESSED_DIR / "rp_population_2022.parquet"
    if pop_path.exists():
        pop = pd.read_parquet(pop_path, columns=["code_commune", "population"])
        result = result.merge(pop, on="code_commune", how="left")
        equip_cols = [c for c in result.columns if c.startswith("nb_equip_")]
        for col in equip_cols:
            norm_col = col.replace("nb_equip_", "equip_1000hab_")
            result[norm_col] = (result[col] / result["population"] * 1000).round(2)
        result["equipements_total_1000hab"] = (
            result["nb_equipements_total"] / result["population"] * 1000
        ).round(2)
        result = result.drop(columns=["population"])

    return result
