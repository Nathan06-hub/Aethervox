"""Tests for SQLite database persistence, transactions, and repositories."""

from datetime import datetime, timedelta
from pathlib import Path
import pytest
import sqlite3

from aether.storage import (
    CourseCreate,
    CourseRepository,
    Database,
    DayOfWeek,
    DistractionRuleCreate,
    RuleCategory,
    RuleRepository,
    RuleSeverity,
    SessionRepository,
    SessionStatus,
    SessionType,
    SettingsRepository,
    StorageManager,
    StudySessionCreate,
    StudySessionUpdate,
    ViolationEventCreate,
    ViolationRepository,
)


@pytest.fixture
def memory_db() -> Database:
    """Fixture fournissant une base SQLite éphémère en mémoire pour chaque test."""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def storage(memory_db: Database) -> StorageManager:
    """Fixture fournissant le StorageManager complet branché sur la base en mémoire."""
    return StorageManager(memory_db)


# ============================================================================
# Tests : Database & Pragmas
# ============================================================================

def test_database_foreign_keys_and_schema(memory_db: Database) -> None:
    """Vérifie que les clés étrangères sont activées et que les tables existent."""
    with memory_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        assert fk_status == 1

        # Vérification de l'existence des tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert "courses" in tables
        assert "study_sessions" in tables
        assert "distraction_rules" in tables
        assert "violation_events" in tables
        assert "user_settings" in tables


def test_database_file_mode(tmp_path: Path) -> None:
    """Vérifie le fonctionnement sur un fichier physique avec WAL."""
    db_file = tmp_path / "test_aether.db"
    db = Database(db_file)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0].lower()
        assert mode == "wal"

    assert db_file.exists()


def test_transaction_rollback(memory_db: Database) -> None:
    """Vérifie le rollback automatique en cas d'erreur dans une transaction."""
    courses_repo = CourseRepository(memory_db)

    # Création initiale
    courses_repo.create(
        CourseCreate(
            name="Réseaux",
            day_of_week=DayOfWeek.MONDAY,
            start_time="08:00",
            end_time="10:00",
        )
    )
    assert len(courses_repo.list_all()) == 1

    # Tentative d'insertion avec exception simulée
    try:
        with memory_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO courses (name, day_of_week, start_time, end_time, created_at) "
                "VALUES ('Crash', 0, '10:00', '12:00', '2026-11-14T10:00:00');"
            )
            raise RuntimeError("Simulation d'un échec")
    except RuntimeError:
        pass

    # Le cours 'Crash' doit avoir été annulé par le rollback
    assert len(courses_repo.list_all()) == 1


# ============================================================================
# Tests : CourseRepository
# ============================================================================

def test_course_crud(storage: StorageManager) -> None:
    """Vérifie le cycle de vie CRUD complet d'un cours universitaire."""
    # Create
    new_course = storage.courses.create(
        CourseCreate(
            name="Architecture des Ordinateurs",
            code="ARCH302",
            day_of_week=DayOfWeek.MONDAY,
            start_time="14:00",
            end_time="16:00",
            location="Bâtiment C - Salle 204",
            color="#10B981",
        )
    )
    assert new_course.id is not None
    assert new_course.name == "Architecture des Ordinateurs"

    # Read by ID
    fetched = storage.courses.get_by_id(new_course.id)
    assert fetched is not None
    assert fetched.code == "ARCH302"
    assert fetched.day_of_week == DayOfWeek.MONDAY

    # Read by Day
    monday_courses = storage.courses.get_by_day(DayOfWeek.MONDAY)
    assert len(monday_courses) == 1
    tuesday_courses = storage.courses.get_by_day(DayOfWeek.TUESDAY)
    assert len(tuesday_courses) == 0

    # Update
    updated = storage.courses.update(
        new_course.id,
        CourseCreate(
            name="Architecture des Ordinateurs - TP",
            code="ARCH302",
            day_of_week=DayOfWeek.MONDAY,
            start_time="14:00",
            end_time="17:00",
            location="Labo 1",
            color="#059669",
        ),
    )
    assert updated is not None
    assert updated.name == "Architecture des Ordinateurs - TP"
    assert updated.end_time == "17:00"

    # Delete
    deleted = storage.courses.delete(new_course.id)
    assert deleted is True
    assert storage.courses.get_by_id(new_course.id) is None


