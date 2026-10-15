"""Audit Blocks, for development only (not part of the app; decision 2026-10-15).

Re-reads every library block the configurator uses (connection markers, sizes, visibility
states, attributes and prompts), rewrites catalog/blocks.json, and lists problems with the
blocks. Needs AutoCAD 2026. Sammy owns the block library; run this when he asks.

Run from the project folder, with the environment activated:
    python tools/audit_blocks.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.autocad.catalog_refresh import audit_blocks          # noqa: E402
from src.autocad.connection import AutocadSession             # noqa: E402
from src.autocad.settings import load_autocad_settings        # noqa: E402
from src.layout.settings import load_settings                 # noqa: E402


def main() -> int:
    settings = load_settings(PROJECT_ROOT / "config" / "layout_settings.json")
    autocad_settings = load_autocad_settings(PROJECT_ROOT / "config" / "autocad_settings.json",
                                             PROJECT_ROOT)
    app = AutocadSession(autocad_settings.program_id).app
    changes, problems = audit_blocks(app, settings, autocad_settings,
                                     PROJECT_ROOT / "catalog" / "blocks.json")
    print("Catalog updated:")
    for line in changes or ["(no changes)"]:
        print(f"  - {line}")
    print("Problems found:" if problems else "No problems found.")
    for line in problems:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
