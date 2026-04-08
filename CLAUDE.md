# CLAUDE.md — VoteSocio

## Projet

VoteSocio croise les résultats des élections municipales 2026 avec les indicateurs
socio-économiques communaux pour cartographier les stéréotypes électoraux et leurs exceptions.

**État actuel** : 259 variables × 34 965 communes, 6.7M valeurs, 27 sources, pipeline complet + analyse + front interactif.

## Stack technique

- **Langage** : Python 3.11+
- **BDD** : DuckDB (fichier local `db/votesocio.duckdb`)
- **Pipeline** : scripts Python séquentiels (`pipeline/`)
- **Analyse** : pandas, scikit-learn, statsmodels, scipy (`analysis/`)
- **Front** : SvelteKit 2 (static) + DuckDB-WASM (requêtes SQL dans le navigateur)
- **Carto** : GeoJSON des contours communaux + Maplibre GL
- **Conteneurisation** : Docker (nginx pour le front, Python pour le pipeline)
- **CI/CD** : GitHub Actions (lint, tests, build, Docker)
- **Géo** : shapely + pyproj (calcul superficie Lambert-93)

## Architecture — principes fondamentaux

### 1. Registry déclaratif (`pipeline/sources.yaml`)

Chaque source de données est décrite dans `sources.yaml`, pas dans du code.
Ajouter une source = ajouter un bloc YAML. Le pipeline lit le registry et opère
de façon générique.

### 2. Schéma EAV extensible

La BDD utilise un modèle Entity-Attribute-Value :
- `communes` : table pivot (code_commune, libellé, département, population, superficie, densité)
- `variables_meta` : registre de toutes les variables (nom, source, catégorie, type, display, relative_id)
- `commune_data` : table longue (code_commune, variable_id, value)
- `commune_data_cat` : idem pour les variables catégorielles
- `communes_wide` : vue matérialisée pivotée, régénérée automatiquement

Ajouter des variables ne nécessite JAMAIS de modifier le schéma SQL.

### 3. Pipeline en étapes

```
sources.yaml → 01_download → 02_transform → 03_load → 04_analyze
```

Chaque étape est idempotente et rejouable indépendamment.

### 4. Données électorales

Les résultats électoraux sont stockés dans `commune_data` comme les autres variables
(score_gauche, score_droite, score_exd, pct_abstention, etc.), ce qui permet de les
corréler directement avec les variables socio-éco sans traitement spécial.

### 5. Arrondissements PLM

Paris (75101-75120), Lyon (69381-69389), Marseille (13201-13216) sont remappés vers
leur code commune unique (75056, 69123, 13055) dans tous les transformers via la
fonction partagée `remap_arrondissements()` dans `pipeline/transformers/__init__.py`.

### 6. Tables d'analyse

Les scripts `analysis/` produisent des tables dans DuckDB, exportées en Parquet pour le front :
- `correlation_matrix` : corrélations socio-éco × scores électoraux
- `commune_zscores` : écart de chaque commune à la moyenne de son département
- `regression_results` + `regression_scaler` : coefficients OLS + stats de normalisation
- `commune_residuals` : résidus (communes « surprenantes »)
- `commune_clusters` + `cluster_profiles` : clustering K-Means
- `pca_loadings` : composantes ACP
- `decalage_local_national` : gap entre vote municipal et vote national

## Conventions de code

### Python
- Style : PEP 8, formaté avec `ruff format`
- Lint : `ruff check`
- Imports : stdlib → tiers → locaux, séparés par une ligne vide
- Pas de classes quand des fonctions suffisent
- Typage : annotations de type sur les signatures de fonctions publiques
- Docstrings : uniquement sur les fonctions non triviales, format one-liner ou numpy

### Nommage
- Variables Python : `snake_case`
- Variables de données / colonnes : `snake_case` (ex: `revenu_median`, `score_gauche`)
- Sources dans le registry : `snake_case` avec un id court (ex: `filosofi_2021`, `rp_logement_2021`)
- Catégories de variables : `revenus`, `emploi`, `logement`, `education`, `transport`, `securite`, `sante`, `vie_locale`, `territoire`, `electoral`

