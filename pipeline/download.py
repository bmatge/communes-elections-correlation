"""Étape 1 — Téléchargement des sources de données.

Lit sources.yaml et télécharge chaque source selon son type de download.
Idempotent : ne re-télécharge pas si le fichier existe déjà (sauf --force).
"""

import io
import logging
import time
import zipfile
from pathlib import Path

import requests

from pipeline.config import DATA_RAW_DIR, get_sources, raw_path_for_source

logger = logging.getLogger(__name__)

# Timeout et retry
REQUEST_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # secondes, multiplié à chaque tentative

# User-Agent pour les serveurs INSEE qui bloquent les bots
HEADERS = {
    "User-Agent": "VoteSocio/1.0 (projet open data; contact@votesocio.fr)"
}


def download_file(url: str, dest: Path, timeout: int = REQUEST_TIMEOUT) -> Path:
    """Télécharge un fichier avec retry exponentiel."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("  Téléchargement (tentative %d/%d) : %s", attempt, MAX_RETRIES, url)
            resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
            resp.raise_for_status()

            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192 * 16):
                    f.write(chunk)
            tmp.rename(dest)

            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("  OK — %.1f Mo → %s", size_mb, dest.name)
            return dest

        except (requests.RequestException, IOError) as e:
            logger.warning("  Échec tentative %d : %s", attempt, e)
            # Nettoyer le fichier partiel
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                logger.info("  Retry dans %ds...", wait)
                time.sleep(wait)
            else:
                raise RuntimeError(f"Échec du téléchargement après {MAX_RETRIES} tentatives : {url}") from e

    raise RuntimeError("Unreachable")


def download_and_extract_zip(url: str, dest: Path, filename: str | None = None) -> Path:
    """Télécharge un ZIP et extrait le fichier cible."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("  Téléchargement ZIP (tentative %d/%d) : %s", attempt, MAX_RETRIES, url)
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                names = zf.namelist()
                logger.info("  Contenu du ZIP : %s", names[:10])

                if filename:
                    # Chercher le fichier exact ou par correspondance partielle
                    target = None
                    for name in names:
                        if name == filename or name.endswith("/" + filename):
                            target = name
                            break
                    if not target:
                        # Essayer une correspondance souple (sans chemin)
                        base = Path(filename).name
                        for name in names:
                            if Path(name).name == base:
                                target = name
                                break
                    if not target:
                        logger.warning("  Fichier '%s' non trouvé dans le ZIP. Fichiers disponibles : %s", filename, names)
                        # Prendre le premier CSV/XLSX
                        for name in names:
                            if name.lower().endswith((".csv", ".xlsx", ".xls", ".parquet")):
                                target = name
                                break
                    if not target:
                        raise FileNotFoundError(f"Aucun fichier exploitable dans le ZIP : {names}")
                else:
                    # Prendre le premier fichier de données
                    target = None
                    for name in names:
                        if name.lower().endswith((".csv", ".xlsx", ".xls", ".parquet")):
                            target = name
                            break
                    if not target:
                        target = names[0]

                logger.info("  Extraction : %s", target)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(target) as src, open(dest, "wb") as dst:
                    dst.write(src.read())

                size_mb = dest.stat().st_size / (1024 * 1024)
                logger.info("  OK — %.1f Mo → %s", size_mb, dest.name)
                return dest

        except (requests.RequestException, IOError, zipfile.BadZipFile) as e:
            logger.warning("  Échec tentative %d : %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
            else:
                raise RuntimeError(f"Échec après {MAX_RETRIES} tentatives : {url}") from e

    raise RuntimeError("Unreachable")


def download_source(source: dict, force: bool = False) -> Path | None:
    """Télécharge une source selon sa configuration.

    Retourne le chemin du fichier téléchargé, ou None si le type est 'custom'.
    """
    source_id = source["id"]
    download_cfg = source.get("download", {})
    dl_type = download_cfg.get("type", "direct_url")
    url = download_cfg.get("url", "")

    dest = raw_path_for_source(source)

    if dest.exists() and not force:
        logger.info("[%s] Déjà téléchargé : %s", source_id, dest.name)
        return dest

    logger.info("[%s] Téléchargement — type=%s", source_id, dl_type)

    if dl_type == "custom":
        logger.warning(
            "[%s] Type 'custom' — téléchargement manuel requis. "
            "Placer le fichier dans %s",
            source_id, dest
        )
        return None

    if dl_type == "direct_url":
        return download_file(url, dest)

    if dl_type == "insee_zip":
        filename = download_cfg.get("filename")
        # Les URLs INSEE pointent vers des pages, pas directement vers des fichiers.
        # On tente d'abord le téléchargement direct (certaines URLs sont directes).
        # Si c'est un ZIP, on extrait.
        try:
            return download_and_extract_zip(url, dest, filename)
        except (zipfile.BadZipFile, RuntimeError):
            # Pas un ZIP, essayer en téléchargement direct
            logger.info("  Pas un ZIP, tentative de téléchargement direct...")
            return download_file(url, dest)

    if dl_type == "geojson":
        # Pour les .gz, on garde le fichier compressé tel quel
        # (le transformer gère la décompression)
        return download_file(url, dest)

    logger.error("[%s] Type de téléchargement inconnu : %s", source_id, dl_type)
    return None


def download_all(force: bool = False, source_ids: list[str] | None = None) -> dict[str, Path | None]:
    """Télécharge toutes les sources (ou une sélection).

    Retourne un dict {source_id: path_or_none}.
    """
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    sources = get_sources()

    if source_ids:
        sources = [s for s in sources if s["id"] in source_ids]

    for source in sources:
        source_id = source["id"]
        try:
            path = download_source(source, force=force)
            results[source_id] = path
        except Exception:
            logger.exception("[%s] ERREUR de téléchargement", source_id)
            results[source_id] = None

    succeeded = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)
    logger.info("Téléchargement terminé : %d OK, %d échoués sur %d", succeeded, failed, len(results))

    return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Téléchargement des sources VoteSocio")
    parser.add_argument("--source", "-s", nargs="*", help="IDs des sources à télécharger")
    parser.add_argument("--force", "-f", action="store_true", help="Re-télécharger même si le fichier existe")
    args = parser.parse_args()

    download_all(force=args.force, source_ids=args.source)
