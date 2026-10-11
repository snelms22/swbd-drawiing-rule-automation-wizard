"""Works out how big a section is from what it holds, and which side each single-mount
level goes on. Pure Python, no AutoCAD.

Sizes are PLACEHOLDERS from config ("placeholder_sizes") until the real blocks are
catalogued; group-mounted spacing ("group_mounted") is measured from the references.

Not yet connected to page fitting: that comes with the bus rules (where the main bus sits
on the page) and the section editor.
"""
from dataclasses import dataclass

from src.model.section_contents import (
    GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, TwinLevel,
)

LEFT = "left"
RIGHT = "right"


@dataclass
class SectionSize:
    width: float
    above_height: float   # room needed above the main bus
    below_height: float   # room needed below the main bus


def section_size(contents: SectionContents, settings) -> SectionSize:
    """Width is the widest thing in the section; heights are measured from the main bus."""
    widths = [_arrangement_width(contents.above, settings), _arrangement_width(contents.below, settings)]
    if contents.tie is not None:
        # The tie sits at the section's right edge, beside everything else (approved).
        widths.append(max(widths) + settings.placeholder_sizes.tie_breaker_width)
    return SectionSize(
        width=max(widths),
        above_height=_arrangement_height(contents.above, settings),
        below_height=_arrangement_height(contents.below, settings),
    )


def single_level_sides(group: GroupMounted, settings) -> list[str | None]:
    """Side for each level, nearest the bus first: "left"/"right" for single levels,
    None for twin levels. Single levels alternate, starting from the configured side;
    a flipped level swaps sides without changing the pattern for the levels after it."""
    side = settings.group_mounted.single_mount_first_side
    sides = []
    for level in group.levels:
        if isinstance(level, TwinLevel):
            sides.append(None)
            continue
        sides.append(_other(side) if level.flipped else side)
        side = _other(side)
    return sides


def _other(side: str) -> str:
    return RIGHT if side == LEFT else LEFT


def _arrangement_width(arrangement, settings) -> float:
    sizes = settings.placeholder_sizes
    if arrangement is None:
        return 0.0
    if isinstance(arrangement, MainBreaker):
        return sizes.main_breaker_width
    if isinstance(arrangement, SingleBreaker):
        return sizes.single_breaker_width
    if isinstance(arrangement, GroupMounted):
        return sizes.group_mounted_width
    raise TypeError(f"Unknown arrangement: {arrangement!r}")


def _arrangement_height(arrangement, settings) -> float:
    sizes = settings.placeholder_sizes
    if arrangement is None:
        return 0.0
    if isinstance(arrangement, MainBreaker):
        return sizes.main_breaker_height
    if isinstance(arrangement, SingleBreaker):
        return sizes.single_breaker_height
    if isinstance(arrangement, GroupMounted):
        return _group_height(arrangement, settings)
    raise TypeError(f"Unknown arrangement: {arrangement!r}")


def _group_height(group: GroupMounted, settings) -> float:
    """From the main bus to the end of the vertical bus:
    gap to level 1, then one pitch per extra level, the level itself, then the overhang."""
    g = settings.group_mounted
    if not group.levels:
        return 0.0
    return (
        g.gap_to_first_level
        + (len(group.levels) - 1) * g.level_pitch
        + g.level_height
        + g.vertical_bus_overhang
    )
