"""Line-side (load-bank) breakers (decision 2026-10-22, option B step 3), measured from
Sabey-011475 (52-LBBA tied into the gen main 52-MA-GEN-A):

    main's termination
      | | |
      | | |   voltage taps (FA-n), if any, beyond the tie
      | | |
      +-+-+---------+       the tie: A on top, each phase tees into its own riser phase
        +-+---------+-+     with a dot; `tie_gap` from the main breaker's line-side
          +---------+-+-+   terminals to the tie's nearest phase
      [main breaker]  | | |
                     [line-side breaker]  `gap_to_breaker` beyond the tie's outer phase
                      | | |
                     termination (output)  `gap_breaker_to_output` beyond its other end

The line-side breaker stands in the section next to the main, on the same side of the bus,
and is drawn with the main (like a feed crossing into a main). Its section doesn't carry
the main bus unless something else in it does, and the two sections stay on one page.

Pure Python, no AutoCAD.
"""
from src.layout.section_builder import riser_has_cts


def line_side_run(settings, taps, tap_count: int, has_tie: bool) -> float:
    """A main breaker's line-side terminals to its termination: the load-bank tie nearest
    the breaker (if any), then the voltage taps, then the termination. At least
    `gap_breaker_to_input`."""
    usual = settings.main_breaker.gap_breaker_to_input
    if not has_tie:
        return taps.line_side_run(settings, tap_count) if taps is not None and tap_count else usual
    start = tie_reach(settings)
    if taps is not None and tap_count:
        return max(usual, taps.line_side_run(settings, tap_count, overhang=start))
    return max(usual, start + settings.voltage_taps.clearance)


def tie_reach(settings) -> float:
    """From the main breaker's line-side terminals to the tie's outer phase."""
    return settings.line_side_breakers.tie_gap + 2 * settings.main_bus.phase_spacing


def breaker_pole(settings, catalog, mounting) -> float:
    """Top terminals to bottom terminals of a main breaker block (10 if not catalogued)."""
    block = catalog.get(settings.main_breaker.blocks[mounting]) if catalog else None
    if block is None or not block.top_terminals or not block.bottom_terminals:
        return 10.0
    return block.top_terminals[0][1] - block.bottom_terminals[0][1]


def line_side_breaker_height(settings, catalog, room, main, part, line_side) -> float:
    """Room a line-side breaker needs from the main bus (its section is drawn from the
    main's bus height): the main's riser up to its line-side terminals, the tie, the gap,
    the line-side breaker, the gap to its output, and the output block."""
    ls = settings.line_side_breakers
    main_gap = (room.riser_gap(settings) if riser_has_cts(main, part, room)
                else settings.main_breaker.gap_bus_to_breaker)
    return (main_gap + breaker_pole(settings, catalog, main.mounting) + tie_reach(settings)
            + ls.gap_to_breaker + breaker_pole(settings, catalog, line_side.mounting)
            + ls.gap_breaker_to_output + settings.main_breaker.input_box_height)
