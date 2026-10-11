"""Starts the Hyper Switchboard Configurator.

Run from the project folder (with the virtual environment activated):
    python run_configurator.py

Layout numbers are read from config/layout_settings.json when the app starts.
After editing that file, close and reopen the app to see the change.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from src.layout.settings import SettingsError, load_settings
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, Space,
    TieBreaker, TwinLevel,
)
from src.model.switchboard import Section, Switchboard
from src.ui.main_window import MainWindow

SETTINGS_FILE = Path(__file__).resolve().parent / "config" / "layout_settings.json"


def example_switchboard() -> Switchboard:
    """A made-up starting board so the preview isn't empty. Edit it freely in the app."""
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
                    TwinLevel(Space("PROVISION FOR 3VA41"), bkr("52-F4")),
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
            # Section 4: main fed from the bottom.
            Section(SectionContents(below=MainBreaker(bkr("52-MCB-02")))),
        ],
    )


def main() -> int:
    app = QApplication(sys.argv)
    try:
        settings = load_settings(SETTINGS_FILE)
    except SettingsError as error:
        QMessageBox.critical(None, "Problem with layout settings", str(error))
        return 1
    window = MainWindow(settings, example_switchboard())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
