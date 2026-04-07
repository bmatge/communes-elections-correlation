"""Orchestrateur du pipeline VoteSocio.

Usage :
    python -m pipeline.run --all                    # Tout relancer
    python -m pipeline.run --source filosofi_2021   # Une seule source
    python -m pipeline.run --step download          # Seulement une étape
    python -m pipeline.run --step download --source filosofi_2021
    python -m pipeline.run --force                  # Re-télécharger et re-transformer
"""

import argparse
import logging
import sys
import time

from pipeline.config import get_source_by_id, get_sources

logger = logging.getLogger(__name__)

STEPS = ["download", "transform", "load"]


def run_pipeline(
    steps: list[str] | None = None,
    source_ids: list[str] | None = None,
    force: bool = False,
) -> None:
    """Exécute les étapes demandées du pipeline."""
    if steps is None:
        steps = STEPS

    # Valider les source_ids
    if source_ids:
        for sid in source_ids:
            if get_source_by_id(sid) is None:
                available = [s["id"] for s in get_sources()]
                logger.error("Source inconnue : '%s'. Sources disponibles :\n  %s", sid, "\n  ".join(sorted(available)))
                sys.exit(1)

    start = time.time()
    logger.info("=" * 60)
    logger.info("VoteSocio Pipeline")
    logger.info("Étapes : %s", " → ".join(steps))
    if source_ids:
        logger.info("Sources : %s", ", ".join(source_ids))
    else:
        logger.info("Sources : toutes (%d)", len(get_sources()))
    logger.info("Force : %s", force)
    logger.info("=" * 60)

    if "download" in steps:
        logger.info("")
        logger.info("━━━ ÉTAPE 1/3 : TÉLÉCHARGEMENT ━━━")
        from pipeline.download import download_all
        download_all(force=force, source_ids=source_ids)

    if "transform" in steps:
        logger.info("")
        logger.info("━━━ ÉTAPE 2/3 : TRANSFORMATION ━━━")
        from pipeline.transform import transform_all
        transform_all(force=force, source_ids=source_ids)

    if "load" in steps:
        logger.info("")
        logger.info("━━━ ÉTAPE 3/3 : CHARGEMENT DUCKDB ━━━")
        from pipeline.load import load_all
        load_all(source_ids=source_ids)

    elapsed = time.time() - start
    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline terminé en %.1f secondes", elapsed)
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestrateur du pipeline VoteSocio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python -m pipeline.run --all
  python -m pipeline.run --source filosofi_2021 rp_logement_2021
  python -m pipeline.run --step download --force
  python -m pipeline.run --step transform load --source filosofi_2021
        """,
    )
    parser.add_argument("--all", action="store_true", help="Exécuter toutes les étapes pour toutes les sources")
    parser.add_argument("--step", nargs="*", choices=STEPS, help="Étapes à exécuter (download, transform, load)")
    parser.add_argument("--source", "-s", nargs="*", help="IDs des sources à traiter")
    parser.add_argument("--force", "-f", action="store_true", help="Forcer le re-téléchargement et la re-transformation")
    parser.add_argument("--list", action="store_true", help="Lister toutes les sources disponibles")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le logging DEBUG")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list:
        sources = get_sources()
        print(f"\n{len(sources)} sources disponibles :\n")
        for s in sources:
            tier = s.get("tier", "")
            tier_str = f" [{tier}]" if tier else ""
            print(f"  {s['id']:40s} {s.get('category', ''):15s} {s.get('name', '')}{tier_str}")
        return

    steps = args.step if args.step else STEPS
    source_ids = args.source

    if not args.all and not args.source and not args.step:
        parser.print_help()
        return

    run_pipeline(steps=steps, source_ids=source_ids, force=args.force)


if __name__ == "__main__":
    main()
