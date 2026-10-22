"""Tests for CTs and power meters (decision 2026-10-21; src/layout/current_transformers.py,
src/model/devices.py).

Test numbers (tests/helpers.py): CT block TEST_CT reaches 20 left / 60 right of its A
marker, 10 up and 35 down (45 tall); clearance 5, so a run needs 55. Breaker blocks reach
3.5 past their terminals at most, poles 10 long. Feeder block reaches 1 below its C
connection and 13 above its A connection. Usual riser gap 15, group lead 15, tie step 70.
"""
from src.layout.current_transformers import ct_room
from src.layout.page_fitter import fit_pages
from src.model.devices import ct_sets_in, device_problems, meters_in
from src.model.project_file import open_project, save_project
from src.model.section_contents import (
    Breaker, CurrentTransformers, GroupMounted, MainBreaker, PowerMeter, SectionContents,
    SingleBreaker, TieBreaker, TwinLevel,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS

TOP_STATE = "CT LEFT - POLARITY TOP"
BOTTOM_STATE = "CT LEFT - POLARITY BOTTOM"
METER = PowerMeter(model="Janitza UMG 801", id="m1")


def cts(ratio="4000:5A", meter="m1"):
    return CurrentTransformers(meter_id=meter, ratio=ratio)


def board(*contents, meters=(METER,)):
    sections = [Section(c) for c in contents]
    sections[0].contents.power_meters = list(meters)
    return Switchboard("Test", sections)


def layout(switchboard, catalog=TEST_CATALOG):
    return fit_pages(switchboard, TEST_SETTINGS, catalog)


def blocks(page, name):
    return [b for b in page.parts.blocks if b.block == name]


def test_room_comes_from_the_catalog():
    room = ct_room(TEST_SETTINGS, TEST_CATALOG)
    assert (room.run, room.left, room.right) == (55, 20, 60)
    assert (room.breaker_overhang, room.breaker_pole) == (3.5, 10)
    assert room.feeder_overhang == {"above": 1, "below": 13}


def test_main_breaker_cts_sit_on_its_riser_with_polarity_toward_the_input():
    main = MainBreaker(Breaker("52-M1"), cts=cts())
    page = layout(board(SectionContents(above=main))).pages[0]
    # Bus B at 35, A at 40. The riser gap grows from 15 to 55 + 3.5 = 58.5, so the
    # breaker's bottom terminals are at 98.5 and its base point at 108.5. The riser moves
    # right so the CTs (reaching 20 left of A) clear the content edge at x 15: A at x 35.
    breaker = blocks(page, "TEST_BKR")[0]
    assert breaker.position == (35, 108.5)
    # Between the bus (A, y 40) and the breaker's edge (108.5 - 11 = 97.5), centred:
    # the block's middle is 12.5 below its A marker, so the marker sits at 68.75 + 12.5.
    ct = blocks(page, "TEST_CT")[0]
    assert ct.position == (35, 81.25)
    assert ct.visibility == TOP_STATE
    assert ct.attributes == {"CT_A_DWG#": "1", "CT_B_DWG#": "2", "CT_C_DWG#": "3", "STB#": "1",
                             "LOCATION": "PM-1", "CURRENT_RATIO": "4000:5A"}


def test_single_breaker_cts_point_toward_the_main_bus():
    contents = SectionContents(above=MainBreaker(Breaker("52-M1")),
                               below=SingleBreaker(Breaker("52-F1"), cts=cts()))
    page = layout(board(contents)).pages[0]
    assert blocks(page, "TEST_CT")[0].visibility == TOP_STATE      # the bus is above it
    contents = SectionContents(below=MainBreaker(Breaker("52-M1")),
                               above=SingleBreaker(Breaker("52-F1"), cts=cts()))
    page = layout(board(contents)).pages[0]
    assert blocks(page, "TEST_CT")[0].visibility == BOTTOM_STATE   # the bus is below it


def test_ct_sets_are_numbered_through_the_lineup():
    first = SectionContents(above=MainBreaker(Breaker("52-M1"), cts=cts()))
    second = SectionContents(below=SingleBreaker(Breaker("52-F1"), cts=cts(ratio="800:5A")))
    page = layout(board(first, second)).pages[0]
    second_ct = [b for b in blocks(page, "TEST_CT") if b.attributes["STB#"] == "2"][0]
    assert [second_ct.attributes[t] for t in ("CT_A_DWG#", "CT_B_DWG#", "CT_C_DWG#")] == ["4", "5", "6"]
    assert second_ct.attributes["CURRENT_RATIO"] == "800:5A"


def test_group_mounted_base_cts_push_level_one_out():
    group = GroupMounted([TwinLevel(Breaker("F1"), Breaker("F2"))], base_cts=cts())
    contents = SectionContents(above=group, below=MainBreaker(Breaker("52-M1")))
    page = layout(board(contents)).pages[0]
    bus_y = page.placed_sections[0].section.bus.body_y
    # Level 1's lowest tap (C) is 55 + 1 = 56 above the bus's top phase, not 15.
    feeders = blocks(page, "TEST_FEEDER")
    assert {round(f.position[1] - (bus_y + 5), 6) for f in feeders} == {56}
    ct = blocks(page, "TEST_CT")[0]
    assert ct.visibility == BOTTOM_STATE                           # source: the main bus
    # Centred between the bus (A) and the feeder blocks' lower edge (1 below the C tap).
    assert ct.position[1] - 12.5 == (bus_y + 5 + bus_y + 5 + 55) / 2


def test_tie_with_cts_steps_further_with_the_cts_on_the_entry_side():
    left = SectionContents(above=MainBreaker(Breaker("52-M1")),
                           tie=TieBreaker(Breaker("52-T"), bus_steps="up", cts=cts()))
    right = SectionContents(above=MainBreaker(Breaker("52-M2")))
    page = layout(board(left, right)).pages[0]
    plan = page.placed_sections[0].section.bus
    # The breaker sits 5 + 55 + 3.5 = 63.5 above where the bus enters; then its poles (10)
    # and the usual 30 to the exit: the step is 103.5.
    assert plan.exit_y - plan.body_y == 103.5
    ct = blocks(page, "TEST_CT")[0]
    assert ct.visibility == BOTTOM_STATE                           # entered from below
    tie = [b for b in blocks(page, "TEST_BKR") if b.label == "52-T"][0]
    assert tie.position[1] - 10 == plan.body_y + 63.5              # lower terminals


def test_breaker_fed_on_the_bus_side_warns_and_draws_no_cts():
    main = MainBreaker(Breaker("52-M1"), breaker_feed="bottom", cts=cts())
    result = layout(board(SectionContents(above=main)))
    assert not blocks(result.pages[0], "TEST_CT")
    assert any("CTs on a breaker fed on the bus side are not drawn yet" in w for w in result.warnings)


def test_without_the_ct_block_nothing_is_drawn_and_it_says_why():
    catalog = {name: info for name, info in TEST_CATALOG.items() if name != "TEST_CT"}
    result = layout(board(SectionContents(above=MainBreaker(Breaker("52-M1"), cts=cts()))), catalog)
    assert any('CTs are not drawn: block "TEST_CT"' in w for w in result.warnings)


def test_meters_are_named_in_lineup_order_and_problems_are_listed():
    first = SectionContents(above=MainBreaker(Breaker("52-M1"), cts=cts(meter="")))
    second = SectionContents(below=SingleBreaker(Breaker("52-F1"), cts=cts(meter="gone")))
    second.power_meters = [PowerMeter(model="", id="m2")]
    switchboard = board(first, second)
    assert [(m.name, m.section_number) for m in meters_in(switchboard)] == [("PM-1", 1), ("PM-2", 2)]
    assert [(c.number, c.part) for c in ct_sets_in(switchboard)] == [(1, "above"), (2, "below")]
    assert device_problems(switchboard) == [
        "Section 1 above (52-M1): choose the power meter its CTs feed.",
        "Section 2 below (52-F1): its CTs feed a power meter that no longer exists.",
        "PM-2 (section 2): choose its model.",
    ]


def test_cts_and_meters_are_saved_with_the_project(tmp_path):
    group = GroupMounted([TwinLevel(Breaker("F1"), Breaker("F2"))],
                         base_cts=CurrentTransformers("m1", "600:5A", {"CT_BOM": "12"}))
    original = board(SectionContents(above=MainBreaker(Breaker("52-M1"), cts=cts()), below=group,
                                     tie=TieBreaker(Breaker("52-T"), cts=cts(ratio="2000:5A"))))
    path = save_project(original, tmp_path / "job.swbd")
    assert open_project(path) == original


def test_where_the_bus_begins_it_bends_into_the_leftmost_riser():
    # The main's CTs move its riser right, so the single breaker below is further left: the
    # bus starts there, and the main tees in with dots (nothing tees into missing bus).
    contents = SectionContents(above=MainBreaker(Breaker("52-M1"), cts=cts()),
                               below=SingleBreaker(Breaker("52-F1")))
    # A second section, so the bus doesn't also end in the first one.
    page = layout(board(contents, SectionContents(above=MainBreaker(Breaker("52-M2"))))).pages[0]
    single_b_x = 15.5 + 5
    assert page.parts.bus_start_path[0][0] == single_b_x
    dots = [b.position for b in page.parts.blocks if b.block == "BUS_NODE"]
    assert [x for x, _ in dots] == [35, 40, 45]                 # the main's riser (A at 35)
