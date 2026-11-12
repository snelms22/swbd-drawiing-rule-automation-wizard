"""Page fitting: decides which page each section goes on, and where.

Pure Python, no AutoCAD. The preview (and later the AutoCAD step) both draw from the
result of fit_pages(), so they always agree.

Coordinates are drawing units measured from the bottom-left corner of a page's
drawable area, with y pointing UP (the same direction as AutoCAD).

Rules applied (each one is recorded in docs/DECISIONS.md):
- Sections keep the order they were entered in. They are never reordered.
- Each section's edges sit `divider_clearance` outside its components, and neighbouring
  sections share one edge. (Which edges actually get a drawn divider line is decided in
  page_parts.py.)
- The side margin is measured from the edge of the drawable area to the outermost
  section edge.
- Pages use the standard side margin. If the next section (or linked group) only fits
  with the relaxed margin, that page switches to the relaxed margin.
- Pages fill left to right with as many sections as fit.
- "Push to next page" starts that section on a new page.
- Linked sections stay together; if they don't fit after what is already on the page,
  the whole group moves to a fresh page.
- A section must not reach down into the title block keep-out (bottom-right corner).
  If it would, it moves to the next page.
- Anything that can't fit even on an empty page is placed anyway, overflowing, with a
  warning, so the problem is visible.
"""
from dataclasses import dataclass, field

from src.layout.current_transformers import ct_room, lineup_ct_attributes, tie_step_height
from src.layout.device_pages import device_pages, three_line_sheet_values
from src.layout.voltage_taps import lineup_tap_attributes, tap_room
from src.layout.feeders import feeder_block
from src.layout.incoming_feeds import crossing_height
from src.layout.line_side_breakers import line_side_breaker_height, line_side_run
from src.layout.page_parts import PageParts, add_page_parts
from src.layout.settings import LayoutSettings
from src.layout.main_bus import BusPlan, plan_bus, step_zone_width
from src.layout.section_builder import plan_columns, section_size
from src.model.devices import voltage_taps_in
from src.model.feeds import feed_links, feeds_pointed_at, line_side_links, standalone_feeds
from src.model.interlocks import interlock_links
from src.model.switchboard import Switchboard

# Allowance for floating-point rounding when comparing positions, so that a section
# which fits exactly (e.g. right edge at 490.0000000001) still counts as fitting.
ROUNDING_TOLERANCE = 1e-9


@dataclass
class SectionBox:
    """What page fitting needs to know about a section: its size and page controls.
    Built from the section's contents by fit_pages(); tests build them directly."""
    width: float      # outermost component to outermost component (clearance added later)
    height: float     # top of the highest component to the bottom of the lowest
    push_to_next_page: bool = False
    link_with_next: bool = False
    # Filled in by fit_pages() from the section's contents. Tests that leave them out get
    # a plain box hanging from the top margin.
    top_y: float | None = None          # y of the highest component
    bus: BusPlan | None = None          # main bus height in this section
    above_height: float = 0.0           # room used above the main bus
    below_height: float = 0.0           # room used below the main bus
    has_tie: bool = False
    contents: object = None             # the section's SectionContents (for drawing its parts)
    # CT block attribute values per part ("above", "below", "tie"), numbered through the
    # lineup by fit_pages().
    ct_attributes: dict = field(default_factory=dict)
    # Voltage tap block attribute values per part: {"above": [per tap], ...}.
    tap_attributes: dict = field(default_factory=dict)
    # A main breaker fed from a feed in the next section: {part: (feed's section index,
    # feed's part)}; with a line-side breaker in the next section tied into its feed:
    # {part: (that section's index, its part)}. Those parts are listed in their own
    # section's `parts_drawn_elsewhere`: they are drawn with the main (decision 2026-10-22).
    feed_crossings: dict = field(default_factory=dict)
    line_side_ties: dict = field(default_factory=dict)
    parts_drawn_elsewhere: set = field(default_factory=set)
    # A feed a main breaker points at that can't be drawn (the warnings say why): it stays a
    # placeholder box instead of being drawn as main lugs only.
    feed_parts_not_drawn: set = field(default_factory=set)
    # Interlocks (InterlockLinks) from a main in this section to a main in the next one
    # (decision 2026-10-26); the two sections are linked so they share a page.
    interlocks: list = field(default_factory=list)


