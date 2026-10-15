"""Tests for the update check (src/updates.py, decisions 2026-10-15)."""
from src import updates
from src.updates import newer_version_available, version_key


def test_versions_compare_by_number_not_text():
    assert version_key("2.0.10") > version_key("2.0.9")
    assert version_key("3.0.0") > version_key("2.9.9")
    assert version_key("2.0.0-dev") < version_key("0.0.1")      # development sorts lowest


def test_newer_version_is_offered_only_when_newer(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "RELEASE_FOLDER", tmp_path)
    assert newer_version_available("2.0.0") is None            # no latest.txt (offline)
    (tmp_path / "latest.txt").write_text("2.0.1\n", encoding="utf-8")
    assert newer_version_available("2.0.0") == "2.0.1"
    assert newer_version_available("2.0.1") is None
    assert newer_version_available("2.1.0") is None             # you have a newer one
    assert newer_version_available("2.0.0-dev") is None        # development: never prompted
