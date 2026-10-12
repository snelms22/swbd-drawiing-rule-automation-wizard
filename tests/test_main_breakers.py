"""Tests for drawing main breakers with their bus (docs/DECISIONS.md, 2026-10-11).

Test numbers (tests/helpers.py): breaker TEST_BKR has poles at x 0/5/10 of its base point,
running from y 0 down to y -10; extents left edge -0.5. Bus phases 5 apart; breaker 15
from the bus; input 30 beyond the breaker; input box 15. Section clearance 5, margin 10,
so the first section's content starts at x 15 and the block base sits at x 15.5.
Main breaker placeholder size: 30 wide, 75 tall.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import Breaker, MainBreaker, SectionContents, SingleBreaker
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def layout(*sections):
    return fit_pages(Switchboard("Test", list(sections)), TEST_SETTINGS, TEST_CATALOG)


def top_fed(label="52-M1"):
    return Section(SectionContents(above=MainBreaker(Breaker(label))))


def bottom_fed(label="52-M2"):
    return Section(SectionContents(below=MainBreaker(Breaker(label))))


def test_top_fed_main_at_lineup_start_bends_into_the_bus():
    page = layout(top_fed()).pages[0]
    # Nothing below: bus B at 35 (lowest), A at 40. Breaker bottom terminals 15 above A
    # (y 55), so its base point (top terminals) is at y 65. Block base x = 15.5.
    breaker = [b for b in page.parts.blocks if b.block == "TEST_BKR"][0]
    assert breaker.position == (15.5, 65)
    assert breaker.attributes == {"BREAKER_NAME": "52-M1"}
    assert breaker.visibility == "1 BOM"
    # The main bus starts at the breaker's B terminal and bends into the bus: no dots.
    assert page.parts.bus_path[:2] == [(20.5, 55), (20.5, 35)]
    assert not [b for b in page.parts.blocks if b.block == "BUS_NODE"]


def test_input_side_runs_from_the_input_end_to_the_breaker():
    page = layout(top_fed()).pages[0]
    # Breaker top terminals at y 65; input end 30 higher, at y 95.
    assert [(l.phase, l.start, l.end) for l in page.parts.bus_lines] == [
        ("A", (15.5, 95), (15.5, 65)),
        ("B", (20.5, 95), (20.5, 65)),
        ("C", (25.5, 95), (25.5, 65)),
    ]
    box = page.parts.placeholders[0]
    assert (box.text, box.bottom_y, box.top_y) == ("INPUT", 95, 110)


def test_bottom_fed_main_mid_bus_tees_in_with_junction_dots():
    # Section 1 (top-fed main) starts the bus; section 2's main is fed from below and
    # joins the running bus.
    result = layout(top_fed(), bottom_fed())
    page = result.pages[0]
    dots = sorted(b.position for b in page.parts.blocks if b.block == "BUS_NODE")
    # Section 1 leaves the bus at B = 35. Section 2 needs 75 below it, so the bus rises
    # (in section 2) to B = 30 + 75 + 5 = 110.
    bus_b = page.placed_sections[1].section.bus.body_y
    assert bus_b == 110
    # Each phase tees into its own bus line: A at 115, B at 110, C at 105.
    xs = [x for x, _ in dots]
    assert [y for _, y in dots] == [115, 110, 105]
    assert xs[1] - xs[0] == 5 and xs[2] - xs[1] == 5


def test_drawn_main_breakers_have_no_placeholder_box():
    page = layout(top_fed()).pages[0]
    assert page.parts.content_boxes == []


def test_other_parts_still_get_placeholder_boxes():
    section = Section(SectionContents(above=MainBreaker(Breaker("52-M1")),
                                      below=SingleBreaker(Breaker("52-F1"))))
    page = layout(section).pages[0]
    assert [(c.section_number, c.part) for c in page.parts.content_boxes] == [(1, "below")]


def test_without_a_catalog_main_breakers_stay_placeholders():
    board = Switchboard("Test", [top_fed()])
    page = fit_pages(board, TEST_SETTINGS).pages[0]
    assert page.parts.blocks == []
    assert len(page.parts.content_boxes) == 1
