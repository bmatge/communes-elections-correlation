# =============================================================================
# VoteSocio — Front-end (SvelteKit static + DuckDB-WASM)
# Multi-stage: build → serve avec nginx
# =============================================================================

# --- Stage 1 : Build ---
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Stage 2 : Serve ---
FROM nginx:alpine AS production

# Config nginx optimisée pour SPA + fichiers Parquet
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copier le build statique
COPY --from=build /app/build /usr/share/nginx/html

# Les fichiers Parquet sont montés en volume ou copiés à part
# (voir docker-compose.yml)

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD wget -qO- http://localhost/ || exit 1
