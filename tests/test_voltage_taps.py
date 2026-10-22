"""Tests for the incoming feed split and voltage taps (decision 2026-10-22; src/layout/
voltage_taps.py, src/model/section_contents.py, src/model/project_file.py).

Test numbers (tests/helpers.py): tap block TEST_TAP reaches 2 above its A marker and 12
below (14 tall), 1 left, 30 right; clearance 5. Breaker blocks reach 3.5 past their
terminals at most. Usual run from the breaker to the termination: 30.
"""
import json

from src.layout.page_fitter import fit_pages
from src.layout.voltage_taps import tap_room
from src.model.devices import device_problems, voltage_taps_in
from src.model.project_file import open_project, save_project
from src.model.section_contents import (
    Breaker, IncomingFeed, MainBreaker, PowerMeter, SectionContents, VoltageTap,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS

METER = PowerMeter(model="Janitza UMG 801", id="m1")


def main_with_taps(count, label="52-M1", **feed):
    return MainBreaker(Breaker(label), feed=IncomingFeed(
        voltage_taps=[VoltageTap(meter_id="m1") for _ in range(count)], **feed))


def board(*contents):
    sections = [Section(c) for c in contents]
    sections[0].contents.power_meters = [METER]
    return Switchboard("Test", sections)


def layout(switchboard):
    return fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG)


def taps_on(page):
    return [b for b in page.parts.blocks if b.block == "TEST_TAP"]


def test_room_comes_from_the_catalog():
    room = tap_room(TEST_SETTINGS, TEST_CATALOG)
    assert (room.up, room.down, room.left, room.right, room.breaker_overhang) == (2, 12, 1, 30, 3.5)
    # One tap fits in the usual 30 (3.5 + 5 + 14 + 5 = 27.5); two need 3.5 + 2 x 19 + 5.
    assert room.line_side_run(TEST_SETTINGS, 1) == 30
    assert room.line_side_run(TEST_SETTINGS, 2) == 46.5


def test_taps_sit_on_the_feed_between_breaker_and_termination():
    page = layout(board(SectionContents(above=main_with_taps(2)))).pages[0]
    # As in test_main_breakers: bus A at 40, breaker top terminals at y 65. The riser moves
    # right from x 15.5 to 16 so the taps (1 left of A, the breaker only 0.5) clear the
    # content edge at 15. The run grows to 46.5: the termination's bus end is at y 111.5.
    assert [l.start for l in page.parts.bus_lines if l.phase == "A"] == [(16, 111.5)]
    first, second = taps_on(page)
    # First tap: 3.5 past the terminals, 5 clear, then its bottom (12 below its A marker).
    assert first.position == (16, 65 + 3.5 + 5 + 12)
    assert second.position == (16, first.position[1] + 14 + 5)
    assert first.visibility == "FROM_LEFT"
    assert (first.attributes, second.attributes) == ({"FUSE_DRW_NUM": "1"}, {"FUSE_DRW_NUM": "2"})


def test_fuses_are_numbered_through_the_lineup():
    switchboard = board(SectionContents(above=main_with_taps(1)),
                        SectionContents(below=main_with_taps(2, label="52-M2")))
    assert [(t.fuse, t.section_number, t.part) for t in voltage_taps_in(switchboard)] == [
        ("FA-1", 1, "above"), ("FA-2", 2, "below"), ("FA-3", 2, "below")]


def test_taps_on_a_u_turned_feed_are_not_drawn_yet():
    main = main_with_taps(1, termination_feed="bottom")
    result = layout(board(SectionContents(above=main)))
    assert not taps_on(result.pages[0])
    assert any("voltage taps on a feed whose bus U-turns are not drawn yet" in w for w in result.warnings)


def test_a_tap_needs_a_meter():
    main = MainBreaker(Breaker("52-M1"), feed=IncomingFeed(voltage_taps=[VoltageTap()]))
    assert device_problems(board(SectionContents(above=main))) == [
        "Section 1 above (feed of 52-M1): choose the power meter voltage tap FA-1 feeds."]


def test_the_feed_and_its_taps_are_saved(tmp_path):
    original = board(SectionContents(above=main_with_taps(2, termination_feed="top",
                                                          input_attributes={"LOCATION": "FROM UTILITY"})))
    path = save_project(original, tmp_path / "job.swbd")
    assert json.loads(path.read_text(encoding="utf-8"))["format_version"] == 2
    assert open_project(path) == original


def test_a_format_1_file_is_read_into_a_feed(tmp_path):
    path = tmp_path / "old.swbd"
    path.write_text(json.dumps({"format_version": 1, "name": "Old", "sections": [{"above": {
        "kind": "main breaker", "label": "52-M1", "mounting": "fixed", "breaker_feed": "",
        "termination_feed": "bottom", "breaker_attributes": {},
        "input_attributes": {"LOCATION": "FROM UTILITY"}}, "below": None, "tie": None}]}),
        encoding="utf-8")
    main = open_project(path).sections[0].contents.above
    assert (main.feed.termination_feed, main.feed.input_attributes) == ("bottom", {"LOCATION": "FROM UTILITY"})
    assert main.feed.voltage_taps == []