### Fichiers
- Un module = un fichier. Pas de packages complexes sauf nécessité.
- Les transformers custom vont dans `pipeline/transformers/<source_id>.py`
- Les downloaders custom vont dans `pipeline/downloaders/<type>.py`
- Les scripts d'analyse vont dans `analysis/<nom>.py`

### SQL (DuckDB)
- Mots-clés en MAJUSCULES
- Noms de tables et colonnes en `snake_case`
- Une instruction par ligne pour les requêtes longues

### TypeScript / Svelte
- Svelte 5 avec runes (`$state`, `$derived`, `$effect`)
- Pas de stores Svelte classiques → utiliser les runes
- Requêtes SQL via `query()` / `queryOne()` de `$lib/db.ts`
- Composants dans `src/lib/components/`, pages dans `src/routes/`
- Le front découvre les variables dynamiquement via `variables_meta` (pas de listes hardcodées)

### Git
- Commits atomiques, un sujet par commit
- Messages en français, impératif présent (ex: "Ajouter le transformer FILOSOFI")
- Pas de fichiers de données (CSV, Parquet, DuckDB) dans le repo → `.gitignore`

## Structure du projet

```
votesocio/
├── CLAUDE.md                  ← ce fichier
├── README.md                  ← présentation projet
├── docs/
│   ├── architecture.md        ← doc d'architecture détaillée
│   └── telechargements_manuels.md ← instructions pour les fichiers INSEE
├── pipeline/
│   ├── sources.yaml           ← registry déclaratif (40+ sources, 4 couches)
│   ├── run.py                 ← orchestrateur CLI (--source, --step, --list)
│   ├── config.py              ← chargement config, chemins projet
│   ├── download.py            ← téléchargement générique (direct_url, insee_zip)
│   ├── transform.py           ← nettoyage, mapping colonnes, formules, remapping PLM
│   ├── load.py                ← chargement DuckDB + superficie + vue communes_wide
│   ├── export_parquet.py      ← export DuckDB → Parquet pour le front (17 tables)
│   ├── downloaders/           ← (réservé pour stratégies custom)
│   └── transformers/          ← transformers custom par source
│       ├── __init__.py        ← remap_arrondissements() PLM partagé
│       ├── elections.py       ← agrégation multi-élections + familles politiques
│       ├── delinquance.py     ← taux par catégorie d'infraction
│       ├── dvf.py             ← prix médian au m²
│       ├── ips.py             ← IPS moyen par commune
│       ├── bpe.py             ← équipements + normalisation /1000 hab
│       ├── ic_population.py   ← CSP, immigrés (IRIS → commune)
│       ├── ic_logement.py     ← HLM, rés.secondaires, vacants
│       ├── ic_activite.py     ← activité, chômage
│       ├── ic_menages.py      ← ménages, monoparentales, taille
│       ├── rp_population.py   ← population, tranches d'âge
│       ├── rp_diplomes.py     ← niveaux de diplôme
│       ├── rp_mobilite.py     ← flux résidentiels, sédentarité
│       ├── qpv.py             ← flag QPV + nb quartiers
│       ├── zrr.py             ← flag ZRR
│       ├── rna.py             ← densité associative
│       ├── annuaire_education.py ← comptage écoles/collèges/lycées
│       ├── apl.py             ← accessibilité médecins
│       ├── fibre.py           ← taux couverture FTTH
│       └── geo_contours.py    ← parse GeoJSON → géométries
├── analysis/                  ← scripts d'analyse
│   ├── correlations.py        ← matrice de corrélation
│   ├── zscores.py             ← z-scores départementaux
│   ├── regression.py          ← OLS multivariée + résidus
│   ├── clustering.py          ← K-Means + ACP
│   └── decalage.py            ← décalage local/national
├── tests/                     ← 35 tests (pytest)
│   ├── test_config.py
│   ├── test_download.py
│   ├── test_transform.py
│   └── test_load.py
├── db/
│   ├── schema.sql             ← DDL de la BDD
│   └── votesocio.duckdb       ← fichier BDD (gitignored)
├── data/
│   ├── raw/                   ← fichiers téléchargés (gitignored)
│   └── processed/             ← fichiers transformés (gitignored)
├── web/                       ← front-end SvelteKit
│   ├── src/
│   │   ├── app.css            ← design system (dark, typo éditoriale)
│   │   ├── lib/
│   │   │   ├── db.ts          ← wrapper DuckDB-WASM (initDB, query, queryOne)
│   │   │   └── components/
│   │   │       ├── Map.svelte          ← carte choroplèthe Maplibre GL
│   │   │       ├── CommuneProfile.svelte ← fiche commune complète
│   │   │       ├── CommuneSearch.svelte  ← recherche autocomplete
│   │   │       ├── VariableSelector.svelte ← sélecteur par catégorie
│   │   │       ├── Header.svelte
│   │   │       └── Footer.svelte
│   │   └── routes/
│   │       ├── +page.svelte           ← accueil
│   │       ├── carte/+page.svelte     ← page carte
│   │       ├── commune/+page.svelte   ← page fiche commune
│   │       └── simulateur/+page.svelte ← simulateur régression
│   ├── static/data/           ← fichiers Parquet exportés (17 tables)
│   ├── Dockerfile             ← multi-stage: build Node → serve nginx
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── Dockerfile.pipeline
├── .github/workflows/ci.yml
├── requirements.txt
└── .gitignore
```

