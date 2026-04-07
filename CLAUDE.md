# CLAUDE.md — VoteSocio

## Projet

VoteSocio croise les résultats des élections municipales 2026 avec les indicateurs
socio-économiques communaux pour cartographier les stéréotypes électoraux et leurs exceptions.

## Stack technique

- **Langage** : Python 3.11+
- **BDD** : DuckDB (fichier local `db/votesocio.duckdb`)
- **Pipeline** : scripts Python séquentiels (`pipeline/`)
- **Analyse** : pandas, scikit-learn, statsmodels
- **Front** : SvelteKit 2 (static) + DuckDB-WASM (requêtes SQL dans le navigateur)
- **Carto** : GeoJSON des contours communaux + Maplibre GL
- **Conteneurisation** : Docker (nginx pour le front, Python pour le pipeline)
- **CI/CD** : GitHub Actions (lint, tests, build, Docker)

## Architecture — principes fondamentaux

### 1. Registry déclaratif (`pipeline/sources.yaml`)

Chaque source de données est décrite dans `sources.yaml`, pas dans du code.
Ajouter une source = ajouter un bloc YAML. Le pipeline lit le registry et opère
de façon générique.

### 2. Schéma EAV extensible

La BDD utilise un modèle Entity-Attribute-Value :
- `communes` : table pivot (code_commune, libellé, département, population, superficie)
- `variables_meta` : registre de toutes les variables (nom, source, catégorie, type)
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
├── docs/
│   ├── architecture.md        ← doc d'architecture détaillée
│   └── telechargements_manuels.md ← instructions pour les fichiers INSEE
├── pipeline/
│   ├── sources.yaml           ← registry déclaratif (38 sources, 4 couches)
│   ├── run.py                 ← orchestrateur CLI (--source, --step, --list)
│   ├── config.py              ← chargement config, chemins projet
│   ├── download.py            ← téléchargement générique (direct_url, insee_zip)
│   ├── transform.py           ← nettoyage, mapping colonnes, formules
│   ├── load.py                ← chargement DuckDB + vue communes_wide
│   ├── downloaders/           ← (réservé pour stratégies custom)
│   └── transformers/          ← transformers custom par source
│       ├── elections.py       ← agrégation multi-élections + familles politiques
│       ├── delinquance.py     ← taux par catégorie d'infraction
│       ├── dvf.py             ← prix médian au m²
│       ├── ips.py             ← IPS moyen par commune
│       ├── qpv.py             ← flag QPV + nb quartiers
│       ├── zrr.py             ← flag ZRR
│       ├── rna.py             ← densité associative
│       ├── annuaire_education.py ← comptage écoles/collèges/lycées
│       ├── apl.py             ← accessibilité médecins
│       ├── fibre.py           ← taux couverture FTTH
│       ├── geo_contours.py    ← parse GeoJSON → géométries communes/dept/régions
│       └── __init__.py
├── tests/                     ← 35 tests (pytest)
│   ├── test_config.py         ← tests config et sources.yaml
│   ├── test_download.py       ← tests téléchargement
│   ├── test_transform.py      ← tests transformation + transformers
│   └── test_load.py           ← tests schéma DuckDB + chargement
├── analysis/
│   └── notebooks/             ← exploration Jupyter (à venir)
├── db/
│   ├── schema.sql             ← DDL de la BDD
│   └── votesocio.duckdb       ← fichier BDD (gitignored)
├── data/
│   ├── raw/                   ← fichiers téléchargés (gitignored)
│   └── processed/             ← fichiers transformés (gitignored)
├── web/                       ← front-end SvelteKit
│   ├── src/
│   │   ├── lib/
│   │   │   └── db.ts          ← wrapper DuckDB-WASM (initDB, query, queryOne)
│   │   └── routes/            ← pages SvelteKit
│   ├── static/data/           ← fichiers Parquet exportés (gitignored)
│   ├── Dockerfile             ← multi-stage: build Node → serve nginx
│   ├── nginx.conf             ← config nginx (SPA + WASM + Parquet)
│   └── package.json
├── docker-compose.yml         ← services: web, pipeline, export
├── Dockerfile.pipeline        ← image Python pour le pipeline
├── .github/workflows/ci.yml  ← CI/CD GitHub Actions
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

# --- Front-end ---

# Dev local (hot reload)
cd web && npm run dev

# Build statique
cd web && npm run build

# Export DuckDB → Parquet pour le front
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
4. Lancer `python -m pipeline.run --source <source_id>`
5. Les variables sont auto-détectées dans le DataFrame transformé et enregistrées dans `variables_meta`
6. La vue `communes_wide` se régénère automatiquement
