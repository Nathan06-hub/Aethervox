"""Tests for Æther configuration and core components."""

from pathlib import Path
from aether.core.config import Config, get_config
from aether.core.logger import setup_logger


def test_config_initialization(tmp_path: Path) -> None:
    """Verify that Config creates directories properly and computes paths."""
    test_app_data = tmp_path / "AppData"
    config = Config(app_data_dir=test_app_data)

    assert config.app_name == "Æther"
    assert config.app_slug == "aether"
    assert config.app_data_dir.exists()
    assert config.logs_dir.exists()
    assert config.db_path == test_app_data / "aether.db"
    assert config.log_file == test_app_data / "logs" / "aether.log"


def test_singleton_get_config() -> None:
    """Verify get_config returns a consistent singleton instance."""
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_setup_logger() -> None:
    """Verify setup_logger creates a functional logger."""
    logger = setup_logger("test.logger")
    assert logger.name == "test.logger"
    assert len(logger.handlers) >= 1
