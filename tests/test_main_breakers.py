"""Tests for drawing main breakers with their bus (docs/DECISIONS.md, 2026-10-11).

Test numbers (tests/helpers.py): breaker TEST_BKR has poles at x 0/5/10 of its base point,
running from y 0 down to y -10; extents left edge -0.5. Bus phases 5 apart; breaker 15
from the bus; input 30 beyond the breaker; input box 15. Section clearance 5, margin 10,
so the first section's content starts at x 15 and the block base sits at x 15.5.
Main breaker placeholder size: 30 wide, 75 tall.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import Breaker, IncomingFeed, MainBreaker, SectionContents, SingleBreaker
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
    assert page.parts.bus_paths[0][:2] == [(20.5, 55), (20.5, 35)]
    assert not [b for b in page.parts.blocks if b.block == "BUS_NODE"]


def test_input_side_runs_from_the_input_end_to_the_breaker():
    page = layout(top_fed()).pages[0]
    # Breaker top terminals at y 65; input end 30 higher, at y 95.
    assert [(l.phase, l.start, l.end) for l in page.parts.bus_lines] == [
        ("A", (15.5, 95), (15.5, 65)),
        ("B", (20.5, 95), (20.5, 65)),
        ("C", (25.5, 95), (25.5, 65)),
    ]


def test_top_fed_input_block_is_flipped_with_conn_a_on_the_bus_end():
    page = layout(top_fed()).pages[0]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"][0]
    # The A-phase bus ends at (15.5, 95). Flipped, CONN_A is 5 below the base point,
    # so the base point goes at (15.5, 100).
    assert lugs.flipped
    assert lugs.position == (15.5, 100)
    assert lugs.visibility == "INPUT"
    assert page.parts.placeholders == []


def test_bottom_fed_input_block_is_not_flipped():
    page = layout(top_fed(), bottom_fed()).pages[0]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"]
    bottom = [b for b in lugs if not b.flipped][0]
    a_end_y = min(line.start[1] for line in page.parts.bus_lines if line.phase == "A")
    # Not flipped, CONN_A is 5 above the base point.
    assert bottom.position[1] == a_end_y - 5


def test_input_placeholder_when_the_input_block_is_not_catalogued():
    catalog = {name: info for name, info in TEST_CATALOG.items() if name != "TEST_LUGS"}
    board = Switchboard("Test", [top_fed()])
    page = fit_pages(board, TEST_SETTINGS, catalog).pages[0]
    box = page.parts.placeholders[0]
    assert (box.text, box.bottom_y, box.top_y) == ("INPUT", 95, 110)


def test_bottom_fed_main_mid_bus_tees_in_with_junction_dots():
    # Section 1 (top-fed main) starts the bus; section 2's main is fed from below and
    # joins the running bus; section 3 keeps the bus going past it.
    result = layout(top_fed(), bottom_fed(),
                    Section(SectionContents(above=SingleBreaker(Breaker("52-F1")))))
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


def test_single_breaker_feeder_is_drawn_like_a_main_with_an_output_block():
    section = Section(SectionContents(above=MainBreaker(Breaker("52-M1")),
                                      below=SingleBreaker(Breaker("52-F1"))))
    page = layout(section).pages[0]
    assert page.parts.content_boxes == []
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"]
    assert [(b.visibility, b.flipped) for b in lugs] == [("INPUT", True), ("OUTPUT", False)]
    feeder = [b for b in page.parts.blocks if b.label == "52-F1"]
    assert [b.block for b in feeder] == ["TEST_BKR"]


def test_without_a_catalog_main_breakers_stay_placeholders():
    board = Switchboard("Test", [top_fed()])
    page = fit_pages(board, TEST_SETTINGS).pages[0]
    assert page.parts.blocks == []
    assert len(page.parts.content_boxes) == 1


def test_draw_out_main_uses_the_draw_out_block():
    section = Section(SectionContents(above=MainBreaker(Breaker("52-M1"), mounting="draw-out")))
    blocks = [b.block for b in layout(section).pages[0].parts.blocks if b.block != "TEST_LUGS"]
    assert blocks == ["TEST_BKR_DO"]


def test_fixed_is_the_default_mounting():
    blocks = [b.block for b in layout(top_fed()).pages[0].parts.blocks if b.block != "TEST_LUGS"]
    assert blocks == ["TEST_BKR"]


def test_attribute_values_go_to_the_blocks_and_empty_ones_keep_the_default():
    main = MainBreaker(Breaker("52-M1", attributes={"SIZE/POLLS": "2000AF/1600AT,3P", "ETU/DAS": ""}),
                       feed=IncomingFeed(input_attributes={"LOCATION": "FROM UTILITY", "TERMINATION": ""}))
    page = layout(Section(SectionContents(above=main))).pages[0]
    breaker = [b for b in page.parts.blocks if b.block == "TEST_BKR"][0]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"][0]
    assert breaker.attributes == {"SIZE/POLLS": "2000AF/1600AT,3P", "BREAKER_NAME": "52-M1"}
    assert lugs.attributes == {"LOCATION": "FROM UTILITY"}


def test_main_breaker_in_the_last_section_bends_out_of_the_bus():
    # Section 2's bottom-fed main is the last thing on the bus: the bus bends down into it
    # instead of teeing in with dots.
    page = layout(top_fed(), bottom_fed()).pages[0]
    assert not [b for b in page.parts.blocks if b.block == "BUS_NODE"]
    path = page.parts.bus_paths[0]
    assert path[-1][1] < path[-2][1]            # last segment goes down into the breaker


def test_tie_breaker_uses_the_breaker_block_and_splits_the_bus():
    from src.model.section_contents import TieBreaker
    tie_section = Section(SectionContents(above=MainBreaker(Breaker("52-M1")),
                                          tie=TieBreaker(Breaker("52-T1"), bus_steps="up")))
    after = Section(SectionContents(above=SingleBreaker(Breaker("52-F1"))))
    page = layout(tie_section, after).pages[0]
    ties = [b for b in page.parts.blocks if b.label == "52-T1"]
    assert len(ties) == 1 and ties[0].block == "TEST_BKR"
    assert ties[0].attributes["BREAKER_NAME"] == "52-T1"
    # Bus: up to the breaker's bottom terminals, then on from its top terminals.
    first, second = page.parts.bus_paths
    # Tie: bus B at 35, steps up 70 to 105; breaker centred at 70, terminals at 65 and 75.
    assert first[-1][1] == 65 and second[0][1] == 75
    assert ties[0].position[1] == 75             # base point on the top terminals
