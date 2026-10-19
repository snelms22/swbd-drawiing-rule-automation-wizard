"""Each person's own choices, remembered on their PC (decision 2026-10-15): the folder
their drawings are saved in, and the last version they opened (for the "Updates since
your last session" pop-up, decision 2026-10-19).

Kept in a small JSON file in the person's AppData folder, not in config/ (config is the
same for everyone and comes with each release). A missing or unreadable file just means
nothing has been chosen yet.
"""
import json
import os
from pathlib import Path

PREFERENCES_FILE = (Path(os.environ.get("APPDATA", Path.home())) / "Hyper Configurators"
                    / "Switchboard Configurator" / "preferences.json")

DRAWING_FOLDER = "drawing_folder"
LAST_SEEN_VERSION = "last_seen_version"


def load_preferences(path: Path = PREFERENCES_FILE) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_preference(key: str, value, path: Path = PREFERENCES_FILE):
    path = Path(path)
    data = load_preferences(path)
    data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def drawing_folder(path: Path = PREFERENCES_FILE) -> Path | None:
    """The drawing folder this person picked, if it still exists."""
    value = load_preferences(path).get(DRAWING_FOLDER)
    if not value or not Path(value).is_dir():
        return None
    return Path(value)