@dataclass
class PlacedSection:
    section: SectionBox
    number: int               # position in the lineup: 1 for the first section, and so on
    # "divider" here means the section's edge; a line is only drawn at some edges.
    left_divider_x: float
    right_divider_x: float
    component_left_x: float
    component_right_x: float
    component_top_y: float
    component_bottom_y: float


@dataclass
class Page:
    number: int          # 1, 2, 3 ...
    side_margin: float   # standard or relaxed, whichever this page needed
    placed_sections: list[PlacedSection] = field(default_factory=list)
    # Dividers, ground bus and section labels; filled in by page_parts.add_page_parts().
    parts: PageParts | None = None

    @property
    def edge_xs(self) -> list[float]:
        """x of every section edge on the page, left to right (shared edges listed once)."""
        if not self.placed_sections:
            return []
        return [self.placed_sections[0].left_divider_x] + [
            placed.right_divider_x for placed in self.placed_sections
        ]


@dataclass
class LayoutResult:
    pages: list[Page]
    warnings: list[str]


def fit_pages(switchboard: Switchboard, settings: LayoutSettings, catalog=None,
              devices=None) -> LayoutResult:
    """Work out each section's size from its contents, then fit the sections onto pages.
    With a block catalog, main breakers are drawn with their real block; without one they
    are placeholder boxes. With the device settings (config/devices.json), the device pages
    follow the 3-line pages (decision 2026-10-23)."""
    sections = switchboard.sections
    feeder = feeder_block(settings, catalog)      # None = group-mounted widths are placeholders
    room = ct_room(settings, catalog)             # None = CT block not catalogued: no CTs drawn
    taps = tap_room(settings, catalog)            # None = tap block not catalogued: no taps drawn
    sizes = [section_size(section.contents, settings, feeder, room, taps) for section in sections]
    bus_warnings: list[str] = []
    if catalog is not None and room is None and _has_cts(sections):
        bus_warnings.append(f'CTs are not drawn: block "{settings.current_transformers.block}" '
                            f"isn't in catalog/blocks.json with its visibility states (run Audit Blocks).")
    if catalog is not None and taps is None and voltage_taps_in(switchboard):
        bus_warnings.append(f'Voltage taps are not drawn: block "{settings.voltage_taps.block}" '
                            f"isn't in catalog/blocks.json with its visibility states (run Audit Blocks).")
    # Feeds crossing into a main breaker in the next section (decision 2026-10-22). The
    # feed needs the main's height plus its own run; a section holding nothing else doesn't
    # carry the main bus (it only exists where it is used).
    links, feed_problems = feed_links(switchboard)
    bus_warnings += feed_problems
    # {part: the main's section index} per section, for parts drawn with a main elsewhere.
    drawn_with = [{} for _ in sections]
    for link in links:
        drawn_with[link.feed.section_index][link.feed.part] = link.main_section_index
        main_height = getattr(sizes[link.main_section_index], f"{link.main_part}_height")
        feed_height = crossing_height(settings, taps, link.feed.feed, main_height)
        setattr(sizes[link.feed.section_index], f"{link.feed.part}_height", feed_height)
        # The feed is drawn from the main's bus height, so the main's section must leave room
        # for it when the bus is placed (2026-10-22).
        name = f"{link.main_part}_height"
        setattr(sizes[link.main_section_index], name,
                max(getattr(sizes[link.main_section_index], name), feed_height))
    # Line-side (load-bank) breakers tied into a main's feed in the next section: the main's
    # line side grows for the tie; the breaker's part is drawn from the main's bus height.
    line_side, line_side_problems = line_side_links(switchboard)
    bus_warnings += line_side_problems
    for tie in line_side:
        main_index, main = tie.feed.section_index, tie.feed.main
        drawn_with[tie.section_index][tie.part] = main_index
        tap_count = len(main.feed.voltage_taps) if taps is not None else 0
        growth = (line_side_run(settings, taps, tap_count, True)
                  - line_side_run(settings, taps, tap_count, False))
        name = f"{tie.feed.part}_height"
        setattr(sizes[main_index], name, getattr(sizes[main_index], name) + growth)
        breaker_height = line_side_breaker_height(settings, catalog, room, main, tie.part, tie.breaker,
                                                  taps)
        setattr(sizes[tie.section_index], f"{tie.part}_height", breaker_height)
        # Drawn from the main's bus height: the main's section must leave room for it too.
        setattr(sizes[main_index], name, max(getattr(sizes[main_index], name), breaker_height))
    uses_bus = [_holds_something(section.contents, set(parts)) for section, parts in zip(sections, drawn_with)]
    ties = [s.contents.tie for s in sections]
    plans = plan_bus(sizes, ties, uses_bus, settings, bus_warnings,
                     [tie_step_height(tie, settings, room) for tie in ties])
    ct_values = lineup_ct_attributes(switchboard, settings)
    tap_values = lineup_tap_attributes(switchboard, settings)
    # A split section is drawn fine; the engineer is only told it happened (2026-10-12).
    for number, section in enumerate(sections, start=1):
        columns = plan_columns(section.contents, settings, feeder, room)
        if columns is not None and len(columns.columns) > 1:
            bus_warnings.append(
                f"NOTICE: Section {number} is too tall for the page, so its group-mounted "
                f"feeders continue in a column beside it.")

    half_bundle = settings.main_bus.phase_spacing    # B phase to A (top) or C (bottom)
    boxes = []
    for index, (section, size, plan, values, section_taps) in enumerate(
            zip(sections, sizes, plans, ct_values, tap_values)):
        if plan is None and drawn_with[index]:
            # Only parts drawn with a main in the next section (a feed crossing into it, a
            # line-side breaker tied into its feed): no main bus here. They are drawn from
            # the main's bus height.
            tops, bottoms = [], []
            for part, main_index in drawn_with[index].items():
                body_y = plans[main_index].body_y
                height = getattr(size, f"{part}_height")
                if part == "above":
                    tops.append(body_y + half_bundle + height)
                    bottoms.append(body_y + half_bundle)
                else:
                    tops.append(body_y - half_bundle)
                    bottoms.append(body_y - half_bundle - height)
            boxes.append(SectionBox(width=size.width, height=max(tops) - min(bottoms),
                                    push_to_next_page=section.push_to_next_page,
                                    link_with_next=section.link_with_next,
                                    top_y=max(tops), contents=section.contents,
                                    tap_attributes=section_taps,
                                    parts_drawn_elsewhere=set(drawn_with[index])))
            continue
        if plan is None:
            # Empty section before or after the bus: nothing to draw but its labels and
            # dividers. (Empty sections are fine; no warning.)
            boxes.append(SectionBox(width=0.0, height=0.0,
                                    push_to_next_page=section.push_to_next_page,
                                    link_with_next=section.link_with_next,
                                    contents=section.contents))
            continue
        # The section that makes the bus change height pays for the step zone in width.
        step_width = step_zone_width(settings) if plan.steps_at_entry else 0.0
        # Lowest point: its contents below the bus, or the bus itself where a tie breaker
        # steps it down as it leaves (so the title block check sees that too).
        top = plan.body_y + half_bundle + size.above_height
        bottom = min(plan.body_y - half_bundle - size.below_height, plan.exit_y - half_bundle)
        boxes.append(SectionBox(
            width=size.width + step_width,
            height=top - bottom,
            push_to_next_page=section.push_to_next_page,
            link_with_next=section.link_with_next,
            top_y=plan.body_y + half_bundle + size.above_height,
            bus=plan,
            above_height=size.above_height,
            below_height=size.below_height,
            has_tie=section.contents.tie is not None,
            contents=section.contents,
            ct_attributes=values,
            tap_attributes=section_taps,
            parts_drawn_elsewhere=set(drawn_with[index]),
        ))
    linked_ids = {link.feed.feed.id for link in links}
    for place in standalone_feeds(switchboard):
        if place.feed.id in feeds_pointed_at(switchboard) - linked_ids:
            boxes[place.section_index].feed_parts_not_drawn.add(place.part)
    # A main and its feed are kept on the same page: link them, and tell the main where
    # its feed is.
    for link in links:
        first = min(link.feed.section_index, link.main_section_index)
        boxes[first].link_with_next = True
        boxes[link.main_section_index].feed_crossings[link.main_part] = (
            link.feed.section_index, link.feed.part)
    for tie in line_side:
        boxes[min(tie.section_index, tie.feed.section_index)].link_with_next = True
        boxes[tie.feed.section_index].line_side_ties[tie.feed.part] = (tie.section_index, tie.part)
    # Interlocked mains are kept on the same page (decision 2026-10-26).
    interlocks, interlock_problems = interlock_links(switchboard)
    bus_warnings += interlock_problems
    for link in interlocks:
        boxes[link.left.section_index].link_with_next = True
        boxes[link.left.section_index].interlocks.append(link)
    result = fit_boxes(boxes, settings, catalog)
    result.warnings[:0] = bus_warnings     # bus problems first: they explain later ones
    if devices is not None and catalog is not None:
        _add_device_pages(result, switchboard, settings, devices, catalog)
    return result