# ============================================================================
# Tests : SessionRepository
# ============================================================================

def test_session_crud_and_status(storage: StorageManager) -> None:
    """Vérifie le CRUD et les transitions de statut d'une session."""
    now = datetime(2026, 11, 14, 10, 0)
    end = now + timedelta(hours=2)

    session = storage.sessions.create(
        StudySessionCreate(
            title="Révision Mathématiques Discrètes",
            session_type=SessionType.STUDY,
            start_time=now,
            end_time=end,
        )
    )
    assert session.id is not None
    assert session.status == SessionStatus.SCHEDULED

    # Passage en cours
    updated = storage.sessions.update_status(session.id, SessionStatus.IN_PROGRESS)
    assert updated is not None
    assert updated.status == SessionStatus.IN_PROGRESS

    # Mise à jour partielle
    edited = storage.sessions.update(
        session.id,
        StudySessionUpdate(title="Révision Mathématiques (Partie 1)", notes="Chapitres 1 à 3 faits"),
    )
    assert edited is not None
    assert edited.title == "Révision Mathématiques (Partie 1)"
    assert edited.notes == "Chapitres 1 à 3 faits"
    assert edited.status == SessionStatus.IN_PROGRESS


def test_session_queries(storage: StorageManager) -> None:
    """Vérifie les requêtes de session active, chevauchement et à venir."""
    t0 = datetime(2026, 11, 14, 10, 0)

    # Session 1: 10h00 - 12h00 (STUDY)
    s1 = storage.sessions.create(
        StudySessionCreate(
            title="Session Matin",
            start_time=t0,
            end_time=t0 + timedelta(hours=2),
            status=SessionStatus.IN_PROGRESS,
        )
    )

    # Session 2: 14h00 - 16h00 (STUDY)
    s2 = storage.sessions.create(
        StudySessionCreate(
            title="Session Après-midi",
            start_time=t0 + timedelta(hours=4),
            end_time=t0 + timedelta(hours=6),
            status=SessionStatus.SCHEDULED,
        )
    )

    # Session active à 11h00
    active = storage.sessions.get_active_session(t0 + timedelta(hours=1))
    assert active is not None
    assert active.id == s1.id

    # Aucune session active à 13h00 (pause déjeuner)
    active_lunch = storage.sessions.get_active_session(t0 + timedelta(hours=3))
    assert active_lunch is None

    # Prochaine session à partir de 12h30
    upcoming = storage.sessions.get_upcoming_sessions(limit=5, after_time=t0 + timedelta(hours=2, minutes=30))
    assert len(upcoming) == 1
    assert upcoming[0].id == s2.id

    # Sessions chevauchant la plage [11h30, 14h30]
    overlapping = storage.sessions.get_sessions_between(
        t0 + timedelta(hours=1, minutes=30),
        t0 + timedelta(hours=4, minutes=30),
        include_overlapping=True,
    )
    assert len(overlapping) == 2


def test_delete_by_range(storage: StorageManager) -> None:
    """Vérifie la suppression par plage pour la régénération d'emploi du temps."""
    t0 = datetime(2026, 11, 14, 8, 0)
    for i in range(3):
        storage.sessions.create(
            StudySessionCreate(
                title=f"Session {i}",
                start_time=t0 + timedelta(hours=i * 2),
                end_time=t0 + timedelta(hours=i * 2 + 1),
                status=SessionStatus.SCHEDULED,
            )
        )
    deleted_count = storage.sessions.delete_by_range(t0, t0 + timedelta(hours=10))
    assert deleted_count == 3


