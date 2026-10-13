"""Starts the Hyper Switchboard Configurator.

Run from the project folder (with the virtual environment activated):
    python run_configurator.py

Layout numbers are read from config/layout_settings.json when the app starts.
After editing that file, close and reopen the app to see the change.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from src.autocad.settings import load_autocad_settings
from src.layout.block_catalog import load_block_catalog
from src.layout.settings import SettingsError, load_settings
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, Provision,
    TieBreaker, TwinLevel,
)
from src.model.switchboard import Section, Switchboard
from src.ui.main_window import MainWindow

PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = PROJECT_ROOT / "config" / "layout_settings.json"
AUTOCAD_SETTINGS_FILE = PROJECT_ROOT / "config" / "autocad_settings.json"
BLOCK_CATALOG_FILE = PROJECT_ROOT / "catalog" / "blocks.json"


def new_switchboard() -> Switchboard:
    """What the app opens with: one empty section (decision 2026-10-12). Example and old
    projects come later."""
    return Switchboard(name="New switchboard", sections=[Section()])


def example_switchboard() -> Switchboard:
    """A made-up board used for testing during development (not opened by the app)."""
    def bkr(label):
        return Breaker(label)

    return Switchboard(
        name="Example",
        sections=[
            # Section 1: main fed from the top.
            Section(SectionContents(above=MainBreaker(bkr("52-MCB-01")))),
            # Section 2: group mounted above (twin, twin with a space, then single mount)
            # and twin mount below. Like ES_12 in Sammy's reference.
            Section(SectionContents(
                above=GroupMounted([
                    TwinLevel(bkr("52-F5"), bkr("52-F6")),
                    TwinLevel(Provision("3VA41"), bkr("52-F4")),
                    SingleLevel(bkr("52-F3")),
                    SingleLevel(bkr("52-F2")),
                    SingleLevel(bkr("52-F1")),
                ]),
                below=GroupMounted([
                    TwinLevel(bkr("52-F7"), bkr("52-F8")),
                    TwinLevel(bkr("52-F9"), bkr("52-F10")),
                ]),
            )),
            # Section 3: single breaker up, single breaker down, and a tie breaker (bus steps up).
            Section(SectionContents(
                above=SingleBreaker(bkr("52-F11")),
                below=SingleBreaker(bkr("52-F12")),
                tie=TieBreaker(bkr("52-TB01"), bus_steps="up"),
            )),
            # Section 4: draw-out main fed from the bottom.
            Section(SectionContents(below=MainBreaker(bkr("52-MCB-02"), mounting="draw-out"))),
        ],
    )


def main() -> int:
    app = QApplication(sys.argv)
    try:
        settings = load_settings(SETTINGS_FILE)
    except SettingsError as error:
        QMessageBox.critical(None, "Problem with layout settings", str(error))
        return 1
    # The app still opens without AutoCAD settings; only "Generate drawing" is disabled.
    autocad_settings, autocad_problem = None, ""
    try:
        autocad_settings = load_autocad_settings(AUTOCAD_SETTINGS_FILE, PROJECT_ROOT)
    except SettingsError as error:
        autocad_problem = str(error)
    try:
        catalog = load_block_catalog(BLOCK_CATALOG_FILE)
    except SettingsError as error:
        QMessageBox.warning(None, "Block catalog problem",
                            f"{error}\n\nMain breakers will be shown as placeholder boxes.")
        catalog = None
    window = MainWindow(settings, new_switchboard(), autocad_settings, autocad_problem,
                        catalog, BLOCK_CATALOG_FILE)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
