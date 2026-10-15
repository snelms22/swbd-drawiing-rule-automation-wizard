"""Tests for one-editor-at-a-time locks (src/model/project_lock.py) and each person's
remembered choices (src/preferences.py). Decisions 2026-10-15."""
import json

from src.model import project_lock
from src.model.project_lock import (
    held_by_someone_else, lock_path, read_lock, release_lock, take_lock,
)
from src.preferences import DRAWING_FOLDER, drawing_folder, load_preferences, save_preference


def test_my_own_lock_does_not_block_me(tmp_path):
    project = tmp_path / "Job.swbd"
    take_lock(project)
    assert lock_path(project).name == "Job.swbd.lock"
    assert read_lock(project) is not None
    assert held_by_someone_else(project) is None       # e.g. reopening after a crash


def test_someone_elses_lock_is_reported_and_never_removed_by_me(tmp_path):
    project = tmp_path / "Job.swbd"
    lock_path(project).write_text(json.dumps(
        {"user": "jdoe", "computer": "HS-PC-7", "since": "2026-10-15 09:00"}), encoding="utf-8")
    holder = held_by_someone_else(project)
    assert holder.describe() == "jdoe on HS-PC-7 (since 2026-10-15 09:00)"
    release_lock(project)
    assert lock_path(project).exists()


def test_releasing_my_lock_removes_it(tmp_path):
    project = tmp_path / "Job.swbd"
    take_lock(project)
    release_lock(project)
    assert not lock_path(project).exists()
    release_lock(project)                               # nothing there: no error


def test_an_unreadable_lock_still_counts_as_someone_else(tmp_path):
    project = tmp_path / "Job.swbd"
    lock_path(project).write_text("garbage", encoding="utf-8")
    assert held_by_someone_else(project).user == "someone"


def test_same_user_on_another_computer_is_someone_else(tmp_path, monkeypatch):
    project = tmp_path / "Job.swbd"
    take_lock(project)
    monkeypatch.setattr(project_lock.socket, "gethostname", lambda: "OTHER-PC")
    assert held_by_someone_else(project) is not None


def test_drawing_folder_is_remembered_and_forgotten_if_it_disappears(tmp_path):
    prefs = tmp_path / "prefs" / "preferences.json"
    assert drawing_folder(prefs) is None                # nothing chosen yet
    folder = tmp_path / "Drawings"
    folder.mkdir()
    save_preference(DRAWING_FOLDER, str(folder), prefs)
    assert drawing_folder(prefs) == folder
    folder.rmdir()
    assert drawing_folder(prefs) is None


def test_unreadable_preferences_mean_nothing_chosen(tmp_path):
    prefs = tmp_path / "preferences.json"
    prefs.write_text("not json", encoding="utf-8")
    assert load_preferences(prefs) == {}
