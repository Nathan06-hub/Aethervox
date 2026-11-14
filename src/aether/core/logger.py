"""Centralized logging configuration for Æther."""

import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from aether.core.config import get_config


def setup_logger(name: str = "aether", log_level: int = logging.INFO) -> logging.Logger:
    """Configure and return a standard logger for Æther components."""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    config = get_config()
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # Rotating File Handler (max 5MB, up to 3 backups)
    try:
        file_handler = RotatingFileHandler(
            filename=config.log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning(f"Unable to initialize file logger at {config.log_file}: {exc}")

    return logger
