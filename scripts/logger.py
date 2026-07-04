"""
scripts/logger.py

Centralized logging setup for BestFriendAI.
Every module imports get_logger() from here so all logs
go to the same format, same location, and can be controlled
from one place via config.yaml.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import yaml


def _load_log_config():
    """Read logging settings from config/config.yaml.
    Falls back to safe defaults if the file or keys are missing."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "config.yaml",
    )
    defaults = {"level": "INFO", "log_dir": "logs"}

    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        logging_cfg = data.get("logging", {})
        return {
            "level": logging_cfg.get("level", defaults["level"]),
            "log_dir": logging_cfg.get("log_dir", defaults["log_dir"]),
        }
    except Exception:
        return defaults


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module name.

    Usage:
        from scripts.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    cfg = _load_log_config()
    level = getattr(logging, cfg["level"].upper(), logging.INFO)

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, cfg["log_dir"])
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bestfriendai.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