def _add_device_pages(result, switchboard, settings, devices, catalog):
    """The device pages after the 3-line pages, and the 3-line blocks that point at them
    (a CT set's meter, a tap's fuse) given those pages' sheet numbers."""
    section_pages = {placed.number: page.number for page in result.pages for placed in page.placed_sections}
    devices_result = device_pages(switchboard, settings, devices, catalog, len(result.pages) + 1, section_pages)
    lookups = three_line_sheet_values(settings, devices, devices_result.sheets)
    for page in result.pages:
        for block in page.parts.blocks:
            for (block_name, name_attribute), (sheet_attribute, sheets) in lookups.items():
                device = block.attributes.get(name_attribute)
                if block.block == block_name and device in sheets:
                    block.attributes[sheet_attribute] = sheets[device]
    for page in devices_result.pages:
        result.pages.append(Page(number=page["number"], side_margin=settings.margin_standard,
                                 parts=PageParts(blocks=page["blocks"], wires=page["wires"],
                                                 placeholders=page["placeholders"], notes=page["notes"],
                                                 title=page["title"], wire_labels=page["wire_labels"])))
    result.warnings += devices_result.warnings


def _has_cts(sections) -> bool:
    for section in sections:
        contents = section.contents
        for arrangement in (contents.above, contents.below, contents.tie):
            if getattr(arrangement, "cts", None) is not None or getattr(arrangement, "base_cts", None) is not None:
                return True
    return False


