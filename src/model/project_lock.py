"""One person edits a project at a time (decision 2026-10-15).

While someone has a project open, a small lock file sits next to it:
    "Job 1234.swbd.lock"  ->  {"user": "snelms", "computer": "HS-LAPTOP-12", "since": "..."}
Anyone else who opens the project is told who has it and gets a read-only copy (they can
still Save As somewhere else). The lock is removed when its owner closes the project.

A lock you made yourself (same user on the same computer) is yours: after a crash you can
simply open the project again. If a lock is left behind by someone else's crash, the app
lets you take over editing after warning you.

Note: projects live in SharePoint, so another person's lock reaches your PC only once
OneDrive has synced it (usually within seconds, longer when offline). Pure Python.
"""
import getpass
import json
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOCK_SUFFIX = ".lock"


@dataclass(frozen=True)
class LockInfo:
    user: str
    computer: str
    since: str          # when they opened it, e.g. "2026-10-15 14:02"

    def describe(self) -> str:
        return f"{self.user} on {self.computer} (since {self.since})"


def me() -> LockInfo:
    return LockInfo(getpass.getuser(), socket.gethostname(), datetime.now().strftime("%Y-%m-%d %H:%M"))


def lock_path(project: Path) -> Path:
    project = Path(project)
    return project.with_name(project.name + LOCK_SUFFIX)


def read_lock(project: Path) -> LockInfo | None:
    """Who has the project open, or None. An unreadable lock counts as someone unknown."""
    path = lock_path(project)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return LockInfo(str(data["user"]), str(data["computer"]), str(data["since"]))
    except (OSError, ValueError, KeyError, TypeError):
        return LockInfo("someone", "an unknown computer", "an unknown time")


def is_mine(info: LockInfo) -> bool:
    mine = me()
    return info.user == mine.user and info.computer == mine.computer


def held_by_someone_else(project: Path) -> LockInfo | None:
    info = read_lock(project)
    return info if info is not None and not is_mine(info) else None


def take_lock(project: Path):
    info = me()
    lock_path(project).write_text(
        json.dumps({"user": info.user, "computer": info.computer, "since": info.since}) + "\n",
        encoding="utf-8")


def release_lock(project: Path):
    """Remove the lock if it is ours (never someone else's)."""
    info = read_lock(project)
    if info is not None and is_mine(info):
        try:
            lock_path(project).unlink()
        except OSError:
            pass
