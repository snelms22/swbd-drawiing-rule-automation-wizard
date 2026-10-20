"""Saving and opening switchboard projects (.swbd files). Decisions 2026-10-15.

A project file is plain JSON, readable in any text editor. It holds only what the engineer
entered: the switchboard's name and its sections in lineup order, with every breaker's
label, mounting, feed directions and block attribute values. Page layout, bus heights and
positions are NOT saved: they are worked out again from the current rules every time.

    {
      "format_version": 1,
      "saved_with": "2.0.0",
      "name": "...",
      "sections": [
        {"push_to_next_page": false, "link_with_next": false,
         "above": {...} or null, "below": {...} or null, "tie": {...} or null}
      ]
    }

An arrangement ("above" / "below") has a "kind":
    "drawing_info":   the General Drawing Information fields (job number, revision, ...);
                      missing in older files, which then get the defaults.
    Every breaker also has "comms": true/false (missing = false).
    "main breaker":   label, mounting, breaker_feed, termination_feed,
                      breaker_attributes, input_attributes
    "single breaker": label, breaker_feed, termination_feed,
                      breaker_attributes, output_attributes
    "group mounted":  levels, nearest the bus first:
                      {"type": "twin", "left": slot, "right": slot}
                      {"type": "single", "flipped": bool, "slot": slot}
                      a slot is {"breaker": label, "attributes": {...}},
                      {"provision": info}, or {"space": true}
A tie is: label, bus_steps ("up" / "down"), mounting, breaker_attributes.

`format_version` is raised whenever the format changes; opening an older file upgrades it
here, so old projects keep opening. Pure Python: no AutoCAD, no UI.
"""
import json
from pathlib import Path

from src.model.section_contents import (
    FIXED, Breaker, GroupMounted, MainBreaker, Provision, SectionContents, SingleBreaker, Space,
    SingleLevel, TieBreaker, TwinLevel,
)
from dataclasses import asdict, fields

from src.model.drawing_info import DrawingInfo
from src.model.switchboard import Section, Switchboard
from src.version import VERSION

EXTENSION = ".swbd"
FORMAT_VERSION = 1

MAIN = "main breaker"
SINGLE = "single breaker"
GROUP = "group mounted"


class ProjectFileError(Exception):
    """A project file that can't be read, with a message the engineer can act on."""


# --- Saving ---------------------------------------------------------------------------

def save_project(switchboard: Switchboard, path) -> Path:
    """Write the switchboard to `path` (overwriting it), adding .swbd if it's missing.
    Returns the path written."""
    path = Path(path)
    if path.suffix.lower() != EXTENSION:
        path = path.with_name(path.name + EXTENSION)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(switchboard_to_dict(switchboard), indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def switchboard_to_dict(switchboard: Switchboard) -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "saved_with": VERSION,
        "name": switchboard.name,
        "drawing_info": asdict(switchboard.drawing_info),
        "sections": [_section_to_dict(section) for section in switchboard.sections],
    }


def _section_to_dict(section: Section) -> dict:
    contents = section.contents
    return {
        "push_to_next_page": section.push_to_next_page,
        "link_with_next": section.link_with_next,
        "above": _arrangement_to_dict(contents.above),
        "below": _arrangement_to_dict(contents.below),
        "tie": _tie_to_dict(contents.tie),
    }


def _arrangement_to_dict(arrangement):
    if arrangement is None:
        return None
    if isinstance(arrangement, MainBreaker):
        return {
            "kind": MAIN,
            "label": arrangement.breaker.label,
            "comms": arrangement.breaker.comms,
            "mounting": arrangement.mounting,
            "breaker_feed": arrangement.breaker_feed,
            "termination_feed": arrangement.termination_feed,
            "breaker_attributes": dict(arrangement.breaker.attributes),
            "input_attributes": dict(arrangement.input_attributes),
        }
    if isinstance(arrangement, SingleBreaker):
        return {
            "kind": SINGLE,
            "label": arrangement.breaker.label,
            "comms": arrangement.breaker.comms,
            "breaker_feed": arrangement.breaker_feed,
            "termination_feed": arrangement.termination_feed,
            "breaker_attributes": dict(arrangement.breaker.attributes),
            "output_attributes": dict(arrangement.output_attributes),
        }
    if isinstance(arrangement, GroupMounted):
        return {"kind": GROUP, "levels": [_level_to_dict(level) for level in arrangement.levels]}
    raise TypeError(f"Unknown arrangement: {arrangement!r}")


def _level_to_dict(level) -> dict:
    if isinstance(level, TwinLevel):
        return {"type": "twin", "left": _slot_to_dict(level.left), "right": _slot_to_dict(level.right)}
    return {"type": "single", "flipped": level.flipped, "slot": _slot_to_dict(level.slot)}


def _slot_to_dict(slot) -> dict:
    if isinstance(slot, Provision):
        return {"provision": slot.info}
    if isinstance(slot, Space):
        return {"space": True}
    return {"breaker": slot.label, "comms": slot.comms, "attributes": dict(slot.attributes)}


def _tie_to_dict(tie):
    if tie is None:
        return None
    return {
        "label": tie.breaker.label,
        "comms": tie.breaker.comms,
        "bus_steps": tie.bus_steps,
        "mounting": tie.mounting,
        "breaker_attributes": dict(tie.breaker.attributes),
    }


# --- Opening --------------------------------------------------------------------------

