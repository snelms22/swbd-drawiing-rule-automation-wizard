"""Works out how big a section is from what it holds, and which side each single-mount
level goes on. Pure Python, no AutoCAD.

Sizes are PLACEHOLDERS from config ("placeholder_sizes") until the real blocks are
catalogued; group-mounted spacing ("group_mounted") is measured from the references.
With the feeder block catalogued, a group-mounted section's width comes from the block
(breaker, taps, vertical bus; see feeders.py for how it is drawn).

Too tall for the page (decision 2026-10-13 "Too tall: split the part below the main bus
first"): a section's above and below group-mounted parts normally share one vertical bus,
column 1. When they don't both fit between the top of the drawing area and the ground bus:
- The ABOVE part gets its room first.
- The BELOW part keeps on column 1 the levels that fit; it is cut there (tilde + bracket)
  and the rest continue in column 2, beside it to the right. Column 2 starts
  `continuation_start_gap` below the main bus (tilde + bracket) and runs down.
- Only if the above part alone is too tall (after leaving room for the below part's
  first level) is it split the same way, upward. Its continuation shares column 2.
- A continuation that is still too tall goes on in column 3, and so on.
- Columns are `column_pitch` apart (A phase to A phase), more if the breakers of two
  neighbouring columns would come closer than `column_clearance`.
Only group-mounted parts split. A main or single breaker that doesn't fit is reported by
main_bus.py as before.

CTs (decision 2026-10-21, see current_transformers.py) make a riser, the base of a
group-mounted part's column 1, or the tie's column longer or wider. Without the CT block
in the catalog no room is kept (`room` is None).
"""
from dataclasses import dataclass, field

from src.layout.current_transformers import tie_column_width
from src.layout.incoming_feeds import feed_width, main_lugs_height

from src.model.section_contents import (
    Breaker, GroupMounted, IncomingFeed, LineSideBreaker, MainBreaker, SectionContents, SingleBreaker,
    SingleLevel, TwinLevel, feed_directions, side_away_from_bus,
)

ROUNDING_TOLERANCE = 1e-9

LEFT = "left"
RIGHT = "right"


@dataclass
class SectionSize:
    width: float
    above_height: float   # room needed above the main bus
    below_height: float   # room needed below the main bus


@dataclass
class Column:
    """One vertical bus of a group-mounted section. Levels are given by their index in the
    part's GroupMounted.levels (nearest the bus first)."""
    above: list[int]
    below: list[int]


@dataclass
class ColumnPlan:
    columns: list[Column]      # column 1 (on the main bus) first, then continuations
    a_offsets: list[float]     # each column's A phase, from the section's content edge
    width: float               # all columns, with their breakers
    above_height: float        # room used above the main bus (the tallest column)
    below_height: float        # room used below the main bus
    # Column 1's lead per part (longer with CTs at the base); see column_lead().
    first_leads: dict = field(default_factory=dict)

    def lead(self, part: str, column_index: int, g) -> float:
        if column_index == 0 and part in self.first_leads:
            return self.first_leads[part]
        return column_lead(column_index, g)

    def continues_after(self, part: str, column_index: int) -> bool:
        """Does `part` have levels in a column after this one (so this one is cut)?"""
        return any(getattr(column, part) for column in self.columns[column_index + 1:])


def section_size(contents: SectionContents, settings, feeder_block=None, room=None,
                 taps=None) -> SectionSize:
    """Width is the widest thing in the section; heights are measured from the main bus.
    `feeder_block` is the catalogued feeder block (BlockInfo), or None for placeholders.
    `room` is the CT block's CtRoom and `taps` the voltage tap block's TapRoom, or None."""
    widths = [_arrangement_width(contents.above, "above", settings, room, taps),
              _arrangement_width(contents.below, "below", settings, room, taps)]
    above_height = _arrangement_height(contents.above, "above", settings, room, taps)
    below_height = _arrangement_height(contents.below, "below", settings, room, taps)
    plan = plan_columns(contents, settings, feeder_block, room)
    if plan is not None:
        if feeder_block is not None:
            # Above and below share their columns, so they share one width.
            widths = [w for part, w in zip((contents.above, contents.below), widths)
                      if not isinstance(part, GroupMounted)]
        widths.append(plan.width)
        if isinstance(contents.above, GroupMounted):
            above_height = plan.above_height
        if isinstance(contents.below, GroupMounted):
            below_height = plan.below_height
    if contents.tie is not None:
        # The tie sits at the section's right edge, beside everything else (approved).
        widths.append(max(widths) + tie_column_width(contents.tie, settings, room))
    return SectionSize(width=max(widths), above_height=above_height, below_height=below_height)


