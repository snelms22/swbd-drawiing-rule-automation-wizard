"""Tests for breaker and termination feed directions (docs/DECISIONS.md, 2026-10-13).

Test numbers (tests/helpers.py): breaker TEST_BKR has poles at x 0/5/10 of its base point,
running from y 0 down to y -10. Bus phases 5 apart; breaker 15 from the bus; input 30
beyond the breaker, input box 15. TEST_LUGS reaches 15 from its connection. U-turn to a
termination: just far enough for the termination's text (5 clear of the breaker), then 35
across and back 5. U-turns of a breaker fed on the bus side: the nearest phase goes 30
from where it starts (the next 5 and 10 further), then 35 across. Phases keep the references' rule: A
left of B on vertical runs, above it on horizontal runs. The first section's content
starts at x 15, so the block base sits at x 15.5.
Main breaker placeholder: 30 wide, 75 tall.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import (
    Breaker, MainBreaker, SectionContents, SingleBreaker, feed_directions,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def layout(*sections):
    return fit_pages(Switchboard("Test", list(sections)), TEST_SETTINGS, TEST_CATALOG)


def lines(page):
    return [(l.phase, l.start, l.end) for l in page.parts.bus_lines]


def lugs(page):
    return [b for b in page.parts.blocks if b.block == "TEST_LUGS"]


def test_empty_feed_directions_mean_the_side_away_from_the_bus():
    main = MainBreaker(Breaker("52-M"))
    assert feed_directions(main, "above") == ("top", "top")
    assert feed_directions(main, "below") == ("bottom", "bottom")


def test_bottom_fed_breaker_below_the_bus_from_a_top_termination_u_turns():
    # As in NTT-013630 section 1. Nothing above: bus B at 30 + 5 + 75 = 110, C at 105.
    # Breaker top terminals 15 below C (y 90), bottom terminals at y 80.
    # The U goes just far enough: the breaker reaches 1 past its bottom terminals, then 5
    # clearance, then the termination reaches 15 back up from its connection, then 5 out
    # of the U-turn: A (nearest) turns 26 below 80, at 54; B at 49, C at 44.
    main = MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="top")
    page = layout(Section(SectionContents(below=main))).pages[0]
    assert lines(page) == [
        ("A", (15.5, 80), (15.5, 54)), ("A", (15.5, 54), (50.5, 54)), ("A", (50.5, 54), (50.5, 59)),
        ("B", (20.5, 80), (20.5, 49)), ("B", (20.5, 49), (55.5, 49)), ("B", (55.5, 49), (55.5, 59)),
        ("C", (25.5, 80), (25.5, 44)), ("C", (25.5, 44), (60.5, 44)), ("C", (60.5, 44), (60.5, 59)),
    ]
    # 5 out of the U-turn (y 59): the termination block, fed from the top: flipped, CONN_A
    # 5 below its base point. Its top (64 + 10 = 74) is 5 below the breaker's (79).
    block, = lugs(page)
    assert block.flipped and block.position == (50.5, 64)


def test_top_fed_breaker_above_the_bus_from_a_bottom_termination_u_turns_up():
    # Bus B at 35, A at 40. Breaker bottom terminals at 55, top terminals at 65; the
    # breaker reaches 3.5 above them. Depth 3.5 + 5 + 15 + 5 = 28.5 to C (nearest, 93.5);
    # A is outermost (103.5). The legs come back down 5, to 88.5.
    main = MainBreaker(Breaker("52-M"), breaker_feed="top", termination_feed="bottom")
    page = layout(Section(SectionContents(above=main))).pages[0]
    a_lines = [line for line in lines(page) if line[0] == "A"]
    assert a_lines == [("A", (15.5, 65), (15.5, 103.5)), ("A", (15.5, 103.5), (50.5, 103.5)),
                       ("A", (50.5, 103.5), (50.5, 88.5))]
    block, = lugs(page)
    assert not block.flipped and block.position == (50.5, 83.5)   # CONN_A 5 above its base


def test_single_breaker_u_turns_too():
    single = SingleBreaker(Breaker("52-F"), breaker_feed="bottom", termination_feed="top")
    page = layout(Section(SectionContents(below=single))).pages[0]
    block, = lugs(page)
    assert block.flipped and block.visibility == "OUTPUT"
    assert len(page.parts.bus_lines) == 9


def test_u_turn_adds_its_width_to_the_section():
    straight = layout(Section(SectionContents(below=MainBreaker(Breaker("52-M")))))
    turned = layout(Section(SectionContents(
        below=MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="top"))))
    assert straight.pages[0].placed_sections[0].section.width == 30
    assert turned.pages[0].placed_sections[0].section.width == 30 + 35


def test_bus_side_fed_breaker_warns_so_it_can_be_checked():
    main = MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="bottom")
    result = layout(Section(SectionContents(above=main)))
    assert any(w.startswith("Section 1: the bottom-fed breaker above the main bus")
               for w in result.warnings)


def test_bottom_fed_above_the_bus_with_a_bottom_termination():
    # The termination block sits between the breaker and the bus: the breaker's bottom
    # terminals are 15 + 30 + 15 = 60 above A (40), at y 100; its top terminals at 110.
    main = MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="bottom")
    page = layout(Section(SectionContents(above=main))).pages[0]
    breaker, = [b for b in page.parts.blocks if b.block == "TEST_BKR"]
    assert breaker.position == (15.5, 110)
    # Cables straight down 30 to the termination, which is fed from the bottom.
    assert ("A", (15.5, 70), (15.5, 100)) in lines(page)
    block, = lugs(page)
    assert not block.flipped and block.position == (15.5, 65)
    # The bus starts at the breaker's top (B at x 20.5), U-turns over it (B 35 up) and
    # comes down 35 to the right into the main bus.
    assert page.parts.bus_paths[0][:4] == [(20.5, 110), (20.5, 145), (55.5, 145), (55.5, 35)]
    assert page.placed_sections[0].section.width == 30 + 35


def test_bottom_fed_above_the_bus_with_a_top_termination_turns_both_ways():
    # Room for the cables' U-turn below the breaker: bottom terminals 15 + 30 + 10 = 55
    # above A, at y 95; top terminals at 105. The cables turn LEFT, so the breaker moves
    # 35 right (base x 50.5).
    main = MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="top")
    page = layout(Section(SectionContents(above=main))).pages[0]
    breaker, = [b for b in page.parts.blocks if b.block == "TEST_BKR"]
    assert breaker.position == (50.5, 105)
    # Cables: down from the bottom (A nearest, 30), left 35, up past the breaker to 30
    # above its top (135).
    a_lines = [line for line in lines(page) if line[0] == "A"]
    assert a_lines == [("A", (50.5, 95), (50.5, 65)), ("A", (50.5, 65), (15.5, 65)),
                       ("A", (15.5, 65), (15.5, 135))]
    block, = lugs(page)
    assert block.flipped and block.position == (15.5, 140)
    # Bus: over the top of the breaker on the right.
    assert page.parts.bus_paths[0][:4] == [(55.5, 105), (55.5, 140), (90.5, 140), (90.5, 35)]
    assert page.placed_sections[0].section.width == 30 + 2 * 35


def test_bus_side_fed_breaker_mid_bus_tees_in_beside_it():
    first = Section(SectionContents(above=MainBreaker(Breaker("52-M1"))))
    middle = Section(SectionContents(above=SingleBreaker(
        Breaker("52-F"), breaker_feed="bottom", termination_feed="bottom")))
    last = Section(SectionContents(above=MainBreaker(Breaker("52-M2"))))
    page = layout(first, middle, last).pages[0]
    breaker, = [b for b in page.parts.blocks if b.label == "52-F"]
    riser_xs = {breaker.position[0] + 35 + dx for dx in (0, 5, 10)}
    dot_xs = {b.position[0] for b in page.parts.blocks if b.block == "BUS_NODE"}
    assert riser_xs <= dot_xs


def test_u_turn_goes_further_for_a_termination_with_more_lines_of_text():
    # Two line breaks in the termination's text: 2 x 1.25 x 1.6 = 4 more, so A turns at
    # 54 - 4 = 50 and the termination sits 5 above that (55) instead of at 59.
    main = MainBreaker(Breaker("52-M"), breaker_feed="bottom", termination_feed="top",
                       input_attributes={"TERMINATION": "LUGS\n(4) 500 KCMIL\nPER PHASE"})
    page = layout(Section(SectionContents(below=main))).pages[0]
    assert ("A", (15.5, 80), (15.5, 50)) in lines(page)
    block, = lugs(page)
    assert block.position == (50.5, 60)
