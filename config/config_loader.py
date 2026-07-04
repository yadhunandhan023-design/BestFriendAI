"""
config/config_loader.py

Single source of truth for reading config.yaml.
Every module should get its settings through this,
instead of reading the YAML file directly.
"""

import os
import yaml


class ConfigError(Exception):
    """Raised when config.yaml is missing or malformed."""
    pass


def load_config() -> dict:
    """
    Loads and returns config/config.yaml as a dictionary.
    Raises ConfigError with a clear message if anything is wrong.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    if not os.path.exists(config_path):
        raise ConfigError(
            f"config.yaml not found at {config_path}. "
            "Did you create it in Step 1?"
        )

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"config.yaml has invalid YAML syntax: {e}")

    if not data:
        raise ConfigError("config.yaml is empty.")

    return data
