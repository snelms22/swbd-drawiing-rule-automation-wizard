"""Switchboard Configurator launcher and installer (decisions 2026-10-15).

Built into one small .exe by the release command. The same .exe does two jobs:

INSTALL - run once per PC from "Install Switchboard Configurator.zip" in SharePoint (the
          installer is zipped: SharePoint will not sync a loose .exe):
    copies itself to  %LOCALAPPDATA%\\Hyper Configurators\\Switchboard Configurator\\
    adds the desktop and Start menu shortcuts "Switchboard Configurator" (to that copy),
    then carries on as the launcher.

LAUNCH - run from the shortcut or the AutoCAD "Hyper" ribbon button:
    1. reads latest.txt in the SharePoint release folder (e.g. "2.0.1");
    2. if that version isn't on this PC yet, unzips it from Releases\\2.0.1\\ into
       ...\\Switchboard Configurator\\versions\\2.0.1\\ (keeping one older version);
    3. puts that version's AutoCAD add-in (the Hyper ribbon tab) into
       %APPDATA%\\Autodesk\\ApplicationPlugins\\;
    4. starts the app and exits.
Without SharePoint (offline, not synced) it starts the newest version already on the PC.

Only Python's standard library is used, so the .exe stays small. Nothing here needs
admin rights: everything goes in the person's own user folders.

Every run is written to launcher.log in the install folder (for helping someone whose
app won't start). For unattended tests, HYPER_LAUNCHER_QUIET=1 writes messages only to the
log instead of showing them.
"""
import ctypes
import datetime
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Shared with the app (src/updates.py): where releases are published and installed.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.updates import (  # noqa: E402
    APP_NAME, INSTALL_FOLDER, INSTALLED_LAUNCHER, RELEASE_FOLDER, VERSIONS_FOLDER,
    latest_released_version, version_key,
)

AUTOCAD_PLUGINS = Path(os.environ.get("APPDATA", Path.home())) / "Autodesk" / "ApplicationPlugins"
ADDIN_IN_RELEASE = Path("autocad_addin") / "HyperConfigurators.bundle"
KEEP_OLDER_VERSIONS = 1


def log(text: str):
    try:
        INSTALL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(INSTALL_FOLDER / "launcher.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n")
    except OSError:
        pass


def message(text: str, error: bool = False):
    """A plain Windows message box (no Qt in the launcher), also written to the log."""
    log(("ERROR: " if error else "") + text.replace("\n", " "))
    if os.environ.get("HYPER_LAUNCHER_QUIET"):
        return
    icon = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, icon)


# --- Install --------------------------------------------------------------------------

def running_from_install_folder() -> bool:
    return Path(sys.executable).resolve() == INSTALLED_LAUNCHER.resolve()


def install():
    INSTALL_FOLDER.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sys.executable, INSTALLED_LAUNCHER)
    desktop = Path.home() / "Desktop"
    start_menu = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft/Windows/Start Menu/Programs"
    for folder in (desktop, start_menu):
        make_shortcut(folder / f"{APP_NAME}.lnk", INSTALLED_LAUNCHER)


def make_shortcut(link: Path, target: Path):
    """A Windows shortcut, made through PowerShell (no extra Python packages needed)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    script = (f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{link}'); "
              f"$s.TargetPath = '{target}'; $s.WorkingDirectory = '{target.parent}'; "
              f"$s.IconLocation = '{target},0'; $s.Description = '{APP_NAME}'; $s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)


# --- Launch ---------------------------------------------------------------------------

def installed_versions() -> list[str]:
    if not VERSIONS_FOLDER.is_dir():
        return []
    ready = [p.name for p in VERSIONS_FOLDER.iterdir() if (p / f"{APP_NAME}.exe").exists()]
    return sorted(ready, key=version_key)


def fetch(version: str):
    """Unzip a released version onto this PC. Unzips into a temporary folder first, so a
    half-copied version is never started."""
    target = VERSIONS_FOLDER / version
    if (target / f"{APP_NAME}.exe").exists():
        return
    archive = RELEASE_FOLDER / "Releases" / version / f"{APP_NAME} {version}.zip"
    partial = VERSIONS_FOLDER / f"{version}.partial"
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    with zipfile.ZipFile(archive) as release:
        release.extractall(partial)
    shutil.rmtree(target, ignore_errors=True)
    partial.rename(target)


def remove_old_versions(current: str):
    older = [v for v in installed_versions() if version_key(v) < version_key(current)]
    for version in older[:-KEEP_OLDER_VERSIONS] if KEEP_OLDER_VERSIONS else older:
        shutil.rmtree(VERSIONS_FOLDER / version, ignore_errors=True)


def install_autocad_addin(version: str):
    """Put this version's Hyper ribbon tab where AutoCAD loads add-ins from. AutoCAD picks
    it up the next time it starts."""
    source = VERSIONS_FOLDER / version / ADDIN_IN_RELEASE
    if not source.is_dir():
        return
    target = AUTOCAD_PLUGINS / source.name
    try:
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)
    except OSError:
        pass          # AutoCAD may have the old one open; it is updated on a later start


def launch() -> int:
    latest = latest_released_version()
    problem = ""
    if latest is not None:
        try:
            fetch(latest)
        except (OSError, zipfile.BadZipFile) as error:
            problem = f"The newest version ({latest}) could not be copied to this PC:\n{error}"
    available = installed_versions()
    if not available:
        message(f"{APP_NAME} could not be found.\n\nIt is published in SharePoint at:\n"
                f"{RELEASE_FOLDER}\n\nMake sure the CAD BLOCKS library is synced to this PC "
                f"(OneDrive), then try again.", error=True)
        return 1
    version = latest if latest in available else available[-1]
    log(f"latest released: {latest}; on this PC: {available}; starting {version}")
    if problem:
        message(f"{problem}\n\nStarting version {version} instead.")
    install_autocad_addin(version)
    remove_old_versions(version)
    app = VERSIONS_FOLDER / version / f"{APP_NAME}.exe"
    subprocess.Popen([str(app)], cwd=str(app.parent))
    log(f"started {app}")
    return 0


def main() -> int:
    try:
        if not running_from_install_folder() and getattr(sys, "frozen", False):
            install()
            message(f"{APP_NAME} is installed.\n\nOpen it from the desktop icon, the Start menu, "
                    f"or the Hyper tab in AutoCAD 2026 (after restarting AutoCAD).")
        return launch()
    except Exception as error:      # never fail silently: say what went wrong
        message(f"Something went wrong:\n{type(error).__name__}: {error}", error=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
