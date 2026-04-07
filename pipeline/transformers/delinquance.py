"""Transformer délinquance : taux agrégé par commune (année la plus récente)."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    df = df.rename(columns={"CODGEO_2025": "code_commune"})

    from pipeline.transformers import remap_arrondissements

    df = remap_arrondissements(df, col="code_commune")

    # Garder l'année la plus récente
    annee_max = df["annee"].max()
    df = df[df["annee"] == annee_max]

    # Ne garder que les données diffusées (valeur = "diff")
    if "est_diffuse" in df.columns:
        df = df[df["est_diffuse"] == "diff"]

    # Agréger : somme des faits, taux moyen pondéré
    agg = df.groupby("code_commune").agg(
        nb_faits_total=("nombre", "sum"),
        population=("insee_pop", "first"),
    ).reset_index()

    # Taux pour 1000 habitants
    agg["taux_delinquance_1000"] = (
        agg["nb_faits_total"] / agg["population"] * 1000
    ).round(2)

    # Garder aussi le détail par grande catégorie
    categories_atteintes_personnes = [
        "Homicides", "Tentatives d'homicide",
        "Violences physiques intrafamiliales",
        "Violences physiques hors cadre familial",
        "Violences sexuelles",
    ]
    categories_atteintes_biens = [
        "Cambriolages de logement", "Vols de véhicule",
        "Vols dans les véhicules", "Vols d'accessoires sur véhicules",
        "Vols sans violence contre des personnes",
        "Vols avec armes", "Vols violents sans arme",
    ]

    for cat_name, cat_list in [
        ("taux_atteintes_personnes", categories_atteintes_personnes),
        ("taux_atteintes_biens", categories_atteintes_biens),
    ]:
        sub = df[df["indicateur"].isin(cat_list)]
        cat_agg = sub.groupby("code_commune")["nombre"].sum().reset_index()
        cat_agg = cat_agg.rename(columns={"nombre": f"nb_{cat_name}"})
        agg = agg.merge(cat_agg, on="code_commune", how="left")
        agg[cat_name] = (agg[f"nb_{cat_name}"] / agg["population"] * 1000).round(2)
        agg = agg.drop(columns=[f"nb_{cat_name}"])

    result = agg[["code_commune", "taux_delinquance_1000", "taux_atteintes_personnes", "taux_atteintes_biens"]]
    return result