def plan_columns(contents: SectionContents, settings, feeder_block=None, room=None) -> ColumnPlan | None:
    """How the section's group-mounted levels are spread over columns (see the top of this
    file). None if the section has no group-mounted levels. `room`: see section_size()."""
    above, below = contents.above, contents.below
    above_count = len(above.levels) if isinstance(above, GroupMounted) else 0
    below_count = len(below.levels) if isinstance(below, GroupMounted) else 0
    if not above_count and not below_count:
        return None

    g = settings.group_mounted
    bus = settings.main_bus
    first_leads = {part: first_lead(getattr(contents, part), part, settings, room)
                   for part in ("above", "below") if isinstance(getattr(contents, part), GroupMounted)}
    ct_reach = (room.left, room.right) if room is not None and any(
        isinstance(getattr(contents, part), GroupMounted) and getattr(contents, part).base_cts
        for part in ("above", "below")) else None
    space = bus.content_top_y - bus.content_bottom_y - 2 * bus.phase_spacing
    above_full = _arrangement_height(above, "above", settings, room)
    below_full = _arrangement_height(below, "below", settings, room)
    if above_full + below_full <= space + ROUNDING_TOLERANCE:
        above_room, below_room = above_full, below_full          # it all fits: no split
    else:
        # The above part gets its room first, leaving the below part room for one level
        # on each of its columns (or all of a main / single breaker, which can't split).
        # A continuation starts further from the bus than column 1, so it needs more.
        below_first = first_leads.get("below", g.gap_to_first_level)
        if below_count > 1:
            below_least = max(_column_height(1, column_lead(1, g), g), _column_height(1, below_first, g))
        elif below_count == 1:
            below_least = _column_height(1, below_first, g)
        else:
            below_least = below_full
        above_room = min(above_full, space - below_least) if above_count else above_full
        below_room = space - above_room

    above_chunks = _split_levels(above_count, above_room, g, first_leads.get("above"))
    below_chunks = _split_levels(below_count, below_room, g, first_leads.get("below"))
    column_count = max(len(above_chunks), len(below_chunks))
    columns = [Column(above=above_chunks[k] if k < len(above_chunks) else [],
                      below=below_chunks[k] if k < len(below_chunks) else [])
               for k in range(column_count)]
    a_offsets, width = _column_positions(columns, contents, settings, feeder_block, ct_reach)
    return ColumnPlan(columns=columns, a_offsets=a_offsets, width=width,
                      above_height=_chunks_height(above_chunks, g, first_leads.get("above")),
                      below_height=_chunks_height(below_chunks, g, first_leads.get("below")),
                      first_leads=first_leads)


def first_lead(group, part, settings, room) -> float:
    """Column 1's lead: `gap_to_first_level`, or longer with CTs at the base."""
    if group.base_cts is not None and room is not None:
        return room.group_lead(part, settings)
    return settings.group_mounted.gap_to_first_level


def column_lead(column_index: int, g) -> float:
    """From the main bus (nearest phase) to the nearest edge of a column's first level:
    column 1 hangs off the main bus; a continuation starts `continuation_start_gap` away
    and its bus runs `vertical_bus_overhang` before the first level."""
    if column_index == 0:
        return g.gap_to_first_level
    return g.continuation_start_gap + g.vertical_bus_overhang


def _column_height(level_count: int, lead: float, g) -> float:
    """From the main bus to the far end of a column's vertical bus."""
    return lead + (level_count - 1) * g.level_pitch + g.level_height + g.vertical_bus_overhang