def open_project(path) -> Switchboard:
    """Read a project file. Raises ProjectFileError with a plain message if it can't."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProjectFileError(f"Project file not found: {path}")
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectFileError(f"{path.name} is not a readable project file: {error}")
    try:
        return switchboard_from_dict(data)
    except ProjectFileError as error:
        raise ProjectFileError(f"{path.name}: {error}")
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ProjectFileError(f"{path.name} is damaged or incomplete ({type(error).__name__}: {error}).")


def switchboard_from_dict(data: dict) -> Switchboard:
    if not isinstance(data, dict) or "format_version" not in data:
        raise ProjectFileError("this is not a switchboard project file.")
    version = data["format_version"]
    if not isinstance(version, int) or version > FORMAT_VERSION:
        raise ProjectFileError(
            f"it was saved by a newer version of the configurator (file format {version}); "
            f"this version reads format {FORMAT_VERSION} and older. Update the configurator.")
    data = _upgrade(data)
    return Switchboard(
        name=data.get("name") or "Switchboard",
        sections=[_section_from_dict(section) for section in data["sections"]],
        drawing_info=_drawing_info_from_dict(data.get("drawing_info") or {}),
    )


def _drawing_info_from_dict(data: dict) -> DrawingInfo:
    """Older files have no drawing_info: every field keeps its default."""
    known = {f.name for f in fields(DrawingInfo)}
    return DrawingInfo(**{name: str(value) for name, value in data.items() if name in known})


def _upgrade(data: dict) -> dict:
    """Bring an older file up to the current format. (Format 1 is the first: nothing to
    do yet. When format 2 arrives, its changes are applied here, one version at a time.)"""
    return data


def _section_from_dict(data: dict) -> Section:
    return Section(
        contents=SectionContents(
            above=_arrangement_from_dict(data.get("above")),
            below=_arrangement_from_dict(data.get("below")),
            tie=_tie_from_dict(data.get("tie")),
        ),
        push_to_next_page=bool(data.get("push_to_next_page", False)),
        link_with_next=bool(data.get("link_with_next", False)),
    )


def _arrangement_from_dict(data):
    if data is None:
        return None
    kind = data["kind"]
    if kind == MAIN:
        return MainBreaker(
            breaker=_breaker(data["label"], data),
            mounting=data["mounting"],
            input_attributes=_texts(data.get("input_attributes")),
            breaker_feed=data.get("breaker_feed", ""),
            termination_feed=data.get("termination_feed", ""),
        )
    if kind == SINGLE:
        return SingleBreaker(
            breaker=_breaker(data["label"], data),
            output_attributes=_texts(data.get("output_attributes")),
            breaker_feed=data.get("breaker_feed", ""),
            termination_feed=data.get("termination_feed", ""),
        )
    if kind == GROUP:
        return GroupMounted([_level_from_dict(level) for level in data["levels"]])
    raise ProjectFileError(f'unknown arrangement "{kind}".')


def _level_from_dict(data: dict):
    if data["type"] == "twin":
        return TwinLevel(_slot_from_dict(data["left"]), _slot_from_dict(data["right"]))
    if data["type"] == "single":
        return SingleLevel(_slot_from_dict(data["slot"]), flipped=bool(data.get("flipped", False)))
    raise ProjectFileError(f'unknown level type "{data["type"]}".')


def _slot_from_dict(data: dict):
    if "provision" in data:
        return Provision(data["provision"])
    if "space" in data:
        return Space()
    return Breaker(data["breaker"], attributes=_texts(data.get("attributes")),
                   comms=bool(data.get("comms", False)))


def _tie_from_dict(data):
    if data is None:
        return None
    return TieBreaker(
        breaker=_breaker(data["label"], data),
        bus_steps=data["bus_steps"],
        mounting=data["mounting"],
    )


def _breaker(label: str, data: dict) -> Breaker:
    """A main, single or tie breaker: label, block attributes, comms (False if missing)."""
    return Breaker(label, attributes=_texts(data.get("breaker_attributes")),
                   comms=bool(data.get("comms", False)))


def _texts(values) -> dict[str, str]:
    """Attribute values as {tag: text}."""
    return {str(tag): str(text) for tag, text in (values or {}).items()}


# --- Checking against the current blocks ---------------------------------------------

def attributes_no_longer_on_blocks(switchboard: Switchboard, settings, catalog) -> list[str]:
    """Attribute values saved in the project whose tag the block no longer has. They are
    kept in the project (nothing is dropped); the engineer is told so on opening."""
    if not catalog:
        return []
    found = []

    def check(where, block_name, values):
        block = catalog.get(block_name)
        if block is None or not block.attributes:
            return
        tags = {attribute.tag for attribute in block.attributes}
        for tag in values:
            if tag not in tags:
                found.append(f'{where}: attribute {tag} is no longer on block {block_name} '
                             f'(its value is kept in the project).')

    mb, io, fd = settings.main_breaker, settings.input_output, settings.feeder
    for number, section in enumerate(switchboard.sections, start=1):
        for part in ("above", "below"):
            arrangement = getattr(section.contents, part)
            where = f"Section {number} {part}"
            if isinstance(arrangement, MainBreaker):
                check(where, mb.blocks[arrangement.mounting], arrangement.breaker.attributes)
                check(where, io.block, arrangement.input_attributes)
            elif isinstance(arrangement, SingleBreaker):
                check(where, mb.blocks[FIXED], arrangement.breaker.attributes)
                check(where, io.block, arrangement.output_attributes)
            elif isinstance(arrangement, GroupMounted):
                for level in arrangement.levels:
                    slots = [level.left, level.right] if isinstance(level, TwinLevel) else [level.slot]
                    for slot in slots:
                        if isinstance(slot, Breaker):
                            check(f"{where}, {slot.label or 'feeder'}", fd.block, slot.attributes)
        tie = section.contents.tie
        if tie is not None:
            check(f"Section {number} tie", mb.blocks[tie.mounting], tie.breaker.attributes)
    return found
