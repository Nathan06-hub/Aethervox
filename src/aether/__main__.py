"""Main entrypoint for Æther CLI / application."""

import sys
from aether.core.config import get_config
from aether.core.logger import setup_logger
from aether.storage import StorageManager


def main() -> None:
    """Application main entry point."""
    config = get_config()
    logger = setup_logger("aether.main")

    logger.info(f"Démarrage de {config.app_name} (v{config.version})")
    logger.info(f"Dossier de données : {config.app_data_dir}")
    logger.info(f"Fichier de base de données : {config.db_path}")

    # Initialisation du Module 1 (Persistance & Modèles)
    storage = StorageManager()
    storage.init_defaults()

    rules_count = len(storage.rules.list_all())
    active_procs = storage.rules.get_active_process_names()
    logger.info(f"Stockage initialisé avec succès : {rules_count} règles de blocage ({len(active_procs)} actives).")
    logger.info(f"Processus surveillés par défaut : {', '.join(sorted(active_procs))}")
    logger.info("Module 1 (Modèles & Persistance SQLite) prêt.")


if __name__ == "__main__":
    main()