## Ce qu'il ne faut PAS faire

- Ne pas hardcoder de chemins de fichiers → utiliser des chemins relatifs à la racine du projet
- Ne pas stocker de données dans le repo (tout dans `.gitignore`)
- Ne pas modifier le schéma SQL pour ajouter une variable → utiliser le registry YAML
- Ne pas créer de dépendances circulaires entre les étapes du pipeline
- Ne pas faire de requêtes API sans cache/retry (les serveurs INSEE tombent souvent)
- Ne pas ignorer les communes DOM-TOM sans le documenter explicitement
- Ne pas confondre corrélation territoriale et causalité individuelle (ecological fallacy)
- Ne pas sommer des taux/moyennes lors de l'agrégation d'arrondissements → pondérer ou recalculer

## Commandes utiles

```bash
# Lister toutes les sources
python -m pipeline.run --list

# Pipeline complet (toutes les sources)
python -m pipeline.run --all

# Pipeline sur une ou plusieurs sources
python -m pipeline.run --source filosofi_2021 rp_logement_2021

# Seulement une étape
python -m pipeline.run --step download --source filosofi_2021
python -m pipeline.run --step transform load --source filosofi_2021

# Forcer le re-téléchargement
python -m pipeline.run --source loyers_2025 --force

# Tests
python -m pytest tests/ -v

# --- Analyse ---

# Corrélations
python -m analysis.correlations

# Z-scores départementaux
python -m analysis.zscores

# Régression multivariée
python -m analysis.regression

# Clustering + ACP
python -m analysis.clustering

# Décalage local/national
python -m analysis.decalage

# --- Front-end ---

# Dev local (hot reload)
cd web && npm run dev

# Build statique
cd web && npm run build

# Type-check Svelte
cd web && npm run check

# Export DuckDB → Parquet pour le front (17 tables)
python -m pipeline.export_parquet

# --- Docker ---

# Front-end de production
docker compose up web

# Pipeline complet + export
docker compose --profile tools up pipeline export
```

## Ajouter une nouvelle source de données

1. Ajouter un bloc dans `pipeline/sources.yaml` avec : id, name, type, url, join_key, variables
2. Si le format est standard (CSV, Parquet avec colonnes à mapper) → aucun code nécessaire
3. Si le nettoyage est atypique → créer `pipeline/transformers/<source_id>.py` avec une fonction `transform(df, source) -> df`
4. Penser à appeler `remap_arrondissements()` si le transformer custom fait un groupby (PLM)
5. Lancer `python -m pipeline.run --source <source_id>`
6. Les variables sont auto-détectées dans le DataFrame transformé et enregistrées dans `variables_meta`
7. La vue `communes_wide` se régénère automatiquement
8. Relancer l'analyse (`python -m analysis.correlations`, etc.) pour intégrer les nouvelles variables
9. Re-exporter les Parquet (`python -m pipeline.export_parquet`)