# ============================================================================
# Tests : RuleRepository
# ============================================================================

def test_rule_crud_and_lookup(storage: StorageManager) -> None:
    """Vérifie le CRUD et la recherche rapide par nom d'exécutable."""
    rule = storage.rules.create(
        DistractionRuleCreate(
            process_name="LeagueClient.exe",
            display_name="League of Legends",
            category=RuleCategory.GAMING,
            severity=RuleSeverity.KILL,
        )
    )
    assert rule.id is not None
    assert rule.process_name == "leagueclient.exe"

    # Recherche insensible à la casse et sans extension
    found = storage.rules.get_by_process_name("LEAGUECLIENT")
    assert found is not None
    assert found.id == rule.id

    # Ensemble de processus actifs pour la sentinelle
    procs = storage.rules.get_active_process_names()
    assert "leagueclient.exe" in procs

    # Désactivation
    storage.rules.toggle_active(rule.id, is_active=False)
    assert "leagueclient.exe" not in storage.rules.get_active_process_names()


def test_seed_default_rules(storage: StorageManager) -> None:
    """Vérifie le chargement des règles par défaut et son idempotence."""
    inserted = storage.rules.seed_default_rules()
    assert inserted > 0
    all_rules = storage.rules.list_all()
    assert len(all_rules) >= 10

    # Idempotence : un second appel ne crée aucun doublon
    re_inserted = storage.rules.seed_default_rules()
    assert re_inserted == 0


# ============================================================================
# Tests : ViolationRepository & Stats
# ============================================================================

def test_violation_recording_and_stats(storage: StorageManager) -> None:
    """Vérifie l'enregistrement des blocages et le calcul des statistiques."""
    # Enregistrer des infractions
    storage.violations.record_violation(
        ViolationEventCreate(
            process_name="discord.exe",
            process_pid=4560,
            window_title="General #chat",
            action_taken="KILLED",
        )
    )
    storage.violations.record_violation(
        ViolationEventCreate(
            process_name="discord.exe",
            process_pid=4561,
            window_title="General #chat",
            action_taken="KILLED",
        )
    )
    storage.violations.record_violation(
        ViolationEventCreate(
            process_name="steam.exe",
            process_pid=9820,
            action_taken="KILLED",
        )
    )

    recent = storage.violations.list_recent(limit=10)
    assert len(recent) == 3

    stats = storage.violations.get_summary_stats()
    assert stats["total_violations"] == 3
    assert stats["top_processes"][0]["process_name"] == "discord.exe"
    assert stats["top_processes"][0]["count"] == 2
    assert stats["actions"]["KILLED"] == 3


# ============================================================================
# Tests : SettingsRepository
# ============================================================================

def test_settings_upsert(storage: StorageManager) -> None:
    """Vérifie le stockage clé/valeur des préférences."""
    assert storage.settings.get("pomodoro_duration", "25") == "25"

    storage.settings.set("pomodoro_duration", "50", "Durée sessions longues")
    assert storage.settings.get("pomodoro_duration") == "50"

    # Mise à jour
    storage.settings.set("pomodoro_duration", "45")
    assert storage.settings.get("pomodoro_duration") == "45"

    all_settings = storage.settings.get_all()
    assert "pomodoro_duration" in all_settings

    storage.settings.delete("pomodoro_duration")
    assert storage.settings.get("pomodoro_duration") is None


# ============================================================================
# Tests : StorageManager Facade
# ============================================================================

def test_storage_manager_init_defaults(storage: StorageManager) -> None:
    """Vérifie que init_defaults initialise les règles et les réglages de base."""
    storage.init_defaults()
    assert len(storage.rules.list_all()) >= 10
    assert storage.settings.get("pomodoro_work_minutes") == "45"
    assert storage.settings.get("auto_block_enabled") == "true"
