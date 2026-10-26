"""The interlock line between two main breakers (decision 2026-10-26). Pure Python, no AutoCAD.

Drawn as in Sabey-011486 and NTT-013631, on its own layer (INTERLOCK in HYPER_A, whose
linetype makes it dashed): a line at the breakers' mid-height (where
the breaker's own dashed line ties its three poles together), from just past the left
main's C terminal, running through its label text as the references do, to just short of
the right main's A terminal. The text sits centred on the line in the stretch after the
left main's block, with a background mask so the dashes don't run through it.

When the two breakers are at different heights the line steps:

    left main  -------------------+
                                  |   (halfway between the divider and the right
                                  +-------  right main     section's contents)

The step stays in the empty strip beside the divider: nothing in either section is drawn
there, and the dividers' own dashed line is left clear.

All gaps and the wording are in config/layout_settings.json ("interlocks").
"""
from dataclasses import dataclass

ROUNDING_TOLERANCE = 1e-9

Point = tuple[float, float]


@dataclass
class InterlockLine:
    points: list[Point]         # the dashed line, left to right: 2 points, or 4 when it steps
    text_lines: tuple[str, ...]
    text_x: float               # centre of the text
    text_y: float               # middle of the text (on the line)


def interlock_line(interlock, left_breaker, right_breaker, divider_x, settings, catalog) -> InterlockLine:
    """The line between two breaker blocks as placed (BlockPlacements); `left_breaker` is in
    the section before `divider_x`, `right_breaker` in the one after it."""
    s = settings.interlocks
    left_block, right_block = catalog[left_breaker.block], catalog[right_breaker.block]
    left_y = _mid_height(left_breaker, left_block)
    right_y = _mid_height(right_breaker, right_block)
    start_x = left_breaker.position[0] + left_block.top_terminals[2][0] + s.start_past_left_c
    end_x = right_breaker.position[0] + right_block.top_terminals[0][0] - s.end_before_right_a
    if abs(left_y - right_y) < ROUNDING_TOLERANCE:
        points = [(start_x, left_y), (end_x, right_y)]
        text_end_x = end_x
    else:
        step_x = divider_x + settings.divider_clearance / 2
        points = [(start_x, left_y), (step_x, left_y), (step_x, right_y), (end_x, right_y)]
        text_end_x = step_x
    # Centred between the left main's block (its label) and the end of the first run.
    text_start_x = left_breaker.position[0] + left_block.extents[2]
    return InterlockLine(points, s.text_lines(interlock), (text_start_x + text_end_x) / 2, left_y)


def _mid_height(placement, block) -> float:
    """Halfway between the breaker's top and bottom terminals."""
    return placement.position[1] + (block.top_terminals[0][1] + block.bottom_terminals[0][1]) / 2
