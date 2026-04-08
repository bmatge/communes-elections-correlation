# VoteSocio

Analyse écologique croisant les résultats des **élections municipales 2026** avec les **indicateurs socio-économiques** des 35 000 communes françaises.

L'objectif : cartographier les stéréotypes électoraux (cadres → gauche, ouvriers → ED, HLM → gauche...) et identifier les communes qui y échappent.

## Chiffres clés

- **259 variables** × **34 965 communes** — 6.7M valeurs
- **27 sources** : INSEE (RP, IC, Filosofi, BPE), data.gouv.fr, OFGL
- **11 scrutins** : présidentielles 2017/2022, législatives 2022/2024, européennes 2024, régionales/départementales 2021, municipales 2020/2026
- **10 catégories** : électoral, territoire, emploi, éducation, logement, revenus, vie locale, sécurité, santé, transport

## Analyses

| Analyse | Description | Table DuckDB |
|---|---|---|
| **Corrélations** | Matrice socio-éco × scores électoraux | `correlation_matrix` |
| **Z-scores** | Écart de chaque commune à son département | `commune_zscores` |
| **Régression OLS** | 10 modèles, 21 features, R² 0.35–0.54 | `regression_results`, `commune_residuals` |
| **Clustering** | 8 profils-types (K-Means + ACP) | `commune_clusters`, `cluster_profiles` |
| **Décalage** | Gap municipales vs présidentielles/législatives | `decalage_local_national` |

## Front-end

Application SvelteKit statique avec DuckDB-WASM — toutes les requêtes SQL s'exécutent dans le navigateur.

| Page | Description |
|---|---|
| **Carte** | Choroplèthe avec palettes politiques, légende, 259 variables au choix |
| **Commune** | Fiche complète : profil socio-éco, scores électoraux, anomalies, z-scores, cluster |
| **Simulateur** | 21 curseurs socio-éco → prédiction temps réel des scores électoraux (OLS) |

## Stack

```
Pipeline :  Python 3.11 → DuckDB → Parquet
Analyse  :  pandas, scikit-learn, statsmodels, scipy
Front    :  SvelteKit 2 (Svelte 5 runes) + DuckDB-WASM + Maplibre GL
Infra    :  Docker (nginx) + GitHub Actions
```

## Démarrage rapide

```bash
# Installer les dépendances Python
pip install -r requirements.txt

# Lancer le pipeline (download + transform + load)
python -m pipeline.run --all

# Lancer l'analyse
python -m analysis.correlations
python -m analysis.zscores
python -m analysis.regression
python -m analysis.clustering
python -m analysis.decalage

# Exporter pour le front
python -m pipeline.export_parquet

# Lancer le front (dev)
cd web && npm install && npm run dev
```

## Architecture

```
sources.yaml ──→ download ──→ transform ──→ load (DuckDB)
                                  │              │
                           remap PLM        analyse (OLS, K-Means, z-scores)
                                              │
                                    export_parquet (17 tables)
                                              │
                                  SvelteKit + DuckDB-WASM
```

### Principes

1. **Registry déclaratif** — ajouter une source = ajouter du YAML, pas du code
2. **Schéma EAV extensible** — ajouter des variables ne modifie jamais le schéma SQL
3. **Pipeline idempotent** — chaque étape est rejouable indépendamment
4. **Arrondissements PLM** — Paris/Lyon/Marseille agrégés automatiquement
5. **Données dans le navigateur** — DuckDB-WASM exécute les requêtes côté client

## Sources de données

### Noyau
- **Filosofi 2021** — revenus, pauvreté, déciles
- **RP 2021/2022** — population, diplômes, CSP, logement, mobilité
- **Bases IC 2021** — population, logement, activité, ménages (IRIS agrégé)
- **Élections** — 11 scrutins agrégés par famille politique (data.gouv.fr)

### Enrichissement
- **BPE 2024** — équipements par domaine (bruts + normalisés /1000 hab)
- **DVF** — prix médian au m²
- **IPS** — indice de position sociale (écoles, collèges)
- **APL** — accessibilité aux médecins
- **Délinquance** — taux par catégorie
- **Fiscalité locale** — taux TFB + potentiel fiscal (OFGL/DGFiP)
- **Loyers, fibre, RNA, QPV, ZRR, EPCI, GeoJSON**

## Avertissement

Ce projet utilise des **corrélations écologiques** (données communales agrégées). Les résultats ne peuvent pas être interprétés au niveau individuel (*ecological fallacy*). Un quartier ouvrier qui vote à gauche ne signifie pas que ce sont les ouvriers qui votent à gauche.

## Licence

Données : licences ouvertes respectives des producteurs (INSEE, data.gouv.fr, OFGL).
Code : MIT.
