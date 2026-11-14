"""Domain models and enumerations for the Æther application using Pydantic v2."""

from datetime import datetime, time
from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# Énumérations Métier (Domain Enums)
# ============================================================================

class DayOfWeek(int, Enum):
    """Jours de la semaine normalisés (0 = Lundi, 6 = Dimanche, selon convention Python)."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    @property
    def label_fr(self) -> str:
        """Nom du jour en français."""
        labels = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        return labels[self.value]


class SessionType(str, Enum):
    """Types de session gérés par le planificateur et l'utilisateur."""
    STUDY = "study"          # Session de travail / révision personnelle (discipline active)
    BREAK = "break"          # Pause courte (ex: Pomodoro 5-15 min, pas de blocage)
    LEISURE = "leisure"      # Créneau de détente garanti (jeux/loisirs autorisés)
    EXAM = "exam"            # Session d'examen ou contrôle continu


class SessionStatus(str, Enum):
    """Cycle de vie d'une session."""
    SCHEDULED = "scheduled"      # Planifiée, à venir
    IN_PROGRESS = "in_progress"  # En cours d'exécution
    COMPLETED = "completed"      # Terminée avec succès
    CANCELLED = "cancelled"      # Annulée manuellement par l'étudiant
    MISSED = "missed"            # Non honorée (le temps est passé sans activation)


class RuleCategory(str, Enum):
    """Catégories d'applications pour le regroupement et les statistiques."""
    GAMING = "gaming"            # Ex: Steam, League of Legends, Valorant
    SOCIAL_MEDIA = "social"      # Ex: Discord, WhatsApp, Telegram
    STREAMING = "streaming"      # Ex: Netflix, Twitch, YouTube
    BROWSING = "browsing"        # Navigateurs ouverts sur distractions
    OTHER = "other"


class RuleSeverity(str, Enum):
    """Niveau de sévérité de la règle lorsque l'application interdite est détectée."""
    KILL = "kill"          # Fermeture brutale et immédiate du processus (SIGKILL / Terminate)
    WARN = "warn"          # Notification Windows toast d'avertissement sans fermeture
    LOG_ONLY = "log_only"  # Uniquement consigné dans l'historique (mode observation)


# ============================================================================
# Modèles : Cours Universitaires (Course)
# ============================================================================

class CourseBase(BaseModel):
    """Schéma de base pour un cours ou un créneau fixe de l'emploi du temps universitaire."""
    name: str = Field(..., min_length=2, max_length=100, description="Nom de la matière ou du cours")
    code: str | None = Field(default=None, max_length=20, description="Code matière (ex: INFO301)")
    day_of_week: DayOfWeek = Field(..., description="Jour hebdomadaire (0 = Lundi ... 6 = Dimanche)")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Heure de début au format HH:MM")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Heure de fin au format HH:MM")
    location: str | None = Field(default=None, max_length=100, description="Salle, amphi ou distanciel")
    color: str = Field(default="#4F46E5", pattern=r"^#[0-9a-fA-F]{6}$", description="Code couleur hexadécimal UI")
    is_active: bool = Field(default=True, description="Si le cours fait partie du semestre en cours")

    @model_validator(mode="after")
    def validate_time_range(self) -> "CourseBase":
        """Vérifie que l'heure de fin est strictement postérieure à l'heure de début."""
        sh, sm = map(int, self.start_time.split(":"))
        eh, em = map(int, self.end_time.split(":"))
        if (sh > 23 or sm > 59) or (eh > 23 or em > 59):
            raise ValueError("Les heures doivent être valides (00:00 à 23:59).")
        if (eh, em) <= (sh, sm):
            raise ValueError(f"L'heure de fin ({self.end_time}) doit être après l'heure de début ({self.start_time}).")
        return self


class CourseCreate(CourseBase):
    """Modèle pour la création d'un cours (sans ID)."""
    pass


class Course(CourseBase):
    """Modèle complet d'un cours avec identifiant en base."""
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Modèles : Sessions de Travail & Discipline (StudySession)
# ============================================================================

