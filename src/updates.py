"""Where releases are published and installed, shared by the launcher and the app
(decisions 2026-10-15). Standard library only: the launcher is built from it too.

    SharePoint (synced):  CAD BLOCKS\\CONFIGURATORS\\Switchboard Configurator\\
                              latest.txt                    e.g. "2.0.1"
                              Releases\\2.0.1\\Switchboard Configurator 2.0.1.zip
                              Install Switchboard Configurator.zip   (installer; zipped,
                                  because SharePoint will not sync a loose .exe)
    This PC:              %LOCALAPPDATA%\\Hyper Configurators\\Switchboard Configurator\\
                              Switchboard Configurator.exe  (the launcher)
                              versions\\2.0.1\\...           (the app)
"""
import os
from pathlib import Path

APP_NAME = "Switchboard Configurator"

# The release folder can be pointed elsewhere for testing with HYPER_RELEASE_FOLDER.
RELEASE_FOLDER = Path(os.environ.get("HYPER_RELEASE_FOLDER") or Path.home() / (
    "Hyper Solutions/Hyper Document Library - Engineering/Electrical Team/CAD BLOCKS/"
    "CONFIGURATORS/Switchboard Configurator"))
INSTALL_FOLDER = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Hyper Configurators" / APP_NAME
INSTALLED_LAUNCHER = INSTALL_FOLDER / f"{APP_NAME}.exe"
VERSIONS_FOLDER = INSTALL_FOLDER / "versions"


def version_key(version: str) -> tuple:
    """'2.0.10' -> (2, 0, 10), so versions compare by number, not as text. Anything that
    isn't X.Y.Z (e.g. a development version) sorts lowest."""
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (-1,)


def latest_released_version() -> str | None:
    """The version in latest.txt, or None if it can't be read (offline, not synced)."""
    try:
        return (RELEASE_FOLDER / "latest.txt").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def newer_version_available(current: str) -> str | None:
    """The released version, if it is newer than `current`."""
    latest = latest_released_version()
    if latest is not None and version_key(latest) > version_key(current) >= (0,):
        return latest
    return None
