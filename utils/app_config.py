"""Pre-DB bootstrap configuration. Zero imports from the rest of the app.

Stores user preferences that must be known before opening the DB (e.g. db_folder).
Config lives in ~/.budget/config.json to avoid a bootstrapping problem.
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".budget"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Returns {} on missing or corrupt file — never raises."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: dict) -> None:
    """Creates ~/.budget/ if needed; atomic write via .tmp + os.replace()."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def get_db_folder() -> str | None:
    """Return config["db_folder"] or None if not set."""
    return load_config().get("db_folder")


def set_db_folder(path: str | None) -> None:
    """Update db_folder in config and save."""
    config = load_config()
    if path is None:
        config.pop("db_folder", None)
    else:
        config["db_folder"] = path
    save_config(config)
