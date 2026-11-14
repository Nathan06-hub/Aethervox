"""Main entrypoint for Æther CLI / application."""

import sys
from aether.core.config import get_config
from aether.core.logger import setup_logger


def main() -> None:
    """Application main entry point."""
    config = get_config()
    logger = setup_logger("aether.main")

    logger.info(f"Démarrage de {config.app_name} (v{config.version})")
    logger.info(f"Dossier de données : {config.app_data_dir}")
    logger.info(f"Fichier de base de données : {config.db_path}")
    logger.info("Module 0 opérationnel. Prêt pour le Module 1 (Stockage & Modèles).")


if __name__ == "__main__":
    main()
