"""Loads catalog/blocks.json: where each library block connects, and how big it is.

The layout uses this to line the bus up with a block's terminals without AutoCAD. Block
geometry itself is never redrawn; these are only the block's own reference points.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from src.layout.settings import SettingsError

Point = tuple[float, float]


@dataclass(frozen=True)
class AttributeInfo:
    tag: str        # e.g. "BREAKER_NAME"
    prompt: str     # written in the block by Sammy; shown as the field label in the app
    default: str


@dataclass(frozen=True)
class BlockInfo:
    name: str
    # A, B, C terminals at the top and bottom of the block as drawn. Which one is "line"
    # and which is "load" depends on power flow (top-fed or bottom-fed), not on the block.
    top_terminals: tuple[Point, ...]
    bottom_terminals: tuple[Point, ...]
    extents: tuple[float, float, float, float]   # left, bottom, right, top (block coords)
    # Connection points read from the block's markers, per flip: {"not_flipped": {"A": (x, y),
    # ...}, "flipped": {...}}. Empty for blocks without markers.
    connections: dict = None
    extents_flipped: tuple | None = None          # extents when flipped (if it can flip)
    visibility_states: tuple = ()
    attributes: tuple = ()                        # AttributeInfo, in the block's order

    def connection(self, phase: str, flipped: bool) -> Point:
        return tuple(self.connections["flipped" if flipped else "not_flipped"][phase])

    def oriented_extents(self, flipped: bool):
        return self.extents_flipped if flipped and self.extents_flipped else self.extents

    @property
    def width(self) -> float:
        return self.extents[2] - self.extents[0]


def load_block_catalog(path) -> dict[str, BlockInfo]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"Block catalog not found: {path}")
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path} is not valid JSON: {error}")

    catalog = {}
    for name, entry in data.get("blocks", {}).items():
        try:
            catalog[name] = BlockInfo(
                name=name,
                top_terminals=tuple(tuple(p) for p in entry.get("top_terminals", [])),
                bottom_terminals=tuple(tuple(p) for p in entry.get("bottom_terminals", [])),
                extents=tuple(entry["extents"]),
                connections=entry.get("connections") or {},
                extents_flipped=tuple(entry["extents_flipped"]) if "extents_flipped" in entry else None,
                visibility_states=tuple(entry.get("visibility_states", [])),
                attributes=tuple(AttributeInfo(a["tag"], a.get("prompt", ""), a.get("default", ""))
                                 for a in entry.get("attributes", [])),
            )
        except (KeyError, TypeError) as error:
            raise SettingsError(f'Block "{name}" in {path.name} is incomplete: {error}')
        if len(catalog[name].extents) != 4:
            raise SettingsError(f'Block "{name}" in {path.name}: extents needs 4 numbers.')
    return catalog
