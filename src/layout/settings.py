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
class DividerSettings:
    layer: str
    bottom_y: float   # dividers run from here...
    top_y: float      # ...up to here, on every page


@dataclass(frozen=True)
class GroundBusSettings:
    layer: str
    y: float
    start_x: float                  # where the ground bus line starts on every page
    gap_before_title_block: float   # the line stops this far left of the title block
    label_text: str
    label_offset_x: float           # label's left edge, measured from the line's start
    label_gap_above_bus: float      # label's bottom, measured up from the line
    symbol_offset_x: float          # ground symbol stem, measured from the line's start
    symbol_stem_length: float
    symbol_bar_widths: tuple[float, ...]   # widest bar first
    symbol_bar_spacing: float


@dataclass(frozen=True)
class TextSettings:
    layer: str
    style: str
    height: float
    # Average character width as a fraction of text height (measured from "SECTION 1" in
    # Sammy's ES_01). Used to estimate how wide a label is without AutoCAD.
    char_width_factor: float

    def estimated_width(self, text: str) -> float:
        return len(text) * self.height * self.char_width_factor


@dataclass(frozen=True)
class SectionLabelSettings:
    text_format: str   # e.g. "SECTION {number}"
    bottom_y: float
    gap_above_title_block: float   # used when a label is moved up out of the title block


@dataclass(frozen=True)
class GroupMountedSettings:
    gap_to_first_level: float     # main bus to the nearest level
    level_pitch: float            # level to level
    level_height: float           # one level (a breaker's three poles)
    vertical_bus_overhang: float  # vertical bus continues this far past the last level
    single_mount_first_side: str  # "left" or "right": side of the first single level


@dataclass(frozen=True)
class PlaceholderSizes:
    """Stand-in sizes until the real blocks are catalogued. Widths include labels."""
    main_breaker_width: float
    main_breaker_height: float
    single_breaker_width: float
    single_breaker_height: float
    group_mounted_width: float
    tie_breaker_width: float


@dataclass(frozen=True)
class MainBusSettings:
    phase_spacing: float     # A-B and B-C; A to C is twice this
    step_width: float        # extra section width when the bus changes height there
    tie_step_height: float   # how far the bus moves up or down at a tie breaker
    content_top_y: float     # nothing in a section goes above this
    content_bottom_y: float  # nothing in a section goes below this (clear of the ground bus)


