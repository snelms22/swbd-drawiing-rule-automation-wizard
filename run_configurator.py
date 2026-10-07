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
from src.model.switchboard import Section, Switchboard
from src.ui.main_window import MainWindow

SETTINGS_FILE = Path(__file__).resolve().parent / "config" / "layout_settings.json"


def example_switchboard() -> Switchboard:
    """A made-up starting board so the preview isn't empty. Edit or remove rows freely."""
    return Switchboard(
        name="Example",
        sections=[
            Section("Main 1", 70, 140),
            Section("Feeders 1", 110, 220),
            Section("Feeders 2", 110, 220),
            Section("Feeders 3", 110, 220),
            Section("Main 2", 70, 140, link_with_next=True),
            Section("Feeders 4", 110, 180),
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
