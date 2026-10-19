"""Tests for group-mounted feeders on a vertical bus (src/layout/feeders.py).

Test numbers (tests/helpers.py): feeder block TEST_FEEDER has its connections at x 0
(A 10, B 5, C 0 above its base point) and reaches 23 out from them, mirrored for the right
side. Taps: the nearest phase's tap is 10. Group spacing: gap 15, pitch 25, level 10,
overhang 10. Bus phases 5 apart. Section clearance 5, margin 10: the first section's
content starts at x 15.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, Provision, SingleLevel, Space, TwinLevel,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def layout(*sections):
    return fit_pages(Switchboard("Test", list(sections)), TEST_SETTINGS, TEST_CATALOG)


def main_section():
    return Section(SectionContents(above=MainBreaker(Breaker("52-M"))))


def group_section(above=None, below=None):
    return Section(SectionContents(above=above, below=below))


def twin(left="52-L", right="52-R"):
    return TwinLevel(Breaker(left), Breaker(right))


def feeders(page, label):
    return [b for b in page.parts.blocks if b.block == "TEST_FEEDER" and b.label == label]


def dots(page):
    return {b.position for b in page.parts.blocks if b.block == "BUS_NODE"}


def middle_section_layout(above=None, below=None):
    """Main, group, main: the group sits where the main bus is already running."""
    result = layout(main_section(), group_section(above, below), main_section())
    page = result.pages[0]
    return page, page.placed_sections[1]


def test_twin_level_breakers_tap_their_own_phases():
    page, placed = middle_section_layout(above=GroupMounted([twin()]))
    left, = feeders(page, "52-L")
    right, = feeders(page, "52-R")
    assert not left.flipped and right.flipped
    assert left.attributes == {"DEVICE_ID": "52-L"} and left.visibility == "3 PHASE-3 WIRE"
    # Left breaker reaches 23 from the content edge; A is 10 further on.
    a_x = placed.component_left_x + 23 + 10
    conn_left = left.position[0]
    conn_right = right.position[0]
    assert conn_left == a_x - 10 and conn_right == a_x + 10 + 10
    a_lines = [l for l in page.parts.bus_lines if l.phase == "A" and l.start[1] == left.position[1] + 10]
    assert sorted(l.start[0] for l in a_lines) == [conn_left, conn_right]
    assert {l.end[0] for l in a_lines} == {a_x}                 # both end on the A phase


def test_nearest_tap_is_10_long_on_each_side():
    page, placed = middle_section_layout(above=GroupMounted([twin()]))
    left, = feeders(page, "52-L")
    right, = feeders(page, "52-R")
    base_y = left.position[1]
    lengths = {(l.phase, l.start[0]): abs(l.end[0] - l.start[0]) for l in page.parts.bus_lines
               if l.start[1] == l.end[1] and base_y <= l.start[1] <= base_y + 10}
    assert lengths[("A", left.position[0])] == 10 and lengths[("C", left.position[0])] == 20
    assert lengths[("C", right.position[0])] == 10 and lengths[("A", right.position[0])] == 20


def test_levels_above_start_15_over_the_bus_and_are_25_apart():
    group = GroupMounted([SingleLevel(Breaker("52-F1")), SingleLevel(Breaker("52-F2"))])
    page, placed = middle_section_layout(above=group)
    main_a = placed.section.bus.body_y + 5
    first, = feeders(page, "52-F1")
    second, = feeders(page, "52-F2")
    assert first.position[1] == main_a + 15                     # its C tap (base point)
    assert second.position[1] == first.position[1] + 25
    assert not first.flipped and second.flipped                 # single levels alternate


def test_levels_below_start_15_under_the_bus_with_a_on_top():
    page, placed = middle_section_layout(below=GroupMounted([twin()]))
    main_c = placed.section.bus.body_y - 5
    left, = feeders(page, "52-L")
    assert left.position[1] + 10 == main_c - 15                 # its A tap


def test_vertical_bus_tees_into_a_running_main_bus_with_dots():
    page, placed = middle_section_layout(above=GroupMounted([twin()]))
    body = placed.section.bus.body_y
    a_x = placed.component_left_x + 33
    left, = feeders(page, "52-L")
    top = left.position[1] + 10 + 10                            # top A tap + overhang
    for phase, dx, y in (("A", 0, body + 5), ("B", 5, body), ("C", 10, body - 5)):
        assert (a_x + dx, y) in dots(page)
        vertical = [l for l in page.parts.bus_lines if l.phase == phase and l.start == (a_x + dx, y)]
        assert vertical[0].end == (a_x + dx, top)


def test_vertical_bus_starting_the_main_bus_bends_into_it():
    page = layout(group_section(above=GroupMounted([twin()])), main_section()).pages[0]
    placed = page.placed_sections[0]
    body = placed.section.bus.body_y
    b_x = placed.component_left_x + 33 + 5
    left, = feeders(page, "52-L")
    top = left.position[1] + 20
    assert page.parts.bus_paths[0][:2] == [(b_x, top), (b_x, body)]
    assert (b_x, body) not in dots(page)                        # a bend, not a tee


def test_one_dot_per_phase_where_twin_taps_meet():
    page, placed = middle_section_layout(above=GroupMounted([twin()]))
    a_x = placed.component_left_x + 33
    left, = feeders(page, "52-L")
    tap_dots = [d for d in dots(page) if left.position[1] <= d[1] <= left.position[1] + 10]
    assert sorted(tap_dots) == [(a_x, left.position[1] + 10), (a_x + 5, left.position[1] + 5),
                                (a_x + 10, left.position[1])]


def test_width_counts_only_the_sides_in_use():
    _, one_side = middle_section_layout(above=GroupMounted([SingleLevel(Breaker("52-F1"))]))
    _, two_sides = middle_section_layout(above=GroupMounted([twin()]))
    assert one_side.section.width == 23 + 10 + 10               # breaker, tap, A to C
    assert two_sides.section.width == 23 + 10 + 10 + 10 + 23


def test_a_provision_is_tapped_out_and_ends_with_its_note():
    group = GroupMounted([TwinLevel(Breaker("52-L"), Provision("3VA62 250AF"))])
    page, placed = middle_section_layout(above=group)
    left, = feeders(page, "52-L")
    a_x = placed.component_left_x + 33
    end_x = a_x + 10 + 10                                       # where a breaker would connect
    a_y = left.position[1] + 10
    taps = sorted((l.phase, l.start, l.end) for l in page.parts.bus_lines
                  if l.start[0] == end_x)
    assert taps == [("A", (end_x, a_y), (a_x, a_y)),
                    ("B", (end_x, a_y - 5), (a_x + 5, a_y - 5)),
                    ("C", (end_x, a_y - 10), (a_x + 10, a_y - 10))]
    note, = page.parts.notes
    assert note.lines == ["PROVISION FOR", "3VA62 250AF"]
    assert (note.x, note.middle_y, note.align) == (end_x + 10, a_y - 5, "middle_left")
    assert not [b for b in page.parts.blocks if b.block == "TEST_FEEDER" and b.flipped]


def test_a_space_is_tapped_out_like_a_provision_and_labelled_space():
    # Decision 2026-10-19: solid bus taps to where a breaker would connect, then "SPACE".
    group = GroupMounted([TwinLevel(Breaker("52-L"), Space())])
    page, placed = middle_section_layout(above=group)
    a_x = placed.component_left_x + 33
    end_x = a_x + 10 + 10
    assert len([l for l in page.parts.bus_lines if l.start[0] == end_x]) == 3
    note, = page.parts.notes
    assert note.lines == ["SPACE"]
    assert (note.x, note.align) == (end_x + 10, "middle_left")


def test_a_space_works_on_a_single_level_too():
    page, placed = middle_section_layout(above=GroupMounted([SingleLevel(Space())]))
    note, = page.parts.notes
    assert note.lines == ["SPACE"] and note.align == "middle_right"


def test_a_provision_on_the_left_runs_its_note_leftward():
    group = GroupMounted([SingleLevel(Provision())])
    page, placed = middle_section_layout(above=group)
    note, = page.parts.notes
    assert note.lines == ["PROVISION"]                          # no info given
    assert note.align == "middle_right"
    # The section is wide enough for the note: gap 10 + estimated text width.
    estimated = len("PROVISION") * 1.25 * 0.8                  # test text settings
    assert placed.section.width == 10 + estimated + 10 + 10
