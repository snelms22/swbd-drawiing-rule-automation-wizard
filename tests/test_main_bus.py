"""Tests for the main bus height rule (docs/DECISIONS.md, "Main bus height").

Test numbers (tests/helpers.py): content between y 30 and 280, phases 5 apart (so the bus
B phase is 5 above the lowest content when nothing is below it), step adds 10 width,
a tie moves the bus 70. Placeholders: main 75 tall, single breaker 45 tall.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, TieBreaker,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_SETTINGS


def section(above=None, below=None, tie=None):
    return Section(SectionContents(above=above, below=below, tie=tie))


def main():
    return MainBreaker(Breaker("52-M"))


def single():
    return SingleBreaker(Breaker("52-F"))


def group(levels):
    # gap 15 + (levels - 1) x 25 + level 10 + overhang 10
    return GroupMounted([SingleLevel(Breaker(f"52-F{n}")) for n in range(levels)])


def bus_plans(*sections):
    result = fit_pages(Switchboard("Test", list(sections)), TEST_SETTINGS)
    boxes = [p.section for page in result.pages for p in page.placed_sections]
    return [box.bus for box in boxes], boxes, result.warnings


def test_bus_starts_as_low_as_possible():
    plans, _, _ = bus_plans(section(above=main()))
    assert plans[0].body_y == 30 + 5           # nothing below: C phase sits on y 30


def test_part_below_pushes_the_bus_up():
    plans, _, _ = bus_plans(section(above=main(), below=single()))
    assert plans[0].body_y == 30 + 45 + 5


def test_bus_stays_level_when_it_can():
    # Section 2 has nothing below; the bus does not drop back down for it.
    plans, boxes, _ = bus_plans(section(below=single()), section(above=main()))
    assert plans[0].body_y == plans[1].body_y == 80
    assert not plans[1].steps_at_entry
    assert boxes[1].width == 30                 # no step, no extra width


def test_bigger_part_below_moves_the_bus_up_and_that_section_takes_the_step():
    # Section 2's group (5 levels: 15 + 4x25 + 10 + 10 = 135 tall) needs the bus higher.
    plans, boxes, _ = bus_plans(section(above=main()), section(below=group(5)))
    assert plans[0].body_y == 35
    assert plans[1].body_y == 30 + 135 + 5
    assert plans[1].steps_at_entry
    assert boxes[1].width == 145 + 20           # group width + step zone (bus 10 + clearance 10)


def test_tall_part_above_pushes_the_bus_down_only_as_far_as_needed():
    # Section 1 lifts the bus to 170 (group of 5 below). Section 2 has a group of 8 above
    # (15 + 7x25 + 10 + 10 = 210), so the bus can be at most 280 - 5 - 210 = 65.
    plans, _, _ = bus_plans(section(below=group(5)), section(above=group(8)))
    assert plans[0].body_y == 170
    assert plans[1].body_y == 65
    assert plans[1].steps_at_entry


def test_tie_breaker_moves_the_bus_as_it_leaves_its_section():
    plans, _, _ = bus_plans(
        section(above=main(), tie=TieBreaker(Breaker("52-T"), bus_steps="up")),
        section(above=single()),
    )
    assert (plans[0].body_y, plans[0].exit_y) == (35, 105)
    assert plans[1].entry_y == plans[1].body_y == 105   # next section just carries on


def test_section_too_tall_for_the_page_is_split_not_warned():
    # Room between y 30 and 280, less the bus (10) = 240. Groups of 7 above (185) and 2
    # below (60) need 245. The part below is split (see test_section_builder.py), so the
    # bus fits: as low as the split part below allows (30 + 5 + 45 for its continuation).
    plans, _, warnings = bus_plans(section(above=group(7), below=group(2)))
    assert not any(w.startswith("Section 1 is too tall") for w in warnings)
    assert any(w.startswith("NOTICE: Section 1 is too tall") for w in warnings)
    assert plans[0].body_y == 80


def test_bus_path_steps_inside_the_section_that_needs_it():
    # Section 1 (main above, 30 wide) spans 10-50; its content starts at 15. Section 2
    # (group of 5 below, 145 + 20 step zone) spans 50-225. Its bus run is at 55-65 (centre
    # 60), then 10 clear, so its content starts at 75. The bus ends at section 2's content
    # edge (220), the last section using it.
    result = fit_pages(Switchboard("Test", [section(above=main()), section(below=group(5))]),
                       TEST_SETTINGS)
    assert result.pages[0].parts.bus_paths == [[
        (15, 35), (50, 35),     # starts in section 1, level
        (60, 35), (60, 170),    # rises in section 2's step zone
        (220, 170),             # on through section 2, ends there
    ]]
    boxes = result.pages[0].parts.content_boxes
    section_2 = [b for b in boxes if b.section_number == 2][0]
    assert section_2.left_x - (60 + 5) == 10      # vertical run's C phase is 10 clear


def test_no_bus_in_empty_sections_before_or_after():
    result = fit_pages(Switchboard("Test", [Section(), section(above=single()), Section()]),
                       TEST_SETTINGS)
    boxes = [p.section for p in result.pages[0].placed_sections]
    assert [b.bus is None for b in boxes] == [True, False, True]
    path = result.pages[0].parts.bus_paths[0]
    section_2 = result.pages[0].placed_sections[1]
    assert path[0][0] == section_2.component_left_x      # starts in section 2
    assert path[-1][0] == section_2.component_right_x    # and ends there
    assert result.warnings == []                        # empty sections are fine


def test_bus_runs_through_an_empty_section_in_the_middle():
    result = fit_pages(Switchboard("Test", [section(above=single()), Section(), section(above=single())]),
                       TEST_SETTINGS)
    boxes = [p.section for p in result.pages[0].placed_sections]
    assert all(b.bus is not None for b in boxes)
    assert len(result.pages[0].parts.bus_paths) == 1


def test_tie_stepping_down_raises_the_sections_before_it():
    # Section 2's tie steps down 70: the bus must be at least 35 + 70 = 105 there. Section 1
    # can sit that high (nothing tall above it), so the bus starts at 105 and runs level.
    plans, _, warnings = bus_plans(
        section(above=main()),
        section(above=single(), tie=TieBreaker(Breaker("52-T"), bus_steps="down")),
    )
    assert plans[0].body_y == 105 and plans[1].body_y == 105
    assert not plans[1].steps_at_entry
    assert plans[1].exit_y == 35
    assert warnings == []


def test_tie_wraps_up_when_the_sections_before_cannot_be_raised():
    # Section 1 has a tall group above (210), so its bus can't go above 280 - 5 - 210 = 65.
    # The bus steps up in section 2 (the wrap) to 105, then the tie steps it down to 35.
    plans, boxes, warnings = bus_plans(
        section(above=group(8)),
        section(above=single(), tie=TieBreaker(Breaker("52-T"), bus_steps="down")),
    )
    assert plans[0].body_y == 35
    assert plans[1].steps_at_entry and plans[1].body_y == 105 and plans[1].exit_y == 35
    assert warnings == []


def test_tie_with_no_room_warns_without_suggesting_the_other_direction():
    # The tie section itself has a tall group above, so the bus can't reach 105 there.
    plans, _, warnings = bus_plans(
        section(above=group(8), tie=TieBreaker(Breaker("52-T"), bus_steps="down")),
    )
    assert any("isn't room above the main bus for the tie breaker" in w for w in warnings)
    assert not any("Try" in w for w in warnings)


def test_tie_stepping_up_lowers_the_sections_before_it():
    # A tie stepping up 70 needs the bus at most 275 - 70 = 205 in its section. Section 1's
    # tall group below holds its bus at 270, so it can't be lowered; the bus steps down in
    # section 2 instead, then the tie steps it back up.
    plans, _, warnings = bus_plans(
        section(below=group(9)),          # lifts the bus to 30 + 235 + 5 = 270
        section(below=single(), tie=TieBreaker(Breaker("52-T"), bus_steps="up")),
    )
    assert plans[1].body_y <= 205
    assert plans[1].steps_at_entry          # section 1 can't go that low, so it steps down here



def test_bus_lowered_by_a_tie_counts_as_part_of_the_section():
    # The section's lowest point includes the bus after its tie steps down, so the title
    # block check (and the page fitting) sees it.
    tie_section = section(above=single(), tie=TieBreaker(Breaker("52-T"), bus_steps="down"))
    result = fit_pages(Switchboard("Test", [section(below=group(5)), tie_section]), TEST_SETTINGS)
    placed = result.pages[0].placed_sections[1]
    assert placed.component_bottom_y == placed.section.bus.exit_y - 5



# --- Page breaks (decision 2026-10-12 "Bus at a page break") --------------------------

import dataclasses


def with_page_break_room(minimum=10.0, label=15.0, maximum=30.0):
    bus = dataclasses.replace(TEST_SETTINGS.main_bus, page_break_overrun_min=minimum,
                              page_break_label_space=label, page_break_overrun_max=maximum)
    return dataclasses.replace(TEST_SETTINGS, main_bus=bus)


def test_bus_runs_30_past_the_divider_at_a_page_break_when_there_is_room():
    # Two groups of 145 (footprint 155 each): section 2 can't join section 1 on the page.
    settings = with_page_break_room()
    board = Switchboard("Test", [section(above=group(1)), section(above=group(9)), section(above=group(1))])
    result = fit_pages(board, settings)
    page1 = result.pages[0]
    last = page1.placed_sections[-1]
    path = page1.parts.bus_paths[-1]
    assert path[-1][0] == last.right_divider_x + 30
    label = [p for p in page1.parts.placeholders if p.text == "TO NEXT PAGE"][0]
    assert label.left_x == path[-1][0] and label.right_x - label.left_x == 15


def test_bus_overrun_is_limited_by_the_room_left_on_the_page():
    # A huge maximum: the run stops where the room ends. Page 1 holds sections 1-2 (to
    # x 320); the bus is beside the title block (low), so room ends at its left edge
    # (400), minus the 15 label space.
    settings = with_page_break_room(maximum=1000.0)
    board = Switchboard("Test", [section(above=group(1)), section(above=group(9)), section(above=group(1))])
    page1 = fit_pages(board, settings).pages[0]
    last = page1.placed_sections[-1]
    end_x = page1.parts.bus_paths[-1][-1][0]
    assert end_x == 400 - 15
    assert end_x - last.right_divider_x >= 10


def test_page_keeps_room_for_the_minimum_overrun_and_label():
    # No title block here, so only the width matters. Three sections of footprint 155
    # (465) fit in 480 without a reserve. With 10 + 20 kept free after the last one (its
    # bus carries on), 465 + 30 is too wide even with relaxed margins (490), so the third
    # moves to page 2.
    def no_title_block(settings):
        return dataclasses.replace(settings, keepout_width=0.0, keepout_height=0.0)
    board = Switchboard("Test", [section(above=group(1)) for _ in range(4)])
    no_reserve = fit_pages(board, no_title_block(TEST_SETTINGS))
    reserved = fit_pages(board, no_title_block(with_page_break_room(label=20.0)))
    assert len(no_reserve.pages[0].placed_sections) == 3
    assert len(reserved.pages[0].placed_sections) == 2


def test_bus_starts_right_away_at_the_left_margin_on_the_next_page():
    settings = with_page_break_room()
    board = Switchboard("Test", [section(above=group(1)), section(above=group(9)), section(above=group(1))])
    page2 = fit_pages(board, settings).pages[1]
    assert page2.parts.bus_paths[0][0][0] == page2.placed_sections[0].left_divider_x



def test_page_break_gets_tilde_and_labelled_brackets_on_both_pages():
    from tests.helpers import TEST_CATALOG
    settings = with_page_break_room()
    # A one-level feeder group is only 33 wide (one side), so nine of them need two pages.
    board = Switchboard("Test", [section(above=group(1)) for _ in range(9)])
    page1, page2 = fit_pages(board, settings, TEST_CATALOG).pages
    end_x, end_y = page1.parts.bus_paths[-1][-1]
    tilde1 = [b for b in page1.parts.blocks if b.block == "TEST_TILDE"][0]
    bracket1 = [b for b in page1.parts.blocks if b.block == "TEST_BRACKET"][0]
    assert tilde1.position == (end_x, end_y + 5)             # on the A-phase end
    assert bracket1.position == (end_x + 2.0, end_y)          # just past it, on B
    assert bracket1.attributes == {"VERTICAL_LABLE": "TO ES_02"} and not bracket1.flipped
    start_x, start_y = page2.parts.bus_paths[0][0]
    bracket2 = [b for b in page2.parts.blocks if b.block == "TEST_BRACKET"][0]
    assert start_x == page2.placed_sections[0].component_left_x
    assert bracket2.position == (start_x - 2.0, start_y)
    assert bracket2.attributes == {"VERTICAL_LABLE": "FROM ES_01"} and bracket2.flipped
    assert not [p for p in page1.parts.placeholders if p.text == "TO NEXT PAGE"]
    # The tilde faces the way the bus goes: as is where it leaves; mirrored where it
    # arrives, with only its left-right flip, so its letters sit on the incoming side.
    tilde2 = [b for b in page2.parts.blocks if b.block == "TEST_TILDE"][0]
    assert not tilde1.flipped
    assert tilde2.flipped and tilde2.flip_parameter == "Flip state1"
    assert tilde2.position == (start_x, start_y + 5)


def test_sections_are_not_raised_when_a_later_section_already_lifts_the_bus_enough():
    # Section 2's group below (135) lifts the bus to 170 on its own, more than the tie in
    # section 3 needs (105). So section 1 stays low; nothing is raised for the tie.
    plans, _, _ = bus_plans(
        section(above=main()),
        section(below=group(5)),
        section(above=single(), tie=TieBreaker(Breaker("52-T"), bus_steps="down")),
    )
    assert plans[0].body_y == 35
    assert plans[1].body_y == 170 and plans[2].exit_y == 100


def test_bus_enters_a_new_page_at_the_height_it_needs_without_a_step():
    # Sections 1-2 (group of 1 above, 145 wide) fill page 1 (a third would sit over the
    # title block) with the bus at 35. Section 3 (group of 5 below) needs the bus at 170
    # and starts page 2: the bus arrives there at 170 (2026-10-13), so section 3 has no
    # step and no step zone (145 wide, not 165).
    sections = [section(above=group(1)) for _ in range(2)] + [section(below=group(5))]
    result = fit_pages(Switchboard("Test", sections), TEST_SETTINGS)
    assert [len(page.placed_sections) for page in result.pages] == [2, 1]
    first_on_page_2 = result.pages[1].placed_sections[0].section
    assert first_on_page_2.bus.entry_y == first_on_page_2.bus.body_y == 170
    assert first_on_page_2.width == 145
    # Page 1's bus leaves at its own height (35).
    assert result.pages[0].placed_sections[-1].section.bus.exit_y == 35
