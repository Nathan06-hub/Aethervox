"""SQLite database manager with WAL mode, foreign keys, and context-managed transactions."""

import sqlite3
from pathlib import Path
from typing import Generator
from contextlib import contextmanager
import logging

from aether.core.config import get_config
from aether.core.logger import setup_logger

logger = setup_logger("aether.storage.db")


# Schéma SQL DDL de création des tables et des index
SCHEMA_SQL = """
-- Table des créneaux fixes de cours (Emploi du temps universitaire)
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT,
    color TEXT DEFAULT '#4F46E5',
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_courses_day ON courses(day_of_week, is_active);

-- Table des sessions d'étude et de pause générées ou saisies
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    session_type TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_dates ON study_sessions(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON study_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_course ON study_sessions(course_id);

-- Table des règles de blocage (Liste noire de discipline)
CREATE TABLE IF NOT EXISTS distraction_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    severity TEXT NOT NULL DEFAULT 'kill',
    window_title_keyword TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rules_proc ON distraction_rules(process_name);
CREATE INDEX IF NOT EXISTS idx_rules_active ON distraction_rules(is_active);

-- Table de journalisation des violations / infractions interceptées
CREATE TABLE IF NOT EXISTS violation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES study_sessions(id) ON DELETE SET NULL,
    rule_id INTEGER REFERENCES distraction_rules(id) ON DELETE SET NULL,
    process_name TEXT NOT NULL,
    process_pid INTEGER,
    window_title TEXT,
    action_taken TEXT NOT NULL DEFAULT 'KILLED',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violation_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_violations_session ON violation_events(session_id);
CREATE INDEX IF NOT EXISTS idx_violations_proc ON violation_events(process_name);

-- Table des paramètres dynamiques et préférences locales
CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT NOT NULL
);
"""


class Database:
    """Gestionnaire de persistance SQLite pour Æther.

    Fonctionnalités clés :
    - Mode WAL (Write-Ahead Logging) pour lectures/écritures concurrentes fluides
    - Activation obligatoire des clés étrangères (PRAGMA foreign_keys = ON)
    - Accès colonnes par nom via sqlite3.Row
    - Gestion robuste des transactions avec commit automatique et rollback sur erreur
    - Support des bases en mémoire (:memory:) pour les tests unitaires
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialise la base de données.

        Args:
            db_path: Chemin du fichier SQLite ou ':memory:'. Si omis, utilise config.db_path.
        """
        if db_path is None:
            self.db_path = get_config().db_path
        elif isinstance(db_path, str) and db_path == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        # Si base en mémoire, conserver une connexion persistante pour que les tables survivent
        self._memory_conn: sqlite3.Connection | None = None
        if self.is_memory:
            self._memory_conn = self._create_connection()

        self.initialize_schema()

    @property
    def is_memory(self) -> bool:
        """Vérifie si la base tourne en mémoire RAM."""
        return self.db_path == ":memory:"

    def _create_connection(self) -> sqlite3.Connection:
        """Crée et configure une nouvelle connexion SQLite avec les pragmas requis."""
        if not self.is_memory and isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        target = ":memory:" if self.is_memory else str(self.db_path)
        conn = sqlite3.connect(
            target,
            timeout=5.0,  # 5s busy timeout
            check_same_thread=False,
        )

        conn.row_factory = sqlite3.Row

        # Configuration des pragmas critiques
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        if not self.is_memory:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.close()

        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager fournissant une connexion active avec transaction sécurisée.

        Effectue un commit automatique si le bloc s'exécute sans erreur,
        ou un rollback en cas d'exception.
        """
        if self.is_memory:
            assert self._memory_conn is not None
            conn = self._memory_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        else:
            conn = self._create_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def initialize_schema(self) -> None:
        """Crée toutes les tables et index si nécessaire."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
        logger.debug(f"Schéma de base de données initialisé ({self.db_path})")

    def reset_database(self) -> None:
        """Supprime et recrée toutes les tables (utilitaire de test ou reset usine)."""
        tables = ["violation_events", "distraction_rules", "study_sessions", "courses", "user_settings"]
        with self.get_connection() as conn:
            for table in tables:
                conn.execute(f"DROP TABLE IF EXISTS {table};")
        self.initialize_schema()
        logger.info("Base de données réinitialisée avec succès.")

    def close(self) -> None:
        """Ferme la connexion si c'était une base en mémoire."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None