def _holds_something(contents, parts_drawn_elsewhere=frozenset()) -> bool:
    """Does the section use the main bus? Parts drawn with the next section's main (a
    crossing feed, a line-side breaker) don't."""
    parts = [getattr(contents, part) for part in ("above", "below") if part not in parts_drawn_elsewhere]
    return any(arrangement is not None for arrangement in parts) or contents.tie is not None


def fit_boxes(boxes: list[SectionBox], settings: LayoutSettings, catalog=None) -> LayoutResult:
    warnings: list[str] = []
    # Sections are known by their position in the lineup ("Section 3"); they have no names.
    numbers = {id(box): n for n, box in enumerate(boxes, start=1)}
    _check_section_sizes(boxes, settings, warnings)
    groups = _group_linked_sections(boxes, numbers, warnings)

    # First decide which sections go on which page, then work out exact positions.
    sections_per_page: list[list[SectionBox]] = []
    current_page: list[SectionBox] = []

    for group in groups:
        if current_page and group[0].push_to_next_page:
            sections_per_page.append(current_page)
            current_page = []

        if _fits_on_one_page(current_page + group, settings):
            current_page = current_page + group
            continue

        # Doesn't fit after what's already on this page, so start a fresh page.
        if current_page:
            sections_per_page.append(current_page)
            current_page = []

        if _fits_on_one_page(group, settings):
            current_page = group
        else:
            # Doesn't fit even on an empty page. Give it a page of its own so nothing
            # else gets squeezed in beside it, and say why.
            warning = _explain_why_group_does_not_fit(group, numbers, settings)
            if warning:
                warnings.append(warning)
            sections_per_page.append(group)

    if current_page:
        sections_per_page.append(current_page)

    # The bus can enter a new page at any height, so the first section on a page never
    # needs to step it (2026-10-13): it drops the step and the width paid for it.
    for sections in sections_per_page[1:]:
        _enter_page_at_own_height(sections[0], settings)

    pages = []
    first_section_number = 1
    for page_number, sections in enumerate(sections_per_page, start=1):
        pages.append(_build_page(page_number, sections, settings, first_section_number))
        first_section_number += len(sections)

    add_page_parts(pages, settings, catalog, warnings)
    return LayoutResult(pages=pages, warnings=warnings)


