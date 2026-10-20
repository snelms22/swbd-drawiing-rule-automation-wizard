"""Copy the team's template (HYPER_A in SharePoint) into the configurator (decision 2026-10-20).

The configurator draws from its own copy, templates/HYPER_A.dwt, so every version uses a
fixed, tested template. The release command runs this first, so each release carries the
team's current template. Run it by hand during development to pick up template changes:

    python tools/update_template.py
"""
import filecmp
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.autocad.settings import load_autocad_settings  # noqa: E402


def update_template() -> str:
    """Copy the source template over the configurator's copy. Returns what happened."""
    settings = load_autocad_settings(PROJECT_ROOT / "config" / "autocad_settings.json", PROJECT_ROOT)
    source, copy = settings.template_source, settings.template_file
    if not source.exists():
        raise FileNotFoundError(f"The team's template was not found: {source}")
    if copy.exists() and filecmp.cmp(source, copy, shallow=False):
        return f"Template already up to date ({copy.name})."
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, copy)
    return f"Template updated from {source}."


if __name__ == "__main__":
    print(update_template())
