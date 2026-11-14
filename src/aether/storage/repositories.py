"""Data Access Object (DAO) / Repository implementations for Æther domain entities."""

from datetime import datetime
from typing import Any
import sqlite3

from aether.storage.database import Database
from aether.storage.models import (
    Course,
    CourseCreate,
    DayOfWeek,
    DistractionRule,
    DistractionRuleCreate,
    RuleCategory,
    RuleSeverity,
    SessionStatus,
    SessionType,
    StudySession,
    StudySessionCreate,
    StudySessionUpdate,
    UserSetting,
    ViolationEvent,
    ViolationEventCreate,
)


class BaseRepository:
    """Classe de base fournissant la référence vers l'instance Database."""

    def __init__(self, db: Database) -> None:
        self.db = db


# ============================================================================
# CourseRepository
# ============================================================================

class CourseRepository(BaseRepository):
    """Accès aux données pour les créneaux de cours universitaires."""

    def create(self, course: CourseCreate) -> Course:
        """Insère un nouveau cours en base."""
        created_at = datetime.now().isoformat()
        query = """
            INSERT INTO courses (
                name, code, day_of_week, start_time, end_time, location, color, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            course.name,
            course.code,
            int(course.day_of_week),
            course.start_time,
            course.end_time,
            course.location,
            course.color,
            1 if course.is_active else 0,
            created_at,
        )
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            new_id = cursor.lastrowid
            assert new_id is not None
            cursor.execute("SELECT * FROM courses WHERE id = ?;", (new_id,))
            row = cursor.fetchone()
            return Course.model_validate(dict(row))

    def get_by_id(self, course_id: int) -> Course | None:
        """Récupère un cours par son ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses WHERE id = ?;", (course_id,))
            row = cursor.fetchone()
            return Course.model_validate(dict(row)) if row else None

    def list_all(self, active_only: bool = False) -> list[Course]:
        """Retourne la liste ordonnée des cours (par jour puis heure de début)."""
        query = """
            SELECT * FROM courses
            WHERE (? = 0 OR is_active = 1)
            ORDER BY day_of_week ASC, start_time ASC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (1 if active_only else 0,))
            return [Course.model_validate(dict(row)) for row in cursor.fetchall()]

    def get_by_day(self, day_of_week: DayOfWeek | int, active_only: bool = True) -> list[Course]:
        """Retourne les cours d'un jour spécifique de la semaine."""
        day_val = int(day_of_week)
        query = """
            SELECT * FROM courses
            WHERE day_of_week = ? AND (? = 0 OR is_active = 1)
            ORDER BY start_time ASC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (day_val, 1 if active_only else 0))
            return [Course.model_validate(dict(row)) for row in cursor.fetchall()]

    def update(self, course_id: int, course: CourseCreate) -> Course | None:
        """Met à jour les informations d'un cours existant."""
        query = """
            UPDATE courses
            SET name = ?, code = ?, day_of_week = ?, start_time = ?, end_time = ?,
                location = ?, color = ?, is_active = ?
            WHERE id = ?;
        """
        params = (
            course.name,
            course.code,
            int(course.day_of_week),
            course.start_time,
            course.end_time,
            course.location,
            course.color,
            1 if course.is_active else 0,
            course_id,
        )
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if cursor.rowcount == 0:
                return None
            cursor.execute("SELECT * FROM courses WHERE id = ?;", (course_id,))
            row = cursor.fetchone()
            return Course.model_validate(dict(row)) if row else None

    def delete(self, course_id: int) -> bool:
        """Supprime un cours par son ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses WHERE id = ?;", (course_id,))
            return cursor.rowcount > 0


# ============================================================================
# SessionRepository
# ============================================================================

class SessionRepository(BaseRepository):
    """Accès aux données pour les sessions d'étude et de pause."""

    def create(self, session: StudySessionCreate) -> StudySession:
        """Planifie et persiste une nouvelle session."""
        now_iso = datetime.now().isoformat()
        query = """
            INSERT INTO study_sessions (
                title, session_type, start_time, end_time, status, course_id, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            session.title,
            session.session_type.value,
            session.start_time.isoformat(),
            session.end_time.isoformat(),
            session.status.value,
            session.course_id,
            session.notes,
            now_iso,
            now_iso,
        )
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            new_id = cursor.lastrowid
            assert new_id is not None
            cursor.execute("SELECT * FROM study_sessions WHERE id = ?;", (new_id,))
            row = cursor.fetchone()
            return StudySession.model_validate(dict(row))

    def get_by_id(self, session_id: int) -> StudySession | None:
        """Récupère une session par son ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM study_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            return StudySession.model_validate(dict(row)) if row else None

    def get_sessions_between(
        self,
        start_time: datetime,
        end_time: datetime,
        include_overlapping: bool = True,
    ) -> list[StudySession]:
        """Récupère toutes les sessions dans un intervalle de dates donné.

        Si include_overlapping est True, inclut toute session ayant au moins une minute
        en commun avec la plage [start_time, end_time].
        """
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        if include_overlapping:
            # Condition standard de chevauchement d'intervalles :
            # début_session < fin_recherche ET fin_session > début_recherche
            query = """
                SELECT * FROM study_sessions
                WHERE start_time < ? AND end_time > ?
                ORDER BY start_time ASC;
            """
            params = (end_iso, start_iso)
        else:
            query = """
                SELECT * FROM study_sessions
                WHERE start_time >= ? AND end_time <= ?
                ORDER BY start_time ASC;
            """
            params = (start_iso, end_iso)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [StudySession.model_validate(dict(row)) for row in cursor.fetchall()]

    def get_active_session(self, at_time: datetime | None = None) -> StudySession | None:
        """Retourne la session active en ce moment précis (priorité aux sessions en cours).

        Utilisé principalement par la Sentinelle Système (Module 3) pour déterminer
        si le blocage des distractions doit être actif maintenant.
        """
        target_iso = (at_time or datetime.now()).isoformat()
        query = """
            SELECT * FROM study_sessions
            WHERE status IN ('in_progress', 'scheduled')
              AND start_time <= ?
              AND end_time >= ?
            ORDER BY
              CASE status
                WHEN 'in_progress' THEN 1
                WHEN 'scheduled' THEN 2
                ELSE 3
              END ASC,
              start_time ASC
            LIMIT 1;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (target_iso, target_iso))
            row = cursor.fetchone()
            return StudySession.model_validate(dict(row)) if row else None

    def get_upcoming_sessions(
        self,
        limit: int = 5,
        after_time: datetime | None = None,
    ) -> list[StudySession]:
        """Retourne les prochaines sessions à venir planifiées."""
        target_iso = (after_time or datetime.now()).isoformat()
        query = """
            SELECT * FROM study_sessions
            WHERE start_time > ? AND status = 'scheduled'
            ORDER BY start_time ASC
            LIMIT ?;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (target_iso, limit))
            return [StudySession.model_validate(dict(row)) for row in cursor.fetchall()]

    def update_status(self, session_id: int, status: SessionStatus) -> StudySession | None:
        """Met à jour rapidement le statut d'une session (ex: activation, fin, annulation)."""
        now_iso = datetime.now().isoformat()
        query = """
            UPDATE study_sessions
            SET status = ?, updated_at = ?
            WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (status.value, now_iso, session_id))
            if cursor.rowcount == 0:
                return None
            cursor.execute("SELECT * FROM study_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            return StudySession.model_validate(dict(row)) if row else None

    def update(self, session_id: int, update_data: StudySessionUpdate) -> StudySession | None:
        """Mise à jour partielle des attributs d'une session."""
        fields: list[str] = []
        values: list[Any] = []

        data_dict = update_data.model_dump(exclude_unset=True)
        if not data_dict:
            return self.get_by_id(session_id)

        for field_name, val in data_dict.items():
            if val is not None:
                if isinstance(val, (SessionType, SessionStatus)):
                    values.append(val.value)
                elif isinstance(val, datetime):
                    values.append(val.isoformat())
                else:
                    values.append(val)
                fields.append(f"{field_name} = ?")

        values.append(datetime.now().isoformat())
        fields.append("updated_at = ?")

        values.append(session_id)
        query = f"UPDATE study_sessions SET {', '.join(fields)} WHERE id = ?;"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(values))
            if cursor.rowcount == 0:
                return None
            cursor.execute("SELECT * FROM study_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            return StudySession.model_validate(dict(row)) if row else None

    def delete(self, session_id: int) -> bool:
        """Supprime une session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM study_sessions WHERE id = ?;", (session_id,))
            return cursor.rowcount > 0

    def delete_by_range(self, start_time: datetime, end_time: datetime) -> int:
        """Supprime les sessions programmées dans une plage de dates (ex: regénération d'emploi du temps)."""
        query = """
            DELETE FROM study_sessions
            WHERE start_time >= ? AND end_time <= ? AND status = 'scheduled';
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (start_time.isoformat(), end_time.isoformat()))
            return cursor.rowcount


# ============================================================================
# RuleRepository
# ============================================================================

class RuleRepository(BaseRepository):
    """Accès aux données pour les règles de blocage d'applications distrayantes."""

    DEFAULT_RULES: list[dict[str, Any]] = [
        {"process_name": "discord.exe", "display_name": "Discord", "category": RuleCategory.SOCIAL_MEDIA, "severity": RuleSeverity.KILL},
        {"process_name": "steam.exe", "display_name": "Steam", "category": RuleCategory.GAMING, "severity": RuleSeverity.KILL},
        {"process_name": "epicgameslauncher.exe", "display_name": "Epic Games Launcher", "category": RuleCategory.GAMING, "severity": RuleSeverity.KILL},
        {"process_name": "riotclientservices.exe", "display_name": "Riot Client", "category": RuleCategory.GAMING, "severity": RuleSeverity.KILL},
        {"process_name": "leagueclient.exe", "display_name": "League of Legends", "category": RuleCategory.GAMING, "severity": RuleSeverity.KILL},
        {"process_name": "valorant.exe", "display_name": "Valorant", "category": RuleCategory.GAMING, "severity": RuleSeverity.KILL},
        {"process_name": "spotify.exe", "display_name": "Spotify", "category": RuleCategory.STREAMING, "severity": RuleSeverity.WARN},
        {"process_name": "telegram.exe", "display_name": "Telegram", "category": RuleCategory.SOCIAL_MEDIA, "severity": RuleSeverity.WARN},
        {"process_name": "whatsapp.exe", "display_name": "WhatsApp", "category": RuleCategory.SOCIAL_MEDIA, "severity": RuleSeverity.WARN},
        {"process_name": "tiktok.exe", "display_name": "TikTok", "category": RuleCategory.SOCIAL_MEDIA, "severity": RuleSeverity.KILL},
    ]

    def create(self, rule: DistractionRuleCreate) -> DistractionRule:
        """Ajoute une nouvelle règle de blocage."""
        created_at = datetime.now().isoformat()
        query = """
            INSERT INTO distraction_rules (
                process_name, display_name, category, severity, window_title_keyword, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            rule.process_name,
            rule.display_name,
            rule.category.value,
            rule.severity.value,
            rule.window_title_keyword,
            1 if rule.is_active else 0,
            created_at,
        )
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            new_id = cursor.lastrowid
            assert new_id is not None
            cursor.execute("SELECT * FROM distraction_rules WHERE id = ?;", (new_id,))
            row = cursor.fetchone()
            return DistractionRule.model_validate(dict(row))

    def get_by_id(self, rule_id: int) -> DistractionRule | None:
        """Récupère une règle par son ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM distraction_rules WHERE id = ?;", (rule_id,))
            row = cursor.fetchone()
            return DistractionRule.model_validate(dict(row)) if row else None

    def get_by_process_name(self, process_name: str) -> DistractionRule | None:
        """Trouve une règle par le nom d'exécutable (insensible à la casse, normalisé .exe)."""
        clean_name = process_name.strip().lower()
        if not clean_name.endswith(".exe"):
            clean_name = f"{clean_name}.exe"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM distraction_rules WHERE process_name = ?;", (clean_name,))
            row = cursor.fetchone()
            return DistractionRule.model_validate(dict(row)) if row else None

    def list_all(self, active_only: bool = False) -> list[DistractionRule]:
        """Liste l'ensemble des règles enregistrées."""
        query = """
            SELECT * FROM distraction_rules
            WHERE (? = 0 OR is_active = 1)
            ORDER BY display_name ASC;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (1 if active_only else 0,))
            return [DistractionRule.model_validate(dict(row)) for row in cursor.fetchall()]

    def get_active_process_names(self) -> set[str]:
        """Retourne un ensemble (Set) des noms de processus actifs à bloquer.

        Idéal pour une vérification en O(1) ultra-rapide dans la boucle de la Sentinelle (psutil).
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT process_name FROM distraction_rules WHERE is_active = 1;")
            return {row["process_name"] for row in cursor.fetchall()}

    def toggle_active(self, rule_id: int, is_active: bool) -> bool:
        """Active ou désactive une règle."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE distraction_rules SET is_active = ? WHERE id = ?;",
                (1 if is_active else 0, rule_id),
            )
            return cursor.rowcount > 0

    def delete(self, rule_id: int) -> bool:
        """Supprime une règle."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM distraction_rules WHERE id = ?;", (rule_id,))
            return cursor.rowcount > 0

    def seed_default_rules(self) -> int:
        """Insère les applications distrayantes courantes si elles n'existent pas déjà.

        Retourne le nombre de nouvelles règles insérées.
        """
        inserted_count = 0
        now_iso = datetime.now().isoformat()
        query = """
            INSERT OR IGNORE INTO distraction_rules (
                process_name, display_name, category, severity, window_title_keyword, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for rule_dict in self.DEFAULT_RULES:
                cursor.execute(
                    query,
                    (
                        rule_dict["process_name"],
                        rule_dict["display_name"],
                        rule_dict["category"].value,
                        rule_dict["severity"].value,
                        None,
                        1,
                        now_iso,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted_count += 1
        return inserted_count


# ============================================================================
# ViolationRepository
# ============================================================================

class ViolationRepository(BaseRepository):
    """Accès aux données pour l'historique des infractions enregistrées par la Sentinelle."""

    def record_violation(self, violation: ViolationEventCreate) -> ViolationEvent:
        """Enregistre un événement de blocage d'application."""
        query = """
            INSERT INTO violation_events (
                session_id, rule_id, process_name, process_pid, window_title, action_taken, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            violation.session_id,
            violation.rule_id,
            violation.process_name,
            violation.process_pid,
            violation.window_title,
            violation.action_taken,
            violation.timestamp.isoformat(),
        )
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            new_id = cursor.lastrowid
            assert new_id is not None
            cursor.execute("SELECT * FROM violation_events WHERE id = ?;", (new_id,))
            row = cursor.fetchone()
            return ViolationEvent.model_validate(dict(row))

    def get_by_id(self, violation_id: int) -> ViolationEvent | None:
        """Récupère une violation par son ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM violation_events WHERE id = ?;", (violation_id,))
            row = cursor.fetchone()
            return ViolationEvent.model_validate(dict(row)) if row else None

    def list_recent(self, limit: int = 50) -> list[ViolationEvent]:
        """Retourne les infractions les plus récentes par ordre antichronologique."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM violation_events ORDER BY timestamp DESC LIMIT ?;", (limit,))
            return [ViolationEvent.model_validate(dict(row)) for row in cursor.fetchall()]

    def get_by_session(self, session_id: int) -> list[ViolationEvent]:
        """Retourne toutes les infractions commises durant une session donnée."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM violation_events WHERE session_id = ? ORDER BY timestamp ASC;",
                (session_id,),
            )
            return [ViolationEvent.model_validate(dict(row)) for row in cursor.fetchall()]

    def get_summary_stats(self, since: datetime | None = None) -> dict[str, Any]:
        """Calcule des statistiques globales sur les infractions.

        Utile pour le Dashboard UI (Module 5) : nombre total, applications les plus fréquentes, etc.
        """
        since_iso = since.isoformat() if since else "1970-01-01T00:00:00"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Nombre total
            cursor.execute("SELECT COUNT(*) AS total FROM violation_events WHERE timestamp >= ?;", (since_iso,))
            total = cursor.fetchone()["total"]

            # Top 5 applications les plus bloquées
            cursor.execute(
                """
                SELECT process_name, COUNT(*) AS count
                FROM violation_events
                WHERE timestamp >= ?
                GROUP BY process_name
                ORDER BY count DESC
                LIMIT 5;
                """,
                (since_iso,),
            )
            top_processes = [dict(row) for row in cursor.fetchall()]

            # Répartition par action
            cursor.execute(
                """
                SELECT action_taken, COUNT(*) AS count
                FROM violation_events
                WHERE timestamp >= ?
                GROUP BY action_taken;
                """,
                (since_iso,),
            )
            actions = {row["action_taken"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_violations": total,
                "top_processes": top_processes,
                "actions": actions,
            }


# ============================================================================
# SettingsRepository
# ============================================================================

class SettingsRepository(BaseRepository):
    """Accès aux réglages et préférences utilisateur locales stockées en base."""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Récupère la valeur d'une clé de configuration."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_settings WHERE key = ?;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set(self, key: str, value: str, description: str | None = None) -> None:
        """Enregistre ou met à jour une clé de configuration (UPSERT)."""
        now_iso = datetime.now().isoformat()
        query = """
            INSERT INTO user_settings (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                description = coalesce(excluded.description, user_settings.description),
                updated_at = excluded.updated_at;
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (key, value, description, now_iso))

    def get_all(self) -> dict[str, str]:
        """Retourne toutes les paires clé/valeur."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_settings;")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def delete(self, key: str) -> bool:
        """Supprime une clé."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_settings WHERE key = ?;", (key,))
            return cursor.rowcount > 0


# ============================================================================
# StorageManager (Facade unifiée)
# ============================================================================

class StorageManager:
    """Façade unifiée pour tous les accès aux données de l'application Æther.

    Permet aux autres modules d'interagir simplement avec la persistance :
    storage = StorageManager()
    active_session = storage.sessions.get_active_session()
    blocked_procs = storage.rules.get_active_process_names()
    """

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self.courses = CourseRepository(self.db)
        self.sessions = SessionRepository(self.db)
        self.rules = RuleRepository(self.db)
        self.violations = ViolationRepository(self.db)
        self.settings = SettingsRepository(self.db)

    def init_defaults(self) -> None:
        """Initialise les règles par défaut et les paramètres de démarrage recommandés."""
        self.rules.seed_default_rules()

        # Paramètres d'étude par défaut (Pomodoro et discipline)
        default_settings = [
            ("pomodoro_work_minutes", "45", "Durée d'un bloc de travail focalisé"),
            ("pomodoro_break_minutes", "10", "Durée d'une pause courte"),
            ("auto_block_enabled", "true", "Activer la fermeture automatique des distractions"),
            ("daily_study_goal_hours", "4", "Objectif quotidien de révision"),
            ("notify_before_session_minutes", "5", "Délai d'alerte avant le début d'une session"),
        ]
        for key, val, desc in default_settings:
            if self.settings.get(key) is None:
                self.settings.set(key, val, desc)

    def reset_all(self) -> None:
        """Réinitialise intégralement la base de données."""
        self.db.reset_database()