def _enter_page_at_own_height(section, settings):
    """The bus arrives from the previous page already at this section's height (its break
    block and "FROM" label sit there), so no step, and no step zone, is needed."""
    plan = section.bus
    if plan is None or plan.starts_bus or not plan.steps_at_entry:
        return
    plan.entry_y = plan.body_y
    section.width -= step_zone_width(settings)


def _check_section_sizes(sections, settings, warnings):
    """Design errors that no page arrangement can fix."""
    widest_allowed = settings.drawable_width - 2 * settings.margin_relaxed
    tallest_allowed = settings.drawable_height - 2 * settings.margin_standard
    for number, section in enumerate(sections, start=1):
        name = f"Section {number}"
        footprint = section.width + 2 * settings.divider_clearance
        if footprint > widest_allowed + ROUNDING_TOLERANCE:
            warnings.append(
                f"{name} is wider than a page (design error): needs {footprint:g} "
                f"including divider clearance, page allows {widest_allowed:g}."
            )
        if section.height > tallest_allowed + ROUNDING_TOLERANCE:
            warnings.append(
                f"{name} is taller than a page (design error): height "
                f"{section.height:g}, page allows {tallest_allowed:g}."
            )


def _group_linked_sections(sections, numbers, warnings) -> list[list[SectionBox]]:
    """Split the section list into groups that must stay on the same page.

    A section with link_with_next=True joins the section after it. Unlinked sections
    become a group of one.
    """
    groups = []
    current_group: list[SectionBox] = []
    for section in sections:
        if current_group and section.push_to_next_page:
            # Pushing would split the group, which contradicts the link. Link wins.
            warnings.append(
                f"Section {numbers[id(section)]} is linked to Section "
                f'{numbers[id(current_group[-1])]}, so its "push to next page" is ignored.'
            )
        current_group.append(section)
        if not section.link_with_next:
            groups.append(current_group)
            current_group = []
    if current_group:  # the last section was marked "link with next" but nothing follows
        groups.append(current_group)
    return groups


def _place_sections(sections, side_margin, settings, first_number=1) -> list[PlacedSection]:
    """Position sections left to right on one page, sharing edges.

    first_number is the lineup number of the first section on this page (pages hold
    consecutive sections, since sections are never reordered).
    """
    clearance = settings.divider_clearance
    # Boxes without a bus plan (some tests) hang down from the top margin.
    default_top_y = settings.drawable_height - settings.margin_standard
    placed = []
    divider_x = side_margin
    for offset, section in enumerate(sections):
        top_y = section.top_y if section.top_y is not None else default_top_y
        right_divider_x = divider_x + clearance + section.width + clearance
        placed.append(
            PlacedSection(
                section=section,
                number=first_number + offset,
                left_divider_x=divider_x,
                right_divider_x=right_divider_x,
                component_left_x=divider_x + clearance,
                component_right_x=right_divider_x - clearance,
                component_top_y=top_y,
                component_bottom_y=top_y - section.height,
            )
        )
        divider_x = right_divider_x  # shared with the next section
    return placed


