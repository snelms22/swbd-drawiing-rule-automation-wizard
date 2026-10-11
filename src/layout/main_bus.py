"""Main bus height: where the bus sits in each section (docs/DECISIONS.md, "Main bus height").

Rules:
- The bus starts as LOW as possible: just high enough for what is below it in the first
  section.
- It stays level from section to section. A section only moves it when it must:
    - the part below the bus needs more room  -> the bus moves up, just enough;
    - the part above the bus needs more room  -> the bus moves down, just enough.
- The section that causes a height change takes the step at its left edge, which adds
  `step_width` (10) to that section's width.
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

    @property
    def steps_at_entry(self) -> bool:
        return abs(self.body_y - self.entry_y) > ROUNDING_TOLERANCE


def plan_bus(sizes, ties, settings, warnings: list[str]) -> list[BusPlan]:
    """One BusPlan per section. `sizes` are SectionSize objects, `ties` the TieBreaker (or
    None) of each section, both in lineup order."""
    bus = settings.main_bus
    half_bundle = bus.phase_spacing     # B to A (top) and B to C (bottom)
    plans = []
    level = None                        # current bus height; None before the first section

    for number, (size, tie) in enumerate(zip(sizes, ties), start=1):
        lowest = bus.content_bottom_y + half_bundle + size.below_height
        highest = bus.content_top_y - half_bundle - size.above_height

        if lowest > highest + ROUNDING_TOLERANCE:
            warnings.append(
                f"Section {number} is too tall: what is above and below the main bus needs "
                f"{size.above_height + size.below_height + 2 * half_bundle:g}, the page allows "
                f"{bus.content_top_y - bus.content_bottom_y:g}."
            )
            body = lowest                # keep the bottom clear of the ground bus
        elif level is None:
            body = lowest                # start as low as possible
        else:
            body = min(max(level, lowest), highest)   # move only as far as needed

        entry = body if level is None else level
        exit_ = body
        if tie is not None:
            exit_ = body - bus.tie_step_height if tie.bus_steps == "down" else body + bus.tie_step_height
            lowest_bus = bus.content_bottom_y + half_bundle
            highest_bus = bus.content_top_y - half_bundle
            if not (lowest_bus - ROUNDING_TOLERANCE <= exit_ <= highest_bus + ROUNDING_TOLERANCE):
                warnings.append(
                    f"Section {number}: the tie breaker steps the bus {tie.bus_steps} to "
                    f"{exit_:g}, outside the usable height ({lowest_bus:g} to {highest_bus:g}). "
                    f"Try stepping {'up' if tie.bus_steps == 'down' else 'down'}."
                )

        plans.append(BusPlan(entry_y=entry, body_y=body, exit_y=exit_))
        level = exit_

    return plans
