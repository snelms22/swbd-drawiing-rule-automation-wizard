"""Tests for incoming feeds standing on their own (decision 2026-10-22, option B step 2;
src/model/feeds.py, src/layout/incoming_feeds.py, main_breakers.py).

Test numbers (tests/helpers.py): bus B at 35 when nothing is below it (A at 40); breaker 15
from the bus, poles 10 long; input 30 beyond the breaker; input box 15. Margin 10, section
clearance 5. TEST_LUGS reaches 3 left of its CONN_A; flipped, CONN_A is 5 below its base.
"""
from src.layout.page_fitter import fit_pages
from src.model.feeds import feed_links
from src.model.project_file import open_project, save_project
from src.model.section_contents import (
    Breaker, IncomingFeed, MainBreaker, PowerMeter, SectionContents, VoltageTap,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def layout(*contents):
    return fit_pages(Switchboard("Test", [Section(c) for c in contents]), TEST_SETTINGS, TEST_CATALOG)


def lines(page, phase):
    return [(l.start, l.end) for l in page.parts.bus_lines if l.phase == phase]


def crossing_lineup():
    feed = IncomingFeed(input_attributes={"LOCATION": "FROM UTILITY"})
    main = MainBreaker(Breaker("52-M1"), feed=None, feed_from=feed.id)
    return SectionContents(above=feed), SectionContents(above=main)


def test_a_feed_alone_is_main_lugs_only():
    page = layout(SectionContents(above=IncomingFeed())).pages[0]
    # The riser runs 15 + 30 = 45 from the bus's top phase (A, y 40) to the termination,
    # 3 in from the content edge (x 15) so the termination block clears it.
    assert page.parts.bus_start_path == [(23, 85), (23, 35)]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"][0]
    assert lugs.position == (18, 90) and lugs.flipped
    assert not [b for b in page.parts.blocks if b.block == "TEST_BKR"]


def test_main_lugs_taps_sit_nearest_the_bus():
    feed = IncomingFeed(voltage_taps=[VoltageTap("m1")])
    contents = SectionContents(above=feed, power_meters=[PowerMeter("Janitza UMG 801", id="m1")])
    page = layout(contents).pages[0]
    tap = [b for b in page.parts.blocks if b.block == "TEST_TAP"][0]
    # 5 clear of the bus (A at 40), then the tap's bottom, 12 below its A marker.
    assert tap.position[1] == 40 + 5 + 12
    assert tap.attributes == {"FUSE_DRW_NUM": "1-1"}


def test_a_feed_crosses_into_the_main_in_the_next_section():
    result = layout(*crossing_lineup())
    assert len(result.pages) == 1 and not result.warnings
    page = result.pages[0]
    first, second = page.placed_sections
    # Section 1 holds only the feed, so the main bus starts at section 2's main breaker.
    assert first.section.bus is None
    assert page.parts.bus_start_path[0][0] == 60.5           # main's B phase
    # Section 1: content x 15 to 45, so section 2's content starts at 55; breaker at 55.5,
    # top terminals at y 65. The line side runs up 30 to C (y 95); A turns at 105, B at
    # 100, across to the feed's riser (3 in from x 15), and up 30 to the termination.
    assert lines(page, "A") == [((55.5, 65), (55.5, 105)), ((55.5, 105), (18, 105)), ((18, 105), (18, 135))]
    assert lines(page, "C") == [((65.5, 65), (65.5, 95)), ((65.5, 95), (28, 95)), ((28, 95), (28, 135))]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"][0]
    assert lugs.position == (18, 140)
    assert lugs.attributes == {"LOCATION": "FROM UTILITY"}
    # The feed is drawn with the main: no placeholder box for section 1.
    assert not page.parts.content_boxes


def test_a_feed_and_its_main_stay_on_one_page():
    feed, main = crossing_lineup()
    sections = [Section(feed), Section(main)]
    sections[1].push_to_next_page = True
    result = fit_pages(Switchboard("Test", sections), TEST_SETTINGS, TEST_CATALOG)
    assert [[p.number for p in page.placed_sections] for page in result.pages] == [[1, 2]]


def test_feeds_that_cannot_be_drawn_are_explained():
    far_feed = IncomingFeed()
    lineup = Switchboard("Test", [Section(SectionContents(above=far_feed)), Section(SectionContents()),
                                  Section(SectionContents(above=MainBreaker(Breaker("52-M1"), feed=None,
                                                                            feed_from=far_feed.id))),
                                  Section(SectionContents(below=MainBreaker(Breaker("52-M2"), feed=None)))])
    links, problems = feed_links(lineup)
    assert links == []
    assert problems == [
        "Section 3 above (52-M1): its incoming feed is in section 1; only a feed in the section "
        "next to it is drawn for now.",
        "Section 4 below (52-M2): choose its incoming feed.",
    ]
    page = fit_pages(lineup, TEST_SETTINGS, TEST_CATALOG).pages[0]
    assert [p.text for p in page.parts.placeholders] == ["NO FEED", "NO FEED"]
    # The far feed is not drawn as main lugs only: it stays a placeholder box.
    assert not [b for b in page.parts.blocks if b.block == "TEST_LUGS"]
    assert [(box.section_number, box.part) for box in page.parts.content_boxes] == [(1, "above")]


def test_feeds_and_feed_choices_are_saved(tmp_path):
    feed, main = crossing_lineup()
    original = Switchboard("Test", [Section(feed), Section(main)])
    assert open_project(save_project(original, tmp_path / "job.swbd")) == original


def test_the_bus_is_placed_low_enough_for_a_crossing_feed():
    # Many taps make the feed tall; the bus in the main's section is lowered to fit it.
    feed, main = crossing_lineup()
    feed.above.voltage_taps = [VoltageTap("m1") for _ in range(6)]
    page = layout(feed, main).pages[0]
    lugs = [b for b in page.parts.blocks if b.block == "TEST_LUGS"][0]
    assert lugs.position[1] + lugs.extents[3] <= TEST_SETTINGS.main_bus.content_top_y
