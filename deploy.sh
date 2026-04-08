#!/usr/bin/env bash
# =============================================================================
# VoteSocio — Script de déploiement
# =============================================================================
# Usage:
#   ./deploy.sh                        → pull, down, up (front seul)
#   ./deploy.sh --build                → build local au lieu de pull
#   ./deploy.sh --pipeline             → + pipeline complète (download+transform+load+export)
#   ./deploy.sh --pipeline-missing     → + pipeline seulement les sources manquantes
#   ./deploy.sh --export               → + export Parquet uniquement
#   ./deploy.sh --build --pipeline     → build local + pipeline complète
# =============================================================================

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_NAME="votesocio"

# --- Parse des arguments ---
BUILD_LOCAL=false
RUN_PIPELINE=""
RUN_EXPORT=false

for arg in "$@"; do
    case "$arg" in
        --build)           BUILD_LOCAL=true ;;
        --pipeline)        RUN_PIPELINE="all" ;;
        --pipeline-missing) RUN_PIPELINE="missing" ;;
        --export)          RUN_EXPORT=true ;;
        --help|-h)
            head -12 "$0" | tail -10
            exit 0
            ;;
        *)
            echo "Option inconnue : $arg"
            echo "Utiliser --help pour l'aide"
            exit 1
            ;;
    esac
done

echo "=== VoteSocio — Déploiement ==="
echo "→ FQDN : macommune.matge.com"
echo ""

# --- Réseau Traefik ---
docker network inspect ecosystem-network >/dev/null 2>&1 || {
    echo "→ Création du réseau ecosystem-network..."
    docker network create ecosystem-network
}

# --- Pull ou Build ---
if [ "$BUILD_LOCAL" = true ]; then
    echo "→ Build des images en local..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build web
    if [ -n "$RUN_PIPELINE" ] || [ "$RUN_EXPORT" = true ]; then
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools build pipeline export
    fi
else
    echo "→ Pull des images depuis GHCR..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" pull web
    if [ -n "$RUN_PIPELINE" ] || [ "$RUN_EXPORT" = true ]; then
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools pull pipeline export
    fi
fi

# --- Down ---
echo "→ Arrêt des services..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down --remove-orphans

# --- Pipeline de données ---
if [ -n "$RUN_PIPELINE" ]; then
    case "$RUN_PIPELINE" in
        all)
            echo "→ Pipeline complète (toutes les sources)..."
            docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools \
                run --rm pipeline python -m pipeline.run --all
            ;;
        missing)
            echo "→ Pipeline partielle (sources manquantes)..."
            docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools \
                run --rm pipeline python -m pipeline.run --all --skip-existing
            ;;
    esac
    # Export Parquet après le pipeline
    echo "→ Export Parquet..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools \
        run --rm export
elif [ "$RUN_EXPORT" = true ]; then
    echo "→ Export Parquet..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile tools \
        run --rm export
fi

# --- Up ---
echo "→ Démarrage du front-end..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d web

# --- Statut ---
echo ""
echo "→ Statut des services :"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
echo ""
echo "=== Déploiement terminé ==="
echo "→ https://macommune.matge.com"
