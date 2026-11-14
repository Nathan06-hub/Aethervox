"""Tests for domain models and data validation (Pydantic v2)."""

from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from aether.storage.models import (
    Course,
    CourseBase,
    CourseCreate,
    DayOfWeek,
    DistractionRule,
    DistractionRuleBase,
    DistractionRuleCreate,
    RuleCategory,
    RuleSeverity,
    SessionStatus,
    SessionType,
    StudySession,
    StudySessionBase,
    StudySessionCreate,
    StudySessionUpdate,
    UserSetting,
    ViolationEvent,
    ViolationEventCreate,
)


# ============================================================================
# Tests : Course & DayOfWeek
# ============================================================================

def test_day_of_week_labels() -> None:
    """Vérifie le mapping des jours et labels français."""
    assert DayOfWeek.MONDAY.value == 0
    assert DayOfWeek.SUNDAY.value == 6
    assert DayOfWeek.MONDAY.label_fr == "Lundi"
    assert DayOfWeek.FRIDAY.label_fr == "Vendredi"


def test_course_creation_valid() -> None:
    """Vérifie la création d'un modèle Course valide."""
    course = CourseCreate(
        name="Algorithmique & Graphes",
        code="INFO301",
        day_of_week=DayOfWeek.MONDAY,
        start_time="08:30",
        end_time="10:30",
        location="Amphi Turing",
        color="#3B82F6",
    )
    assert course.name == "Algorithmique & Graphes"
    assert course.day_of_week == DayOfWeek.MONDAY
    assert course.start_time == "08:30"
    assert course.end_time == "10:30"
    assert course.is_active is True


def test_course_invalid_time_range() -> None:
    """Vérifie que l'heure de fin doit être strictement après l'heure de début."""
    with pytest.raises(ValidationError) as exc:
        CourseCreate(
            name="Mathématiques",
            day_of_week=DayOfWeek.TUESDAY,
            start_time="14:00",
            end_time="12:00",  # Fin avant début
        )
    assert "L'heure de fin" in str(exc.value)


def test_course_invalid_time_format() -> None:
    """Vérifie la validation du format HH:MM."""
    with pytest.raises(ValidationError):
        CourseCreate(
            name="Physique",
            day_of_week=DayOfWeek.WEDNESDAY,
            start_time="8:30",  # Manque le zéro initial
            end_time="10:30",
        )


# ============================================================================
# Tests : StudySession
# ============================================================================

def test_study_session_valid() -> None:
    """Vérifie la création et le calcul de durée d'une session."""
    now = datetime(2026, 11, 14, 14, 0)
    end = now + timedelta(minutes=90)
    session = StudySessionCreate(
        title="Révision Examen Système",
        session_type=SessionType.STUDY,
        start_time=now,
        end_time=end,
    )
    assert session.title == "Révision Examen Système"
    assert session.duration_minutes == 90
    assert session.status == SessionStatus.SCHEDULED


def test_study_session_invalid_dates() -> None:
    """Vérifie le rejet d'une date de fin antérieure ou égale au début."""
    now = datetime(2026, 11, 14, 15, 0)
    with pytest.raises(ValidationError):
        StudySessionCreate(
            title="Invalide",
            start_time=now,
            end_time=now,  # Même heure
        )


# ============================================================================
# Tests : DistractionRule
# ============================================================================

def test_distraction_rule_normalization() -> None:
    """Vérifie la normalisation automatique du nom d'exécutable (.exe et minuscules)."""
    rule = DistractionRuleCreate(
        process_name="  DisCord  ",
        display_name="Discord",
        category=RuleCategory.SOCIAL_MEDIA,
        severity=RuleSeverity.KILL,
    )
    assert rule.process_name == "discord.exe"

    rule2 = DistractionRuleCreate(
        process_name="STEAM.EXE",
        display_name="Steam",
    )
    assert rule2.process_name == "steam.exe"


# ============================================================================
# Tests : ViolationEvent
# ============================================================================

def test_violation_event_normalization() -> None:
    """Vérifie la normalisation du nom de processus dans l'infraction."""
    event = ViolationEventCreate(
        process_name="  Spotify.EXE  ",
        process_pid=1234,
        window_title="Daily Mix 1",
    )
    assert event.process_name == "spotify.exe"
    assert event.action_taken == "KILLED"
    assert isinstance(event.timestamp, datetime)
