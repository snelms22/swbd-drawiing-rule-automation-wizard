"""Sizes for incoming feeds standing on their own (decision 2026-10-22, option B step 2).

Main lugs only (no main breaker points at the feed): the feed's riser runs straight from
the main bus to its termination. The run is at least `gap_bus_to_breaker` +
`gap_breaker_to_input` (what a main breaker's riser has besides the breaker), and grows
to fit the feed's voltage taps, which sit on it nearest the bus first.

Crossing into a main breaker in the next section: the main's line side runs on to where
its input would normally sit, turns across into the feed's section (A on top of the
horizontal run, corners staggered so phases cross without dots, as in the U-turns), and
runs on to the feed's termination. That last run is at least `gap_breaker_to_input` and
grows to fit the feed's voltage taps, nearest the crossing first. The feed's section is
kept on the same page as the main's (they are linked automatically).

Pure Python, no AutoCAD.
"""


def feed_run(settings, taps, feed, minimum: float) -> float:
    """A feed's run from where it starts (the main bus, or the crossing) to its termination."""
    count = len(feed.voltage_taps)
    if taps is None or count == 0:
        return minimum
    return max(minimum, taps.line_side_run(settings, count, overhang=0.0))


def main_lugs_run(settings, taps, feed) -> float:
    mb = settings.main_breaker
    return feed_run(settings, taps, feed, mb.gap_bus_to_breaker + mb.gap_breaker_to_input)


def crossing_run(settings, taps, feed) -> float:
    return feed_run(settings, taps, feed, settings.main_breaker.gap_breaker_to_input)


def main_lugs_height(settings, taps, feed) -> float:
    """Room a main-lugs-only feed needs from the main bus."""
    return main_lugs_run(settings, taps, feed) + settings.main_breaker.input_box_height


def crossing_height(settings, taps, feed, main_height: float) -> float:
    """Room a feed crossing into a main needs from the main bus: the main's own height
    (up to and including where its input would sit), the three phases of the crossing, and
    the feed's run to its termination."""
    return main_height + 2 * settings.main_bus.phase_spacing + crossing_run(settings, taps, feed)


def feed_width(settings, taps, feed) -> float:
    width = settings.placeholder_sizes.main_breaker_width
    if taps is not None and feed.voltage_taps:
        width = max(width, taps.left + taps.right)
    return width


def feed_left_reach(settings, catalog, taps, feed) -> float:
    """How far left of a feed's A phase its termination block (or taps) reach, so the
    feed's riser can sit that far in from the section's edge."""
    reach = 0.0
    io_block = catalog.get(settings.input_output.block) if catalog else None
    if io_block is not None and io_block.connections:
        for flipped in (False, True):
            reach = max(reach, io_block.connection("A", flipped)[0] - io_block.oriented_extents(flipped)[0])
    if taps is not None and feed is not None and feed.voltage_taps:
        reach = max(reach, taps.left)
    return reach
