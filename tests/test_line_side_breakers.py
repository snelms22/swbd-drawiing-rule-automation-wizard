"""Tests for line-side (load-bank) breakers (decision 2026-10-22, option B step 3;
src/layout/line_side_breakers.py, main_breakers.py, src/model/feeds.py).

Test numbers (tests/helpers.py): bus B at 35 when nothing is below it (A at 40); breaker 15
from the bus, poles 10; input 30 beyond the breaker. Line-side breakers: tie 10 from the main
breaker's line-side terminals, line-side breaker 15 beyond the tie, output 25 beyond it.
TEST_LUGS reaches 3 left of its CONN_A; flipped, CONN_A is 5 below its base point.
"""
from src.layout.page_fitter import fit_pages
from src.model.feeds import line_side_links
from src.model.project_file import open_project, save_project
from src.model.section_contents import (
    Breaker, IncomingFeed, LineSideBreaker, MainBreaker, PowerMeter, SectionContents, VoltageTap,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def load_bank_lineup(taps=0):
    """Like Sabey-011475: the load-bank breaker in section 1, the gen main in section 2."""
    main = MainBreaker(Breaker("52-GEN"), feed=IncomingFeed(voltage_taps=[VoltageTap("m1")] * taps))
    load_bank = LineSideBreaker(Breaker("52-LBBA"), output_attributes={"LOCATION": "TO LOAD BANK"},
                                fed_from=main.feed.id)
    return [Section(SectionContents(above=load_bank)),
            Section(SectionContents(above=main, power_meters=[PowerMeter("Janitza UMG 801", id="m1")]))]


def layout(sections):
    return fit_pages(Switchboard("Test", sections), TEST_SETTINGS, TEST_CATALOG)


def lines(page, phase):
    return [(l.start, l.end) for l in page.parts.bus_lines if l.phase == phase]


def test_the_load_bank_breaker_ties_into_the_mains_line_side():
    result = layout(load_bank_lineup())
    assert not result.warnings
    page = result.pages[0]
    assert page.placed_sections[0].section.bus is None        # section 1 carries no main bus
    # Main: line-side (top) terminals at y 65, x 55.5. The tie's nearest phase (C) is 10
    # above them; A at 85 on top. The load-bank breaker sits 3 in from section 1's content
    # edge (x 15), its line-side terminals 15 above the tie (y 100), top terminals at 110,
    # output 25 beyond (y 135).
    assert ((18, 100), (18, 85)) in lines(page, "A")
    assert ((18, 85), (55.5, 85)) in lines(page, "A")
    assert ((28, 75), (65.5, 75)) in lines(page, "C")
    assert ((18, 110), (18, 135)) in lines(page, "A")
    dots = [b.position for b in page.parts.blocks if b.block == "BUS_NODE"]
    assert dots == [(55.5, 85), (60.5, 80), (65.5, 75)]
    breaker = [b for b in page.parts.blocks if b.label == "52-LBBA"][0]
    assert breaker.position == (18, 110)
    output = [b for b in page.parts.blocks if b.block == "TEST_LUGS" and b.visibility == "OUTPUT"][0]
    assert output.position == (18, 140) and output.attributes == {"LOCATION": "TO LOAD BANK"}


def test_voltage_taps_go_beyond_the_tie():
    page = layout(load_bank_lineup(taps=1)).pages[0]
    tap = [b for b in page.parts.blocks if b.block == "TEST_TAP"][0]
    # Past the tie's top phase (85), 5 clear, then the tap's bottom (12 below its A marker).
    assert tap.position[1] == 85 + 5 + 12
    # The main's run: 10 + 10 to the tie's top, one tap (5 + 14), 5 clear = 44.
    main_input = [b for b in page.parts.blocks if b.block == "TEST_LUGS" and b.visibility == "INPUT"][0]
    assert main_input.position[1] == 65 + 44 + 5


def test_the_load_bank_and_its_main_stay_on_one_page():
    sections = load_bank_lineup()
    sections[1].push_to_next_page = True
    result = layout(sections)
    assert [[p.number for p in page.placed_sections] for page in result.pages] == [[1, 2]]


def test_load_banks_that_cannot_be_drawn_are_explained():
    standalone = IncomingFeed()
    lineup = Switchboard("Test", [
        Section(SectionContents(above=standalone)),
        Section(SectionContents(above=LineSideBreaker(Breaker("52-LB1"), fed_from=standalone.id))),
        Section(SectionContents(below=LineSideBreaker(Breaker("52-LB2")))),
    ])
    links, problems = line_side_links(lineup)
    assert links == []
    assert problems == [
        "Section 2 above (52-LB1): a line-side breaker on an incoming feed by itself is not drawn "
        "yet; pick a main breaker's own feed.",
        "Section 3 below (52-LB2): choose the feed it is fed from.",
    ]
    page = fit_pages(lineup, TEST_SETTINGS, TEST_CATALOG).pages[0]
    assert not [b for b in page.parts.blocks if b.label in ("52-LB1", "52-LB2")]


def test_line_side_breakers_are_saved(tmp_path):
    original = Switchboard("Test", load_bank_lineup(taps=1))
    assert open_project(save_project(original, tmp_path / "job.swbd")) == original
