"""Publish a new version of the Switchboard Configurator to the team (decisions 2026-10-15).

    python tools/release.py 2.0.1 --note "SPACE option for empty slots" --note "..."

Each --note is one short line for the release notes: they go in CHANGELOG.md under the
version, ship inside the app, and are shown to everyone in the "Updates since your last
session" pop-up the first time they open the new version (decision 2026-10-19).

Version numbers are X.Y.Z: Z = routine changes and small fixes, Y = something changed but
not huge, X = a milestone. Steps, stopping at the first problem:
  1. checks: the number is X.Y.Z and newer than the released one; no uncommitted changes;
  2. runs every test;
  3. sets the version in src/version.py and adds the notes to CHANGELOG.md;
  4. builds the app (PyInstaller) with config, catalog, template, switchboard library and
     icons, adds the AutoCAD add-in (Hyper ribbon tab), and zips it;
  5. builds the launcher / installer;
  6. copies everything to SharePoint: Releases/X.Y.Z/, "Install Switchboard
     Configurator.exe", and LAST latest.txt (so nobody sees a half-copied version);
  7. commits the version and notes, and tags the version in git.
Everyone gets the new version the next time they open the app (or is offered a restart).

Trying it out without touching SharePoint or git:
    python tools/release.py 2.0.0 --test-folder C:/somewhere/test-release
then run the installer from "Install Switchboard Configurator.zip" there, with the environment variable
HYPER_RELEASE_FOLDER set to the same folder.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from distribution.autocad_addin import write_bundle             # noqa: E402
from src.updates import APP_NAME, RELEASE_FOLDER, version_key   # noqa: E402

PYTHON = sys.executable
# Built outside OneDrive (like the virtual environment): OneDrive locks files while it
# syncs, which breaks the build.
BUILD = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Hyper Configurators" / "build" / "switchboard"
VERSION_FILE = PROJECT_ROOT / "src" / "version.py"
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"
INSTALLER_NAME = f"Install {APP_NAME}"
# Folders shipped inside the app (read at run time, relative to the program).
DATA_FOLDERS = ["config", "catalog", "templates", "switchboard_library", "assets"]
DATA_FILES = ["CHANGELOG.md"]          # the release notes, for the pop-up


class ReleaseError(Exception):
    pass


def run(command, **kwargs):
    print("  >", " ".join(str(part) for part in command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, **kwargs)
    if result.returncode != 0:
        raise ReleaseError(f"Step failed: {' '.join(str(part) for part in command)}")
    return result


def check(version: str, release_folder: Path, use_git: bool):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseError(f'"{version}" is not a version number like 2.0.1.')
    latest_file = release_folder / "latest.txt"
    if latest_file.exists():
        latest = latest_file.read_text(encoding="utf-8").strip()
        if version_key(version) <= version_key(latest):
            raise ReleaseError(f"{version} is not newer than the released version {latest}.")
    if (release_folder / "Releases" / version).exists():
        raise ReleaseError(f"Releases/{version} already exists.")
    if use_git:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True).stdout.strip()
        if status:
            raise ReleaseError("There are uncommitted changes. Commit them first (a release is "
                               "always built from committed code).")


def set_version(version: str):
    text = VERSION_FILE.read_text(encoding="utf-8")
    VERSION_FILE.write_text(re.sub(r'VERSION = "[^"]*"', f'VERSION = "{version}"', text),
                            encoding="utf-8")


def build_app(version: str) -> Path:
    """The app as a folder (program + its files), with the AutoCAD add-in. Returns it."""
    shutil.rmtree(BUILD, ignore_errors=True)
    data = []
    for folder in DATA_FOLDERS:
        data += ["--add-data", f"{PROJECT_ROOT / folder};{folder}"]
    for file in DATA_FILES:
        data += ["--add-data", f"{PROJECT_ROOT / file};."]
    run([PYTHON, "-m", "PyInstaller", str(PROJECT_ROOT / "run_configurator.py"),
         "--name", APP_NAME, "--windowed", "--noconfirm", "--clean",
         "--icon", str(PROJECT_ROOT / "assets" / "swbd.ico"),
         "--distpath", str(BUILD / "dist"), "--workpath", str(BUILD / "work"),
         "--specpath", str(BUILD), *data])
    app_folder = BUILD / "dist" / APP_NAME
    write_bundle(app_folder / "autocad_addin", version, PROJECT_ROOT / "assets")
    return app_folder


def build_launcher() -> Path:
    run([PYTHON, "-m", "PyInstaller", str(PROJECT_ROOT / "distribution" / "launcher.py"),
         "--name", INSTALLER_NAME, "--onefile", "--windowed", "--noconfirm",
         "--icon", str(PROJECT_ROOT / "assets" / "swbd.ico"),
         "--paths", str(PROJECT_ROOT),
         "--distpath", str(BUILD / "dist"), "--workpath", str(BUILD / "work_launcher"),
         "--specpath", str(BUILD)])
    return BUILD / "dist" / f"{INSTALLER_NAME}.exe"


def zip_folder(folder: Path, archive: Path):
    """Zip the folder's CONTENTS (the launcher unzips them into versions/X.Y.Z/)."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in folder.rglob("*"):
            zipped.write(path, path.relative_to(folder))