@dataclass(frozen=True)
class LayoutSettings:
    drawable_width: float
    drawable_height: float
    margin_standard: float
    margin_relaxed: float
    divider_clearance: float
    keepout_width: float
    keepout_height: float
    divider: DividerSettings
    ground_bus: GroundBusSettings
    text: TextSettings
    section_label: SectionLabelSettings
    group_mounted: GroupMountedSettings
    placeholder_sizes: PlaceholderSizes
    main_bus: MainBusSettings

    @property
    def keepout_left_x(self) -> float:
        """x where the title block keep-out begins (it runs to the right edge)."""
        return self.drawable_width - self.keepout_width


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
    corner = _read_text(data, "title_block_keepout", "corner")
    if corner != "bottom_right":
        raise SettingsError(
            f'title_block_keepout.corner is "{corner}", but only "bottom_right" is supported.'
        )

    first_side = _read_text(data, "group_mounted", "single_mount_first_side")
    if first_side not in ("left", "right"):
        raise SettingsError(
            f'group_mounted.single_mount_first_side must be "left" or "right", got "{first_side}".'
        )

    section_label_format = _read_text(data, "section_label", "text_format")
    if "{number}" not in section_label_format:
        raise SettingsError('section_label.text_format must contain "{number}".')

    return LayoutSettings(
        drawable_width=_read_number(data, "page", "drawable_width"),
        drawable_height=_read_number(data, "page", "drawable_height"),
        margin_standard=_read_number(data, "page", "margin_standard"),
        margin_relaxed=_read_number(data, "page", "margin_relaxed"),
        divider_clearance=_read_number(data, "section", "divider_clearance"),
        keepout_width=_read_number(data, "title_block_keepout", "width"),
        keepout_height=_read_number(data, "title_block_keepout", "height"),
        divider=DividerSettings(
            layer=_read_text(data, "divider", "layer"),
            bottom_y=_read_number(data, "divider", "bottom_y"),
            top_y=_read_number(data, "divider", "top_y"),
        ),
        ground_bus=GroundBusSettings(
            layer=_read_text(data, "ground_bus", "layer"),
            y=_read_number(data, "ground_bus", "y"),
            start_x=_read_number(data, "ground_bus", "start_x"),
            gap_before_title_block=_read_number(data, "ground_bus", "gap_before_title_block"),
            label_text=_read_text(data, "ground_bus", "label_text"),
            label_offset_x=_read_number(data, "ground_bus", "label_offset_x"),
            label_gap_above_bus=_read_number(data, "ground_bus", "label_gap_above_bus"),
            symbol_offset_x=_read_number(data, "ground_bus", "symbol_offset_x"),
            symbol_stem_length=_read_number(data, "ground_bus", "symbol_stem_length"),
            symbol_bar_widths=_read_number_list(data, "ground_bus", "symbol_bar_widths"),
            symbol_bar_spacing=_read_number(data, "ground_bus", "symbol_bar_spacing"),
        ),
        text=TextSettings(
            layer=_read_text(data, "text", "layer"),
            style=_read_text(data, "text", "style"),
            height=_read_number(data, "text", "height"),
            char_width_factor=_read_number(data, "text", "char_width_factor"),
        ),
        section_label=SectionLabelSettings(
            text_format=section_label_format,
            bottom_y=_read_number(data, "section_label", "bottom_y"),
            gap_above_title_block=_read_number(data, "section_label", "gap_above_title_block"),
        ),
        group_mounted=GroupMountedSettings(
            gap_to_first_level=_read_number(data, "group_mounted", "gap_to_first_level"),
            level_pitch=_read_number(data, "group_mounted", "level_pitch"),
            level_height=_read_number(data, "group_mounted", "level_height"),
            vertical_bus_overhang=_read_number(data, "group_mounted", "vertical_bus_overhang"),
            single_mount_first_side=first_side,
        ),
        placeholder_sizes=PlaceholderSizes(
            main_breaker_width=_read_number(data, "placeholder_sizes", "main_breaker_width"),
            main_breaker_height=_read_number(data, "placeholder_sizes", "main_breaker_height"),
            single_breaker_width=_read_number(data, "placeholder_sizes", "single_breaker_width"),
            single_breaker_height=_read_number(data, "placeholder_sizes", "single_breaker_height"),
            group_mounted_width=_read_number(data, "placeholder_sizes", "group_mounted_width"),
            tie_breaker_width=_read_number(data, "placeholder_sizes", "tie_breaker_width"),
        ),
        main_bus=MainBusSettings(
            phase_spacing=_read_number(data, "main_bus", "phase_spacing"),
            step_width=_read_number(data, "main_bus", "step_width"),
            tie_step_height=_read_number(data, "main_bus", "tie_step_height"),
            content_top_y=_read_number(data, "main_bus", "content_top_y"),
            content_bottom_y=_read_number(data, "main_bus", "content_bottom_y"),
        ),
    )


def _read_value(data, group, key):
    try:
        return data[group][key]
    except (KeyError, TypeError):
        raise SettingsError(f'Missing setting "{group}.{key}" in layout_settings.json.')


def _check_number(value, where) -> float:
    # bool is a kind of int in Python, so rule it out explicitly (true/false is a typo here).
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingsError(f'Setting "{where}" must be a number, got {value!r}.')
    if value < 0:
        raise SettingsError(f'Setting "{where}" must not be negative, got {value}.')
    return float(value)


def _read_number(data, group, key) -> float:
    return _check_number(_read_value(data, group, key), f"{group}.{key}")


def _read_number_list(data, group, key) -> tuple[float, ...]:
    value = _read_value(data, group, key)
    if not isinstance(value, list) or not value:
        raise SettingsError(f'Setting "{group}.{key}" must be a list of numbers.')
    return tuple(_check_number(item, f"{group}.{key}") for item in value)


def _read_text(data, group, key) -> str:
    value = _read_value(data, group, key)
    if not isinstance(value, str) or not value:
        raise SettingsError(f'Setting "{group}.{key}" must be some text, got {value!r}.')
    return value
