"""Release notes for the "Updates since your last session" pop-up (decision 2026-10-19).

The notes live in CHANGELOG.md (written by the release command, shipped inside the app):

    ## 2.0.1 (2026-10-19)
    - Short description of one change
    - Another change

When someone opens a version newer than the one they last used, the app lists the notes of
every version in between, newest first, each with its version number, so someone who skipped
a few updates sees them all. Pure Python.
"""
import re

from src.updates import version_key

HEADING = re.compile(r"^##\s+(\d+\.\d+\.\d+)")


def parse_changelog(text: str) -> list[tuple[str, list[str]]]:
    """[(version, [notes])] in the order they appear in the file (newest first)."""
    releases = []
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            releases.append((heading.group(1), []))
        elif releases and line.strip():
            note = line.strip()
            releases[-1][1].append(note[1:].strip() if note.startswith("-") else note)
    return releases


def notes_since(text: str, last_seen: str | None, current: str) -> list[tuple[str, list[str]]]:
    """The releases to show: newer than `last_seen` and not newer than `current`, newest
    first. Someone opening the app for the very first time (`last_seen` None) sees only the
    current version's notes."""
    releases = parse_changelog(text)
    if last_seen is None:
        return [(version, notes) for version, notes in releases if version == current]
    return [(version, notes) for version, notes in releases
            if version_key(last_seen) < version_key(version) <= version_key(current)]
