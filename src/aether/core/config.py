"""Application configuration management for Æther."""

from dataclasses import dataclass, field
from pathlib import Path
import os
import sys


@dataclass
class Config:
    """Central configuration container for Æther."""

    app_name: str = "Æther"
    app_slug: str = "aether"
    version: str = "0.1.0"
    debug: bool = False

    # Directories
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    app_data_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "AETHER_DATA_DIR",
                os.environ.get("APPDATA", str(Path.home() / ".aether")),
            )
        )
        / "Aether"
    )

    def __post_init__(self) -> None:
        """Ensure necessary directories exist with fallback for restricted/portable environments."""
        try:
            self.app_data_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # Fallback to local directory inside project or user home for portable/dev environments
            fallback_dir = self.base_dir.parent.parent / ".aether_data"
            self.app_data_dir = fallback_dir
            self.app_data_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Path to SQLite database file."""
        return self.app_data_dir / f"{self.app_slug}.db"

    @property
    def logs_dir(self) -> Path:
        """Path to application logs directory."""
        return self.app_data_dir / "logs"

    @property
    def log_file(self) -> Path:
        """Path to default log file."""
        return self.logs_dir / f"{self.app_slug}.log"


_config_instance: Config | None = None


def get_config() -> Config:
    """Singleton getter for application configuration."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
