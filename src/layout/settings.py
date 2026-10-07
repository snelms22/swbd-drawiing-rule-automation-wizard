"""Loads the editable layout numbers from config/layout_settings.json.

Every number that controls page layout lives in that file, not in code (see CLAUDE.md).
This module only reads and checks them, so a typo in the file gives a clear message
instead of a confusing crash somewhere inside the layout engine.
"""
import json
from dataclasses import dataclass
from pathlib import Path


class SettingsError(Exception):
    """The settings file is missing, unreadable, or has a bad value."""


@dataclass(frozen=True)
class LayoutSettings:
    drawable_width: float
    drawable_height: float
    margin_standard: float
    margin_relaxed: float
    divider_clearance: float
    keepout_width: float
    keepout_height: float


def load_settings(path) -> LayoutSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"Settings file not found: {path}")
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path} is not valid JSON: {error}")

    # Only the bottom-right corner is supported so far; fail loudly rather than
    # silently putting the keep-out somewhere other than the file says.
    corner = _read_value(data, "title_block_keepout", "corner")
    if corner != "bottom_right":
        raise SettingsError(
            f'title_block_keepout.corner is "{corner}", but only "bottom_right" is supported.'
        )

    return LayoutSettings(
        drawable_width=_read_number(data, "page", "drawable_width"),
        drawable_height=_read_number(data, "page", "drawable_height"),
        margin_standard=_read_number(data, "page", "margin_standard"),
        margin_relaxed=_read_number(data, "page", "margin_relaxed"),
        divider_clearance=_read_number(data, "section", "divider_clearance"),
        keepout_width=_read_number(data, "title_block_keepout", "width"),
        keepout_height=_read_number(data, "title_block_keepout", "height"),
    )


def _read_value(data, group, key):
    try:
        return data[group][key]
    except (KeyError, TypeError):
        raise SettingsError(f'Missing setting "{group}.{key}" in layout_settings.json.')


def _read_number(data, group, key) -> float:
    value = _read_value(data, group, key)
    # bool is a kind of int in Python, so rule it out explicitly (true/false is a typo here).
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingsError(f'Setting "{group}.{key}" must be a number, got {value!r}.')
    if value < 0:
        raise SettingsError(f'Setting "{group}.{key}" must not be negative, got {value}.')
    return float(value)
