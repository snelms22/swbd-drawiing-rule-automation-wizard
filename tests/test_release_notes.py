"""Tests for the "Updates since your last session" notes (src/release_notes.py)."""
from src.release_notes import notes_since, parse_changelog

CHANGELOG = """# Switchboard Configurator: release history

## 2.1.0 (2026-10-25)
- General Drawing Information tab
- Comms checkbox on each breaker

## 2.0.1 (2026-10-19)
- What's new pop-up
- SPACE option for empty slots

## 2.0.0 (2026-10-15)
First release to the team.
"""


def test_changelog_is_read_newest_first_with_its_notes():
    assert parse_changelog(CHANGELOG) == [
        ("2.1.0", ["General Drawing Information tab", "Comms checkbox on each breaker"]),
        ("2.0.1", ["What's new pop-up", "SPACE option for empty slots"]),
        ("2.0.0", ["First release to the team."]),
    ]


def test_someone_who_skipped_updates_sees_every_version_since_their_last():
    shown = notes_since(CHANGELOG, last_seen="2.0.0", current="2.1.0")
    assert [version for version, _ in shown] == ["2.1.0", "2.0.1"]


def test_nothing_new_shows_nothing():
    assert notes_since(CHANGELOG, last_seen="2.1.0", current="2.1.0") == []


def test_first_ever_start_shows_only_the_current_version():
    assert notes_since(CHANGELOG, last_seen=None, current="2.0.1") == [
        ("2.0.1", ["What's new pop-up", "SPACE option for empty slots"])]