def publish(version: str, app_folder: Path, launcher: Path, release_folder: Path):
    archive = release_folder / "Releases" / version / f"{APP_NAME} {version}.zip"
    print(f"  > zipping to {archive}")
    zip_folder(app_folder, archive)
    publish_installer(launcher, release_folder)
    (release_folder / "latest.txt").write_text(version + "\n", encoding="utf-8")   # last


def publish_installer(launcher: Path, release_folder: Path):
    """The installer goes in SharePoint ZIPPED: SharePoint won't sync a loose .exe
    (2026-10-16). People open the zip and run the installer from it; it copies itself to
    their PC, so where it was run from doesn't matter. A loose .exe from an earlier
    release is removed."""
    archive = release_folder / f"{INSTALLER_NAME}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.write(launcher, launcher.name)
    (release_folder / f"{INSTALLER_NAME}.exe").unlink(missing_ok=True)


def add_to_changelog(version: str, notes: list[str]):
    """The notes as a list under the version, newest version first."""
    lines = "".join(f"- {note.strip()}\n" for note in notes)
    entry = f"## {version} ({date.today():%Y-%m-%d})\n{lines}\n"
    old = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else (
        "# Switchboard Configurator: release history\n\n")
    heading, _, rest = old.partition("\n\n")
    CHANGELOG.write_text(f"{heading}\n\n{entry}{rest}", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a new version to the team.")
    parser.add_argument("version", help="X.Y.Z, e.g. 2.0.1")
    parser.add_argument("--note", action="append", default=[],
                        help="one short line about a change (repeat for each change)")
    parser.add_argument("--test-folder", help="publish here instead of SharePoint; no git")
    args = parser.parse_args()
    release_folder = Path(args.test_folder) if args.test_folder else RELEASE_FOLDER
    use_git = not args.test_folder
    original_version_file = VERSION_FILE.read_text(encoding="utf-8")
    original_changelog = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else None

    def put_files_back():
        VERSION_FILE.write_text(original_version_file, encoding="utf-8")
        if original_changelog is not None:
            CHANGELOG.write_text(original_changelog, encoding="utf-8")
    try:
        print("1. Checking")
        check(args.version, release_folder, use_git)
        if use_git and not args.note:
            raise ReleaseError('Say what changed: --note "..." (one per change)')
        print("2. Running the tests")
        run([PYTHON, "-m", "pytest", "-q"])
        print(f"3. Setting version {args.version} and adding the release notes")
        set_version(args.version)
        add_to_changelog(args.version, args.note or ["(test release)"])
        print("4. Building the app")
        app_folder = build_app(args.version)
        print("5. Building the launcher / installer")
        launcher = build_launcher()
        print(f"6. Publishing to {release_folder}")
        release_folder.mkdir(parents=True, exist_ok=True)
        publish(args.version, app_folder, launcher, release_folder)
        if use_git:
            print("7. Recording the release in git")
            notes = "\n".join(f"- {note}" for note in args.note)
            run(["git", "add", str(VERSION_FILE), str(CHANGELOG)])
            run(["git", "commit", "-m", f"Release {args.version}\n\n{notes}"])
            run(["git", "tag", f"v{args.version}"])
    except ReleaseError as error:
        print(f"\nNOT RELEASED: {error}")
        put_files_back()
        return 1
    finally:
        if not use_git:          # a test release leaves the code exactly as it was
            put_files_back()
    print(f"\nReleased {APP_NAME} {args.version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
