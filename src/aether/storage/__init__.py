"""Storage package for Æther: SQLite persistence, Pydantic models, and repositories."""

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
from aether.storage.repositories import (
    CourseRepository,
    RuleRepository,
    SessionRepository,
    SettingsRepository,
    StorageManager,
    ViolationRepository,
)

__all__ = [
    # Database
    "Database",
    # Enums
    "DayOfWeek",
    "SessionType",
    "SessionStatus",
    "RuleCategory",
    "RuleSeverity",
    # Models
    "Course",
    "CourseCreate",
    "StudySession",
    "StudySessionCreate",
    "StudySessionUpdate",
    "DistractionRule",
    "DistractionRuleCreate",
    "ViolationEvent",
    "ViolationEventCreate",
    "UserSetting",
    # Repositories & Facade
    "CourseRepository",
    "SessionRepository",
    "RuleRepository",
    "ViolationRepository",
    "SettingsRepository",
    "StorageManager",
]
