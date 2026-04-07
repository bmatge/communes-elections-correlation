-- =============================================================================
-- VoteSocio — Schéma DuckDB
-- =============================================================================
-- Modèle EAV extensible : ajouter des variables ne modifie jamais ce schéma.
-- =============================================================================

-- Table pivot des communes
CREATE TABLE IF NOT EXISTS communes (
    code_commune VARCHAR PRIMARY KEY,
    libelle VARCHAR,
    code_departement VARCHAR,
    code_region VARCHAR,
    population DOUBLE,
    superficie DOUBLE,
    densite DOUBLE,
    code_epci VARCHAR,
    libelle_epci VARCHAR
);

-- Registre de toutes les variables disponibles
CREATE TABLE IF NOT EXISTS variables_meta (
    variable_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    category VARCHAR NOT NULL,
    type VARCHAR NOT NULL DEFAULT 'numeric',  -- numeric | categorical | flag
    unit VARCHAR,
    year INTEGER
);

-- Valeurs numériques (EAV)
CREATE TABLE IF NOT EXISTS commune_data (
    code_commune VARCHAR NOT NULL,
    variable_id VARCHAR NOT NULL,
    value DOUBLE,
    PRIMARY KEY (code_commune, variable_id)
);

-- Valeurs catégorielles (EAV)
CREATE TABLE IF NOT EXISTS commune_data_cat (
    code_commune VARCHAR NOT NULL,
    variable_id VARCHAR NOT NULL,
    value VARCHAR,
    PRIMARY KEY (code_commune, variable_id)
);

-- Détail des résultats électoraux par liste/candidat et par commune
CREATE TABLE IF NOT EXISTS elections_raw (
    code_commune VARCHAR NOT NULL,
    id_election VARCHAR NOT NULL,
    nuance VARCHAR,
    famille VARCHAR,
    libelle_liste VARCHAR,
    inscrits INTEGER,
    votants INTEGER,
    exprimes INTEGER,
    voix INTEGER,
    pct_voix_exprimes DOUBLE,
    pct_voix_inscrits DOUBLE
);

-- Géométries des communes (résolution 50m — carte zoomée)
CREATE TABLE IF NOT EXISTS geo_communes (
    code_commune VARCHAR PRIMARY KEY,
    nom VARCHAR,
    geometry VARCHAR,  -- GeoJSON string du contour
    centroid_lat DOUBLE,
    centroid_lon DOUBLE
);

-- Géométries des communes basse résolution (1000m — vue France entière)
CREATE TABLE IF NOT EXISTS geo_communes_lowres (
    code_commune VARCHAR PRIMARY KEY,
    nom VARCHAR,
    geometry VARCHAR,
    centroid_lat DOUBLE,
    centroid_lon DOUBLE
);

-- Géométries des départements (50m)
CREATE TABLE IF NOT EXISTS geo_departements (
    code_departement VARCHAR PRIMARY KEY,
    nom VARCHAR,
    geometry VARCHAR,
    centroid_lat DOUBLE,
    centroid_lon DOUBLE
);

-- Géométries des régions (50m)
CREATE TABLE IF NOT EXISTS geo_regions (
    code_region VARCHAR PRIMARY KEY,
    nom VARCHAR,
    geometry VARCHAR,
    centroid_lat DOUBLE,
    centroid_lon DOUBLE
);

-- Coefficients de régression (pré-calculés par 04_analyze.py)
CREATE TABLE IF NOT EXISTS regression_coefficients (
    target_variable VARCHAR NOT NULL,
    predictor_variable VARCHAR NOT NULL,
    coefficient DOUBLE,
    std_error DOUBLE,
    t_stat DOUBLE,
    p_value DOUBLE,
    PRIMARY KEY (target_variable, predictor_variable)
);

-- Scores d'anomalie par commune (résidus de la régression)
CREATE TABLE IF NOT EXISTS anomalies (
    code_commune VARCHAR NOT NULL,
    target_variable VARCHAR NOT NULL,
    predicted DOUBLE,
    actual DOUBLE,
    residual DOUBLE,
    zscore DOUBLE,
    PRIMARY KEY (code_commune, target_variable)
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_commune_data_variable ON commune_data (variable_id);
CREATE INDEX IF NOT EXISTS idx_commune_data_cat_variable ON commune_data_cat (variable_id);
CREATE INDEX IF NOT EXISTS idx_elections_raw_election ON elections_raw (id_election, code_commune);
CREATE INDEX IF NOT EXISTS idx_variables_meta_category ON variables_meta (category);