def _placement_fits(placed, side_margin, settings) -> bool:
    if not placed:
        return True
    last = placed[-1]
    right_limit = settings.drawable_width - side_margin
    # Option A (2026-10-12): if the bus carries on past the last section, always keep room
    # for its minimum run past the divider plus the break label, in case the page ends here.
    reserve = page_break_reserve(last, settings)
    if reserve and _bus_beside_title_block(last, settings):
        right_limit = min(right_limit, settings.keepout_left_x)
    if last.right_divider_x + reserve > right_limit + ROUNDING_TOLERANCE:
        return False
    return not any(_overlaps_title_block(p, settings) for p in placed)


def page_break_reserve(placed: PlacedSection, settings) -> float:
    """Room kept after a section whose bus carries on to the right (0 if it doesn't)."""
    plan = placed.section.bus
    if plan is None or plan.ends_bus:
        return 0.0
    bus = settings.main_bus
    return bus.page_break_overrun_min + bus.page_break_label_space


def _bus_beside_title_block(placed: PlacedSection, settings) -> bool:
    """The bus leaving this section is low enough to run into the title block."""
    plan = placed.section.bus
    return plan.exit_y - settings.main_bus.phase_spacing < settings.keepout_height - ROUNDING_TOLERANCE


def _overlaps_title_block(placed: PlacedSection, settings) -> bool:
    """True if the section sits over the keep-out's x-range AND reaches down into it."""
    keepout_top_y = settings.keepout_height
    is_over_keepout = placed.right_divider_x > settings.keepout_left_x + ROUNDING_TOLERANCE
    reaches_into_keepout = placed.component_bottom_y < keepout_top_y - ROUNDING_TOLERANCE
    return is_over_keepout and reaches_into_keepout


def _fits_with_margin(sections, side_margin, settings) -> bool:
    return _placement_fits(_place_sections(sections, side_margin, settings), side_margin, settings)


def _fits_on_one_page(sections, settings) -> bool:
    return _fits_with_margin(sections, settings.margin_standard, settings) or _fits_with_margin(
        sections, settings.margin_relaxed, settings
    )


def _build_page(number, sections, settings, first_section_number) -> Page:
    # Standard margin unless this page only works with the relaxed one. A page that
    # doesn't fit either way (an overflow page) keeps the standard margin.
    if _fits_with_margin(sections, settings.margin_standard, settings):
        side_margin = settings.margin_standard
    elif _fits_with_margin(sections, settings.margin_relaxed, settings):
        side_margin = settings.margin_relaxed
    else:
        side_margin = settings.margin_standard
    placed = _place_sections(sections, side_margin, settings, first_section_number)
    return Page(number=number, side_margin=side_margin, placed_sections=placed)


def _explain_why_group_does_not_fit(group, numbers, settings) -> str:
    """Warning text for a group that can't fit even on an empty page.

    Returns "" when the reason was already reported by _check_section_sizes
    (a single section wider than a page), to avoid saying the same thing twice.
    """
    names = ", ".join(str(numbers[id(section)]) for section in group)
    if len(group) > 1:
        return (
            f"Linked sections {names} do not fit together on one page; "
            f"placed on their own page anyway (overflowing)."
        )
    footprint = group[0].width + 2 * settings.divider_clearance
    if footprint > settings.drawable_width - 2 * settings.margin_relaxed + ROUNDING_TOLERANCE:
        return ""
    return f"Section {names} reaches into the title block area even alone on a page."