def _levels_that_fit(room: float, lead: float, g) -> int:
    """How many levels fit in `room` (at least 1, so a column is never empty)."""
    spare = room - _column_height(1, lead, g)
    return 1 + max(0, int((spare + ROUNDING_TOLERANCE) // g.level_pitch))


def _split_levels(count: int, room: float, g, first=None) -> list[list[int]]:
    """Level indices per column, column 1 first. `first`: column 1's lead, if not the usual."""
    chunks, start = [], 0
    while start < count:
        lead = first if not chunks and first is not None else column_lead(len(chunks), g)
        taken = min(count - start, _levels_that_fit(room, lead, g))
        chunks.append(list(range(start, start + taken)))
        start += taken
    return chunks


def _chunks_height(chunks, g, first=None) -> float:
    return max((_column_height(len(chunk), first if k == 0 and first is not None else column_lead(k, g), g)
                for k, chunk in enumerate(chunks)), default=0.0)


def _column_positions(columns, contents, settings, block, ct_reach=None):
    """Each column's A phase from the content edge, and the width of all columns.
    Without the feeder block (placeholders), each extra column adds `column_pitch`.
    `ct_reach`: (left, right) of CTs at the base of column 1, or None."""
    g = settings.group_mounted
    if block is None:
        return ([k * g.column_pitch for k in range(len(columns))],
                settings.placeholder_sizes.group_mounted_width + (len(columns) - 1) * g.column_pitch)
    tap = settings.feeder.tap_length
    bus_width = 2 * settings.main_bus.phase_spacing          # A to C
    reaches = [(_column_reach(column, contents, LEFT, block, settings),
                _column_reach(column, contents, RIGHT, block, settings)) for column in columns]

    def out(reach):                       # from the nearest phase out to the slot's far edge
        return tap + reach if reach else 0.0

    a_offsets = [out(reaches[0][0])]
    if ct_reach is not None:
        a_offsets[0] = max(a_offsets[0], ct_reach[0])       # CTs reach left of column 1
    for k in range(1, len(columns)):
        needed = bus_width + out(reaches[k - 1][1]) + g.column_clearance + out(reaches[k][0])
        if k == 1 and ct_reach is not None:
            needed = max(needed, ct_reach[1] + g.column_clearance + out(reaches[k][0]))
        a_offsets.append(a_offsets[-1] + max(g.column_pitch, needed))
    width = max(a + bus_width + out(right) for a, (_, right) in zip(a_offsets, reaches))
    if ct_reach is not None:
        width = max(width, a_offsets[0] + ct_reach[1])
    return a_offsets, width


def _column_reach(column, contents, side, block, settings) -> float:
    """How far the widest slot on one side of a column reaches out (0 if none)."""
    reaches = []
    for part in ("above", "below"):
        indices = getattr(column, part)
        if not indices:
            continue
        slots = level_slots(getattr(contents, part), settings)
        reaches += [_slot_reach(slots[i][side], side, block, settings)
                    for i in indices if side in slots[i]]
    return max(reaches, default=0.0)


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


def level_slots(group, settings) -> list[dict[str, object]]:
    """For each level (nearest the bus first): {"left": slot, "right": slot}, with only
    the side(s) that level uses."""
    slots = []
    for level, side in zip(group.levels, single_level_sides(group, settings)):
        if isinstance(level, TwinLevel):
            slots.append({LEFT: level.left, RIGHT: level.right})
        else:
            slots.append({side: level.slot})
    return slots


def _slot_reach(slot, side, block, settings) -> float:
    """How far a slot reaches out from where its taps end (away from the vertical bus):
    a breaker by its block's size, a provision or space by its note."""
    if isinstance(slot, Breaker):
        flipped = side == RIGHT
        left, _, right, _ = block.oriented_extents(flipped)
        conn_x = block.connection("A", flipped)[0]
        return (right - conn_x) if flipped else (conn_x - left)
    lines = settings.feeder.note_lines(slot)
    return settings.feeder.provision_text_gap + max(settings.text.estimated_width(line) for line in lines)


def _other(side: str) -> str:
    return RIGHT if side == LEFT else LEFT


def u_turn_count(arrangement, part) -> int:
    """How many U-turns a main or single breaker's bus makes (decision 2026-10-13): one
    when the termination is fed from the other side than the breaker, and one more when
    the breaker is fed on the bus side (the bus U-turns over it into its far end)."""
    breaker_feed, termination_feed = feed_directions(arrangement, part)
    away = side_away_from_bus(part)
    return int(termination_feed != breaker_feed) + int(breaker_feed != away)


def riser_has_taps(arrangement, part, taps) -> bool:
    """Are voltage taps drawn on this main breaker's feed? Only on the straight run for now
    (not when the cables U-turn or the breaker is fed on the bus side)."""
    if (not isinstance(arrangement, MainBreaker) or arrangement.feed is None
            or not arrangement.feed.voltage_taps or taps is None):
        return False
    breaker_feed, termination_feed = feed_directions(arrangement, part)
    return breaker_feed == termination_feed == side_away_from_bus(part)


def riser_has_cts(arrangement, part, room) -> bool:
    """Are CTs drawn on this main / single breaker's riser? (Not yet for a breaker fed on
    the bus side: its riser is a U-turn.)"""
    if arrangement.cts is None or room is None:
        return False
    breaker_feed, _ = feed_directions(arrangement, part)
    return breaker_feed == side_away_from_bus(part)


def _arrangement_width(arrangement, part, settings, room=None, taps=None) -> float:
    sizes = settings.placeholder_sizes
    if arrangement is None:
        return 0.0
    if isinstance(arrangement, IncomingFeed):
        return feed_width(settings, taps, arrangement)
    if isinstance(arrangement, LineSideBreaker):
        return sizes.main_breaker_width
    if isinstance(arrangement, (MainBreaker, SingleBreaker)):
        is_main = isinstance(arrangement, MainBreaker)
        width = sizes.main_breaker_width if is_main else sizes.single_breaker_width
        # Each U-turn runs off to one side of the breaker.
        width += u_turn_count(arrangement, part) * settings.main_breaker.u_turn_width
        has_cts = riser_has_cts(arrangement, part, room)
        if has_cts:
            # The riser moves right so the CTs clear the section's edge; the CTs reach
            # further right than the breaker.
            width = max(width + room.left, room.left + room.right)
        if riser_has_taps(arrangement, part, taps):
            # The taps' wires and "TO FA-n" reach right of the riser.
            width = max(width, (room.left if has_cts else taps.left) + taps.right)
        return width
    if isinstance(arrangement, GroupMounted):
        return sizes.group_mounted_width
    raise TypeError(f"Unknown arrangement: {arrangement!r}")


def _arrangement_height(arrangement, part, settings, room=None, taps=None) -> float:
    sizes = settings.placeholder_sizes
    if arrangement is None:
        return 0.0
    if isinstance(arrangement, IncomingFeed):
        # Main lugs only; a feed crossing into a main is resized by page_fitter.
        return main_lugs_height(settings, taps, arrangement)
    if isinstance(arrangement, LineSideBreaker):
        return sizes.main_breaker_height       # resized by page_fitter when it is drawn
    if isinstance(arrangement, (MainBreaker, SingleBreaker)):
        is_main = isinstance(arrangement, MainBreaker)
        height = sizes.main_breaker_height if is_main else sizes.single_breaker_height
        breaker_feed, _ = feed_directions(arrangement, part)
        if breaker_feed != side_away_from_bus(part):
            # Fed on the bus side: the bus's U-turn goes past the breaker's far end.
            height += settings.main_breaker.u_turn_depth + 2 * settings.main_bus.phase_spacing
        if riser_has_cts(arrangement, part, room):
            height += room.riser_gap(settings) - settings.main_breaker.gap_bus_to_breaker
        if riser_has_taps(arrangement, part, taps):
            height += (taps.line_side_run(settings, len(arrangement.feed.voltage_taps))
                       - settings.main_breaker.gap_breaker_to_input)
        return height
    if isinstance(arrangement, GroupMounted):
        return _group_height(arrangement, part, settings, room)
    raise TypeError(f"Unknown arrangement: {arrangement!r}")


def _group_height(group: GroupMounted, part, settings, room=None) -> float:
    """All levels on one column, from the main bus to the end of the vertical bus:
    lead to level 1, then one pitch per extra level, the level itself, then the overhang."""
    g = settings.group_mounted
    if not group.levels:
        return 0.0
    return _column_height(len(group.levels), first_lead(group, part, settings, room), g)