class StudySessionBase(BaseModel):
    """Schéma de base pour une session planifiée."""
    title: str = Field(..., min_length=2, max_length=150, description="Titre ou objectif de la session")
    session_type: SessionType = Field(default=SessionType.STUDY, description="Type de session")
    start_time: datetime = Field(..., description="Date et heure de début")
    end_time: datetime = Field(..., description="Date et heure de fin")
    status: SessionStatus = Field(default=SessionStatus.SCHEDULED, description="Statut de la session")
    course_id: int | None = Field(default=None, description="Référence optionnelle vers un cours lié")
    notes: str | None = Field(default=None, max_length=500, description="Notes ou bilan de l'étudiant")

    @model_validator(mode="after")
    def validate_session_dates(self) -> "StudySessionBase":
        """Vérifie que la date de fin est postérieure à la date de début."""
        if self.end_time <= self.start_time:
            raise ValueError(f"end_time ({self.end_time}) doit être postérieur à start_time ({self.start_time}).")
        return self

    @property
    def duration_minutes(self) -> int:
        """Durée totale de la session en minutes."""
        diff = self.end_time - self.start_time
        return int(diff.total_seconds() // 60)


class StudySessionCreate(StudySessionBase):
    """Modèle pour la création d'une session."""
    pass


class StudySessionUpdate(BaseModel):
    """Modèle pour la mise à jour partielle d'une session."""
    title: str | None = Field(default=None, min_length=2, max_length=150)
    session_type: SessionType | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: SessionStatus | None = None
    course_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)


class StudySession(StudySessionBase):
    """Modèle complet d'une session persistée."""
    id: int
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Modèles : Règles de Blocage & Discipline (DistractionRule)
# ============================================================================

class DistractionRuleBase(BaseModel):
    """Schéma de base d'une règle de liste noire."""
    process_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nom de l'exécutable Windows (ex: discord.exe, steam.exe)",
    )
    display_name: str = Field(..., min_length=2, max_length=100, description="Nom lisible pour l'UI (ex: Discord)")
    category: RuleCategory = Field(default=RuleCategory.OTHER, description="Catégorie de distraction")
    severity: RuleSeverity = Field(default=RuleSeverity.KILL, description="Action à exécuter lors de la détection")
    window_title_keyword: str | None = Field(
        default=None,
        max_length=100,
        description="Mot-clé optionnel présent dans le titre de la fenêtre pour ciblage fin",
    )
    is_active: bool = Field(default=True, description="Si la règle est active")

    @field_validator("process_name")
    @classmethod
    def normalize_process_name(cls, value: str) -> str:
        """Normalise le nom du processus : minuscules, espaces retirés, extension .exe garantie."""
        cleaned = value.strip().lower()
        if not cleaned.endswith(".exe"):
            cleaned = f"{cleaned}.exe"
        return cleaned


class DistractionRuleCreate(DistractionRuleBase):
    """Modèle pour la création d'une règle."""
    pass


class DistractionRule(DistractionRuleBase):
    """Modèle complet d'une règle persistée."""
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Modèles : Historique des Infractions (ViolationEvent)
# ============================================================================

class ViolationEventBase(BaseModel):
    """Schéma de base d'un événement de blocage d'application."""
    session_id: int | None = Field(default=None, description="ID de la session en cours lors de l'infraction")
    rule_id: int | None = Field(default=None, description="ID de la règle déclenchée")
    process_name: str = Field(..., max_length=100, description="Nom de l'exécutable capturé")
    process_pid: int | None = Field(default=None, description="PID Windows du processus ciblé")
    window_title: str | None = Field(default=None, max_length=255, description="Titre de la fenêtre active interceptée")
    action_taken: str = Field(default="KILLED", description="Action exécutée (KILLED, WARNED, LOGGED)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage précis de l'infraction")

    @field_validator("process_name")
    @classmethod
    def normalize_process_name(cls, value: str) -> str:
        return value.strip().lower()


class ViolationEventCreate(ViolationEventBase):
    """Modèle pour l'enregistrement d'une infraction."""
    pass


class ViolationEvent(ViolationEventBase):
    """Modèle complet d'une infraction avec identifiant."""
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Modèles : Paramètres Dynamiques Utilisateur (UserSetting)
# ============================================================================

class UserSetting(BaseModel):
    """Paire clé/valeur typée pour les paramètres dynamiques persistés."""
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(...)
    description: str | None = Field(default=None, max_length=255)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)
