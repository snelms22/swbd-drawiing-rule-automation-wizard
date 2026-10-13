"""Main bus height: where the bus sits in each section (docs/DECISIONS.md, "Main bus height").

Rules:
- The bus only exists where it is used: from the first section that holds something to the
  last one. Empty sections before or after have no bus; empty sections in between are
  simply passed through (2026-10-12).
- The bus starts as LOW as possible: just high enough for what is below it in the first
  section that uses it.
- It stays level from section to section. A section only moves it when it must:
    - the part below the bus needs more room  -> the bus moves up, just enough;
    - the part above the bus needs more room  -> the bus moves down, just enough.
- The section that causes a height change takes the step at its left edge. The step zone
  is the bus itself (`step_width`, 10: A to C) plus `step_clearance` (10) so the vertical
  run stays clear of everything else in the section.
- A tie breaker (at the section's right edge) moves the bus up or down by
  `tie_step_height` as it leaves that section.

Heights are the B (middle) phase. A is `phase_spacing` above it, C the same below it.
Pure Python, no AutoCAD. The bus is planned along the whole lineup, before page fitting,
so a bus height carries over a page break.
"""
from dataclasses import dataclass

ROUNDING_TOLERANCE = 1e-9


@dataclass
class BusPlan:
    entry_y: float   # bus height where it enters the section (left edge)
    body_y: float    # bus height through the section's contents
    exit_y: float    # bus height where it leaves (right edge); differs only after a tie
    starts_bus: bool = False   # the first section that uses the bus
    ends_bus: bool = False     # the last section that uses the bus

    @property
    def steps_at_entry(self) -> bool:
        return abs(self.body_y - self.entry_y) > ROUNDING_TOLERANCE


def step_zone_width(settings) -> float:
    """Extra width a section needs when the bus changes height in it."""
    return settings.main_bus.step_width + settings.main_bus.step_clearance


def plan_bus(sizes, ties, uses_bus, settings, warnings: list[str]) -> list[BusPlan | None]:
    """One BusPlan per section (None where there is no bus). `sizes` are SectionSize
    objects, `ties` the TieBreaker (or None) of each section, `uses_bus` whether each
    section holds anything, all in lineup order."""
    bus = settings.main_bus
    half_bundle = bus.phase_spacing     # B to A (top) and B to C (bottom)
    used = [index for index, flag in enumerate(uses_bus) if flag]
    plans: list[BusPlan | None] = [None] * len(sizes)
    if not used:
        return plans
    first, last = used[0], used[-1]
    sections = range(first, last + 1)
    lowest = {i: bus.content_bottom_y + half_bundle + sizes[i].below_height for i in sections}
    highest = {i: bus.content_top_y - half_bundle - sizes[i].above_height for i in sections}

    for i in sections:
        if lowest[i] > highest[i] + ROUNDING_TOLERANCE:
            warnings.append(
                f"Section {i + 1} is too tall: what is above and below the main bus needs "
                f"{sizes[i].above_height + sizes[i].below_height + 2 * half_bundle:g}, the page "
                f"allows {bus.content_top_y - bus.content_bottom_y:g}."
            )
            highest[i] = lowest[i]       # keep the bottom clear of the ground bus

    floor, ceiling = _make_room_for_ties(sections, lowest, highest, ties, settings, warnings)

    plans: list[BusPlan | None] = [None] * len(sizes)
    level = None                        # current bus height; None before the bus starts
    for i in sections:
        if level is None:
            body = floor[i]              # start as low as possible (allowing for ties)
        else:
            body = min(max(level, floor[i]), ceiling[i])   # move only as far as needed
        entry = body if level is None else level
        exit_ = body
        tie = ties[i]
        if tie is not None:
            exit_ = body - bus.tie_step_height if tie.bus_steps == "down" else body + bus.tie_step_height
        plans[i] = BusPlan(entry_y=entry, body_y=body, exit_y=exit_,
                           starts_bus=i == first, ends_bus=i == last)
        level = exit_
    return plans


def _make_room_for_ties(sections, lowest, highest, ties, settings, warnings):
    """Where the bus may sit in each section so every tie breaker has room for its step
    (decision 2026-10-12 "Room for tie breakers").

    A tie stepping DOWN needs the bus high enough to drop `tie_step_height` and still be
    clear of the ground bus; a tie stepping UP needs it low enough to rise. That need is
    passed back to the sections before the tie, so the bus there is raised (or lowered)
    ahead of time and runs level into the tie. It stops at a section that can't move that
    far (what's above or below it is in the way); the bus then steps up (or down) after
    that section instead, "wrapping" before the tie. Returns {section: lowest allowed bus}
    and {section: highest allowed bus}."""
    bus = settings.main_bus
    half_bundle = bus.phase_spacing
    drop = bus.tie_step_height
    lowest_bus = bus.content_bottom_y + half_bundle
    highest_bus = bus.content_top_y - half_bundle
    floor, ceiling = dict(lowest), dict(highest)
    need_above = need_below = None       # what the section after needs of this one's exit

    for i in reversed(list(sections)):
        tie = ties[i]
        # A need on this section's exit becomes a need on its body (shifted by its own tie).
        shift = 0.0 if tie is None else (drop if tie.bus_steps == "down" else -drop)
        body_above = None if need_above is None else need_above + shift
        body_below = None if need_below is None else need_below + shift
        if tie is not None and tie.bus_steps == "down":
            own = lowest_bus + drop
            if own > highest[i] + ROUNDING_TOLERANCE:
                warnings.append(f"Section {i + 1}: there isn't room above the main bus for the tie "
                                f"breaker to step the bus down {drop:g}.")
            else:
                body_above = own if body_above is None else max(body_above, own)
        if tie is not None and tie.bus_steps == "up":
            own = highest_bus - drop
            if own < lowest[i] - ROUNDING_TOLERANCE:
                warnings.append(f"Section {i + 1}: there isn't room below the main bus for the tie "
                                f"breaker to step the bus up {drop:g}.")
            else:
                body_below = own if body_below is None else min(body_below, own)
        # Apply a need only if this section can take it; otherwise stop passing it back.
        if body_above is not None and body_above <= highest[i] + ROUNDING_TOLERANCE:
            floor[i] = max(floor[i], body_above)
        else:
            body_above = None
        if body_below is not None and body_below >= lowest[i] - ROUNDING_TOLERANCE:
            ceiling[i] = min(ceiling[i], body_below)
        else:
            body_below = None
        # If this section already puts the bus that high (or low) on its own, the sections
        # before it don't need to move: the bus gets there here anyway.
        if body_above is not None and lowest[i] >= body_above - ROUNDING_TOLERANCE:
            body_above = None
        if body_below is not None and highest[i] <= body_below + ROUNDING_TOLERANCE:
            body_below = None
        need_above, need_below = body_above, body_below
    return floor, ceiling
