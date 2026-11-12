"""Power supplies (decision 2026-11-05; src/model/devices.py, the section editor's Devices box,
src/layout/device_pages.py): named PS-s-n, fed by a voltage tap, saved with the project, and
drawn on the device pages with their fuse lying beside them (option A)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFormLayout  # noqa: E402

from src.layout.block_catalog import BlockInfo, load_block_catalog  # noqa: E402
from src.layout.page_fitter import fit_pages  # noqa: E402
from src.layout.settings import load_settings  # noqa: E402
from src.model.devices import (  # noqa: E402
    DeviceSettings, FuseSettings, PowerSupplySettings, device_problems, load_device_settings,
    power_supplies_in,
)
from src.model.project_file import switchboard_from_dict, switchboard_to_dict  # noqa: E402
from src.model.section_contents import (  # noqa: E402
    Breaker, IncomingFeed, MainBreaker, PowerMeter, PowerSupply, SectionContents, VoltageTap,
)
from src.model.switchboard import Section, Switchboard  # noqa: E402
from tests.helpers import TEST_CATALOG, TEST_SETTINGS  # noqa: E402

APP = QApplication.instance() or QApplication([])


def lineup_with_a_supply(tap_feeds=None):
    supply = PowerSupply(attributes={"RATING": "240W-10A"})
    tap = VoltageTap(feeds=supply.id if tap_feeds is None else tap_feeds)
    main = MainBreaker(Breaker("52-M1"), feed=IncomingFeed(voltage_taps=[tap]))
    sections = [Section(SectionContents(power_supplies=[PowerSupply()])),
                Section(SectionContents(above=main, power_supplies=[supply]))]
    return Switchboard("Test", sections), supply, tap


def test_power_supplies_are_numbered_through_the_lineup():
    switchboard, supply, _ = lineup_with_a_supply()
    assert [(info.name, info.supply is supply) for info in power_supplies_in(switchboard)] == [
        ("PS-1", False), ("PS-2", True)]


def test_a_tap_can_feed_a_power_supply():
    switchboard, _, _ = lineup_with_a_supply()
    # Only the unfed PS-1 is reported; FA-1 feeding PS-2 is fine.
    assert device_problems(switchboard) == [
        'PS-1 (section 1): no voltage tap feeds it yet; pick it in a voltage tap\'s "Feeds" list.']


def test_a_tap_feeding_a_removed_device_is_reported():
    switchboard, _, _ = lineup_with_a_supply(tap_feeds="gone")
    assert "Section 2 above (feed of 52-M1): voltage tap FA-1 feeds a device that no longer exists." \
        in device_problems(switchboard)


def test_two_taps_on_one_power_supply_are_reported():
    switchboard, supply, _ = lineup_with_a_supply()
    switchboard.sections[1].contents.above.feed.voltage_taps.append(VoltageTap(feeds=supply.id))
    assert any("PS-2 is fed by more than one voltage tap (FA-1, FA-2)" in p
               for p in device_problems(switchboard))


def test_power_supplies_and_what_taps_feed_are_saved_and_opened():
    switchboard, supply, tap = lineup_with_a_supply()
    data = switchboard_to_dict(switchboard)
    assert data["sections"][1]["power_supplies"] == [{"id": supply.id, "attributes": {"RATING": "240W-10A"}}]
    assert switchboard_from_dict(data) == switchboard


def test_older_files_say_meter_for_what_a_tap_feeds():
    meter = PowerMeter("Janitza UMG 801", id="m1")
    main = MainBreaker(Breaker("52-M1"), feed=IncomingFeed(voltage_taps=[VoltageTap(feeds="m1")]))
    data = switchboard_to_dict(Switchboard("Old", [Section(SectionContents(above=main, power_meters=[meter]))]))
    section = data["sections"][0]
    section["above"]["feed"]["voltage_taps"] = [{"meter": "m1", "fuse_attributes": {}}]
    del section["power_supplies"]
    opened = switchboard_from_dict(data).sections[0].contents
    assert opened.above.feed.voltage_taps[0].feeds == "m1" and opened.power_supplies == []


def test_the_editor_adds_a_power_supply_and_a_tap_can_feed_it():
    from src.ui.section_editor import SectionEditor

    devices = load_device_settings("config/devices.json")
    main = MainBreaker(Breaker("52-M1"))
    section = Section(SectionContents(above=main))
    switchboard = Switchboard("Test", [section])
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard,
                           fuse=devices.fuse, power_supply=devices.power_supply)
    editor.load(section, 1)
    devices_box = editor.devices_editor
    devices_box._add_supply()
    supply = section.contents.power_supplies[0]
    assert devices_box.supplies_list.item(0).text().startswith("PS-1")
    # One field per block attribute, by its prompt; the number is the program's.
    tags = [devices_box.supply_attributes_form.itemAt(row, QFormLayout.FieldRole).widget().toolTip()
            for row in range(devices_box.supply_attributes_form.rowCount())]
    assert "Attribute RATING" in tags and "Attribute PS_DRW_NUM" not in tags

    editor.load(section, 1)                          # the taps editor sees the new supply
    taps_editor = editor.above_editor.taps_editor
    taps_editor._add_tap()
    taps_editor.feeds_combo.setCurrentIndex(taps_editor.feeds_combo.findData(supply.id))
    assert main.feed.voltage_taps[0].feeds == supply.id
    assert taps_editor.taps_list.item(0).text() == "FA-1   to PS-1   (line side)"
    editor.close()


# --- On the device pages (option A, 2026-11-05) ------------------------------------------
# Test blocks shaped like Sammy's: the power supply's inputs L1-L3 on its left side, 5 apart
# (x 0.5; y -5, -10, -15); the fuse lying down with its line side at x -7 and its load side at
# x 7 (A, B, C at y -2.5, -7.5, -12.5), its box reaching 14.5 right of its base point.

UP, LYING = "3-POLE VERTICAL", "3-POLE HORIZONTAL"
FUSE_MARKERS = {f"{p}_{side}_{o}": xy for p, i in (("A", 0), ("B", 1), ("C", 2)) for side, o, xy in (
    ("LINE", "V", (-19.5 + 5 * i, 12.5)), ("LOAD", "V", (-19.5 + 5 * i, -1.5)),
    ("LINE", "H", (-7.0, -2.5 - 5 * i)), ("LOAD", "H", (7.0, -2.5 - 5 * i)))}
PS_CATALOG = {
    **TEST_CATALOG,
    "TEST_FUSE": BlockInfo("TEST_FUSE", (), (), extents=(-22.0, -15.0, 14.5, 13.0), visibility_states=(UP, LYING),
                           states={UP: {"markers": {}, "extents": (-22.0, -2.0, 14.5, 13.0)},
                                   LYING: {"markers": {}, "extents": (-7.5, -15.0, 14.5, 11.5)}},
                           markers=FUSE_MARKERS),
    "TEST_PS": BlockInfo("TEST_PS", (), (), extents=(0.0, -30.0, 15.5, 11.5),
                         markers={"L1": (0.5, -5.0), "L2": (0.5, -10.0), "L3": (0.5, -15.0)}),
}
WIRES = {"A": "WIRE A", "B": "WIRE B", "C": "WIRE C"}


def ps_devices(lying=True):
    return DeviceSettings(
        comms_modules=[], power_meters={},
        fuse=FuseSettings("TEST_FUSE", UP, {p: f"{p}_LINE_V" for p in "ABC"}, {p: f"{p}_LOAD_V" for p in "ABC"},
                          "FUSE_NO", "0", WIRES,
                          horizontal_state=LYING if lying else "",
                          horizontal_line_markers={p: f"{p}_LINE_H" for p in "ABC"},
                          horizontal_load_markers={p: f"{p}_LOAD_H" for p in "ABC"}),
        power_supply=PowerSupplySettings("TEST_PS", {"A": "L1", "B": "L2", "C": "L3"}, "PS_NO", "0"))


def ps_pages(switchboard, devices=None):
    result = fit_pages(switchboard, TEST_SETTINGS, PS_CATALOG, devices or ps_devices())
    return result, [p for p in result.pages if not p.placed_sections]


def ps_page(switchboard, devices=None):
    result, pages = ps_pages(switchboard, devices)
    assert len(pages) == 1
    return result, pages[0]


def placed(page, name):
    return [b for b in page.parts.blocks if b.block == name]


def lineup(*supply_sections):
    """Section 1: a main whose feed has one tap; supplies in the sections given, the first fed."""
    supplies = [PowerSupply(attributes={"RATING": "240W-10A"}) for _ in supply_sections]
    tap = VoltageTap(supplies[0].id if supplies else "", {"CURRENT": "3A"})
    sections = [Section(SectionContents(above=MainBreaker(Breaker("52-M1"), feed=IncomingFeed(voltage_taps=[tap])))),
                Section(SectionContents(above=MainBreaker(Breaker("52-M2"))))]
    for supply, number in zip(supplies, supply_sections):
        sections[number - 1].contents.power_supplies.append(supply)
    return Switchboard("Test", sections)


def test_the_fuse_lies_beside_its_power_supply_and_the_wires_run_straight():
    result, page = ps_page(lineup(1))
    assert result.warnings == []
    supply, fuse = placed(page, "TEST_PS")[0], placed(page, "TEST_FUSE")[0]
    assert supply.attributes == {"RATING": "240W-10A", "PS_NO": "1"}
    assert fuse.visibility == LYING and fuse.attributes == {"CURRENT": "3A", "FUSE_NO": "1"}
    sx, sy = supply.position
    # The fuse's box ends 5 (wire spacing) before the supply's box; its load side is level
    # with L1-L3, so each wire is one straight line onto its input.
    assert fuse.position[0] + 14.5 == sx - 5.0
    across = {w.layer: (w.start, w.end) for w in page.parts.wires if w.end[0] == sx + 0.5}
    assert across == {"WIRE A": ((fuse.position[0] + 7.0, sy - 5.0), (sx + 0.5, sy - 5.0)),
                      "WIRE B": ((fuse.position[0] + 7.0, sy - 10.0), (sx + 0.5, sy - 10.0)),
                      "WIRE C": ((fuse.position[0] + 7.0, sy - 15.0), (sx + 0.5, sy - 15.0))}
    # Line side: stubs to the left, a lying tilde on each end, the bracket mirrored to face
    # them, FROM the 3-line page of the tap.
    tildes = placed(page, "TEST_WIRE_TILDE")
    assert len(tildes) == 3 and all(t.visibility == "HORIZONTAL" for t in tildes)
    # Mirrored to face the wires arriving from the left, with only the left-right flip
    # (Sammy, 2026-11-05); every text attribute blank.
    assert all(t.flipped and t.flip_parameter == "Flip state1" and t.attributes == {"TEXT_H": ""}
               for t in tildes)
    assert {t.position for t in tildes} == {(fuse.position[0] - 7.0 - 8.0, sy - 5.0 * k) for k in (1, 2, 3)}
    bracket = placed(page, "TEST_BRACKET")[0]
    assert bracket.attributes == {"VERTICAL_LABLE": "FROM SHEET 1"} and bracket.visibility == "VERTICAL BRACKET"
    assert bracket.flipped and bracket.flip_parameter == "Flip state1"
    assert bracket.position == (fuse.position[0] - 7.0 - 8.0 - 2.0, sy - 10.0)
    # The 3-line tap points at the device page its fuse is on.
    tap = [b for b in result.pages[0].parts.blocks if b.block == "TEST_TAP"][0]
    assert tap.attributes["TO_SHEET"] == "2"


def test_a_power_supply_fed_from_another_section():
    _, (first, second) = ps_pages(lineup(2))           # one page per section
    labels = sorted(next(iter(b.attributes.values())) for b in placed(first, "TEST_BRACKET"))
    # The fuse, alone in section 1: FROM the 3-line, TO the supply on sheet 3.
    assert labels == ["FROM SHEET 1", "TO PS-1 SHEET 3"]
    assert placed(first, "TEST_FUSE")[0].visibility == UP
    # The supply, on section 2's page: FROM the fuse on sheet 2.
    assert [b.attributes for b in placed(second, "TEST_BRACKET")] == [{"VERTICAL_LABLE": "FROM FA-1 SHEET 2"}]


def test_a_power_supply_with_no_tap_is_drawn_alone():
    switchboard = lineup(1)
    switchboard.sections[0].contents.above.feed.voltage_taps.clear()
    _, page = ps_page(switchboard)
    assert len(placed(page, "TEST_PS")) == 1
    assert not placed(page, "TEST_FUSE") and not page.parts.wires


def test_without_a_lying_fuse_state_the_fuse_goes_to_the_supply_by_bracket():
    _, page = ps_page(lineup(1), ps_devices(lying=False))
    labels = sorted(next(iter(b.attributes.values())) for b in placed(page, "TEST_BRACKET"))
    assert labels == ["FROM FA-1 SHEET 2", "FROM SHEET 1", "TO PS-1 SHEET 2"]


def test_the_power_supply_comes_first_in_its_section():
    """Top left, before the meters (Sammy, 2026-11-05): it powers what comes after it."""
    switchboard = lineup(1)
    switchboard.sections[0].contents.power_meters.append(PowerMeter(""))     # drawn as a box
    _, page = ps_page(switchboard)
    supply = placed(page, "TEST_PS")[0]
    meter_box = page.parts.placeholders[0]
    assert supply.position[0] + 15.5 < meter_box.left_x         # the supply is left of the meter


def test_every_wire_gets_its_label():
    """Wire labels (decision 2026-11-09): tap n's wires from the 3-line are 2n-1, from its
    fuse onward 2n; one label per wire run, centred 1 above its longest across piece."""
    _, page = ps_page(lineup(1))
    labels = {label.text: label for label in page.parts.wire_labels}
    assert sorted(labels) == ["4A001", "4A002", "4B001", "4B002", "4C001", "4C002"]
    supply = placed(page, "TEST_PS")[0]
    sx, sy = supply.position
    fuse_x = placed(page, "TEST_FUSE")[0].position[0]
    # Fuse to supply: the middle of the straight wire into L1, 1 above it.
    a = labels["4A002"]
    assert (a.x, a.y, a.rotation) == ((fuse_x + 7.0 + sx + 0.5) / 2, sy - 5.0 + 1.0, 0.0)
    # The stubs FROM the 3-line: the same number as the tap's wires there.
    assert labels["4A001"].y == sy - 5.0 + 1.0 and labels["4A001"].x < fuse_x
    # Every labelled piece carries its run's label.
    assert {w.label for w in page.parts.wires} == set(labels)


# --- 24 V to the comms modules and the Ethernet switch (Sammy, 2026-11-11) ----------------

def feeding_devices():
    devices = ps_devices()
    supply = PowerSupplySettings("TEST_PS", {"A": "L1", "B": "L2", "C": "L3"}, "PS_NO", "0",
                                 outputs={"+": "24P1", "-": "24N1"},
                                 output_wire_layers={"+": "WIRE 24+", "-": "WIRE 24-"})
    catalog_ps = PS_CATALOG["TEST_PS"]
    PS_CATALOG["TEST_PS_FEEDING"] = BlockInfo("TEST_PS", (), (), extents=catalog_ps.extents,
                                              markers={**catalog_ps.markers, "24P1": (14.5, -2.5),
                                                       "24N1": (14.5, -7.5)})
    return DeviceSettings(comms_modules=devices.comms_modules, power_meters={}, fuse=devices.fuse,
                          power_supply=supply)


def feeding_catalog():
    feeding_devices()
    return {**PS_CATALOG, "TEST_PS": PS_CATALOG["TEST_PS_FEEDING"],
            "BUS_NODE": BlockInfo("BUS_NODE", (), (), extents=(-0.75, -0.75, 0.75, 0.75))}


def test_the_power_supply_feeds_24v_to_the_boxes_in_its_section():
    board = lineup(1)
    contents = board.sections[0].contents
    contents.above.breaker.comms_module = "Siemens COM190"
    contents.ethernet_switch = True
    result = fit_pages(board, TEST_SETTINGS, feeding_catalog(), feeding_devices())
    page = [p for p in result.pages if not p.placed_sections][0]
    supply = placed(page, "TEST_PS")[0]
    sx, sy = supply.position
    switch, comms = page.parts.placeholders
    assert (switch.text, comms.text) == ("ETHERNET SWITCH", "52-M1 Siemens COM190")
    # Boxes stacked to the right, left edges lined up: outputs at x 14.5, + rail 8 right of
    # them, - rail 5 further, the boxes 8 beyond that; the first box is level with the outputs.
    box_left = sx + 14.5 + 8.0 + 5.0 + 8.0
    assert switch.left_x == comms.left_x == box_left
    assert (switch.top_y + switch.bottom_y) / 2 == sy - 5.0
    assert comms.top_y == switch.bottom_y - 6.0
    # Straight across into the first box (meeting its rail on the way), then the rail down
    # and a branch into the second; every wire ends 2 inside its box.
    comms_middle = (comms.top_y + comms.bottom_y) / 2
    end = box_left + 2.0
    assert segments(page, "WIRE 24+") == {
        ((sx + 14.5, sy - 2.5), (sx + 22.5, sy - 2.5)), ((sx + 22.5, sy - 2.5), (end, sy - 2.5)),
        ((sx + 22.5, sy - 2.5), (sx + 22.5, comms_middle + 2.5)),
        ((sx + 22.5, comms_middle + 2.5), (end, comms_middle + 2.5))}
    assert segments(page, "WIRE 24-") == {
        ((sx + 14.5, sy - 7.5), (sx + 27.5, sy - 7.5)), ((sx + 27.5, sy - 7.5), (end, sy - 7.5)),
        ((sx + 27.5, sy - 7.5), (sx + 27.5, comms_middle - 2.5)),
        ((sx + 27.5, comms_middle - 2.5), (end, comms_middle - 2.5))}
    # A dot at each tee (not at the last corner, and not where the - wire crosses the + rail).
    assert [b.position for b in placed(page, "BUS_NODE")] == [(sx + 22.5, sy - 2.5), (sx + 27.5, sy - 7.5)]


def segments(page, layer):
    """The wire pieces on `layer`, each written top/left end first."""
    return {tuple(sorted((w.start, w.end), key=lambda p: (p[0], -p[1])))
            for w in page.parts.wires if w.layer == layer}


def test_without_the_shipping_split_blocks_other_sections_stay_unwired():
    board = lineup(1)
    board.sections[1].contents.above.breaker.comms_module = "Siemens COM190"
    result = fit_pages(board, TEST_SETTINGS, feeding_catalog(), feeding_devices())
    page_2 = [p for p in result.pages if not p.placed_sections][1]
    assert [b.text for b in page_2.parts.placeholders] == ["52-M2 Siemens COM190"]
    assert page_2.parts.wires == []


# --- Shipping splits (Sammy, 2026-11-11) ---------------------------------------------------

SPLIT_PINS = {f"CONN_{n}": (7.0, -2.5 - 5.0 * (n - 1)) for n in range(1, 11)}
FEMALE_PINS = {f"CONN_{n}": (0.5, -2.5 - 5.0 * (n - 1)) for n in range(1, 11)}


def split_devices():
    from src.model.devices import ShippingSplitSettings
    devices = feeding_devices()
    return DeviceSettings(comms_modules=[], power_meters={}, fuse=devices.fuse, power_supply=devices.power_supply,
                          shipping_split=ShippingSplitSettings(
                              "TEST_SSM", "TEST_SSF", "SS_NO", "{section}SSM-{number}", "{section}SSF-{number}",
                              "CONN_{pin}", 10, "0"))


def split_catalog():
    return {**feeding_catalog(),
            "TEST_SSM": BlockInfo("TEST_SSM", (), (), extents=(-2.0, -50.0, 8.2, 6.5), markers=SPLIT_PINS),
            "TEST_SSF": BlockInfo("TEST_SSF", (), (), extents=(0.0, -50.0, 9.5, 6.5), markers=FEMALE_PINS)}


def lineup_of(count, supply_section, comms_sections):
    """`count` sections with a breaker each; the one power supply in `supply_section` (fed
    by a tap on section 1's main); a COM190 on the breakers of `comms_sections`."""
    supply = PowerSupply()
    sections = [Section(SectionContents(above=MainBreaker(
        Breaker(f"52-M{n}", comms_module="Siemens COM190" if n in comms_sections else ""),
        feed=IncomingFeed(voltage_taps=[VoltageTap(supply.id)]) if n == 1 else None)))
        for n in range(1, count + 1)]
    sections[supply_section - 1].contents.power_supplies.append(supply)
    return Switchboard("Test", sections)


def split_layout(board):
    result = fit_pages(board, TEST_SETTINGS, split_catalog(), split_devices())
    return result, [p for p in result.pages if not p.placed_sections]


def names_on(page, block):
    return [b.attributes["SS_NO"] for b in page.parts.blocks if b.block == block]


def test_24v_crosses_each_boundary_on_a_male_in_each_section_and_the_females_go_last():
    # Supply in section 2 of 4; loads in sections 1 and 4. Boundaries 1|2, 2|3 and 3|4 are
    # crossed; section 3 only passes the 24 V on.
    result, pages = split_layout(lineup_of(4, 2, {1, 4}))
    titles = [p.parts.title for p in pages]
    assert titles == ["ELECTRICAL SCHEMATIC SECTION 1", "ELECTRICAL SCHEMATIC SECTION 2",
                      "ELECTRICAL SCHEMATIC SECTION 3", "ELECTRICAL SCHEMATIC SECTION 4", "SHIPPING SPLITS"]
    # Males numbered within their section, left boundary first.
    assert [names_on(p, "TEST_SSM") for p in pages[:4]] == [["1SSM-1"], ["2SSM-1", "2SSM-2"],
                                                           ["3SSM-1", "3SSM-2"], ["4SSM-1"]]
    # The left boundary's male faces right (pins on its right), the right one's is flipped.
    section_2 = {b.attributes["SS_NO"]: b for b in pages[1].parts.blocks if b.block == "TEST_SSM"}
    assert not section_2["2SSM-1"].flipped and section_2["2SSM-2"].flipped
    # Females: each split's two, on the last page, named for their own section.
    assert names_on(pages[4], "TEST_SSF") == ["1SSF-1", "2SSF-1", "2SSF-2", "3SSF-1", "3SSF-2", "4SSF-1"]
    # Each cable: + on pin 1, - on pin 2. The supply's fuse is in section 1 (on 52-M1's
    # feed), so its three phases also cross 1|2, on pins 3-5.
    cable = pages[4].parts.wires
    assert sorted(w.layer for w in cable) == sorted(["WIRE 24+", "WIRE 24-"] * 3 + ["WIRE A", "WIRE B", "WIRE C"])
    assert all(w.start[1] == w.end[1] for w in cable)


def test_a_section_fed_through_a_split_wires_its_male_to_its_boxes():
    result, pages = split_layout(lineup_of(2, 1, {2}))
    page = pages[1]
    male = [b for b in page.parts.blocks if b.block == "TEST_SSM"][0]
    box = page.parts.placeholders[0]
    assert male.attributes["SS_NO"] == "2SSM-1" and box.text == "52-M2 Siemens COM190"
    mx, my = male.position
    plus, minus = segments(page, "WIRE 24+"), segments(page, "WIRE 24-")
    # Pin 1 (+) and pin 2 (-) straight across to the box, passing their rails.
    assert ((mx + 7.0, my - 2.5), (mx + 7.0 + 8.0, my - 2.5)) in plus
    assert ((mx + 7.0, my - 7.5), (mx + 7.0 + 13.0, my - 7.5)) in minus
    assert box.left_x == mx + 7.0 + 21.0
    assert (box.top_y + box.bottom_y) / 2 == my - 5.0


def test_no_splits_when_everything_is_in_the_supplys_section():
    result, pages = split_layout(lineup_of(3, 1, {1}))
    assert [p.parts.title for p in pages][-1] != "SHIPPING SPLITS"
    assert not any(b.block in ("TEST_SSM", "TEST_SSF") for p in pages for b in p.parts.blocks)


def test_a_second_power_supply_is_drawn_but_not_wired():
    board = lineup_of(2, 1, {1})
    board.sections[1].contents.power_supplies.append(PowerSupply())
    result, _ = split_layout(board)
    assert "A lineup has one 24 V power supply (Sammy, 2026-11-11); PS-2 is drawn but not wired." \
        in result.warnings


def test_a_fuse_feeding_another_section_sends_its_phases_through_the_splits():
    # Sammy, 2026-11-11: rare, but kept. The supply in section 3, its fuse in section 1:
    # the three phases cross 1|2 and 2|3, after the 24 V's pins (none here: no boxes).
    result, pages = split_layout(lineup_of(3, 3, set()))
    section_1, section_2, section_3 = pages[:3]
    assert names_on(section_1, "TEST_SSM") == ["1SSM-1"]
    assert names_on(section_2, "TEST_SSM") == ["2SSM-1", "2SSM-2"]
    assert names_on(section_3, "TEST_SSM") == ["3SSM-1"]
    # Section 1: the fuse lies down and its load side runs straight into 1SSM-1's pins 1-3
    # (no TO bracket on it).
    fuse = placed(section_1, "TEST_FUSE")[0]
    assert fuse.visibility == LYING
    male_1 = [b for b in section_1.parts.blocks if b.block == "TEST_SSM"][0]
    phase_wires = {w.layer: w for w in section_1.parts.wires if w.layer in ("WIRE A", "WIRE B", "WIRE C")
                   and w.end[0] == male_1.position[0] - 7.0}
    assert len(phase_wires) == 3 and all(w.start[1] == w.end[1] for w in phase_wires.values())
    assert [b.attributes for b in placed(section_1, "TEST_BRACKET")] == [{"VERTICAL_LABLE": "FROM SHEET 1"}]
    # Section 2 only passes them on: three straight wires from 2SSM-1 across the page to 2SSM-2.
    across = section_2.parts.wires
    assert sorted(w.layer for w in across) == ["WIRE A", "WIRE B", "WIRE C"]
    assert all(w.start[1] == w.end[1] and w.end[0] - w.start[0] > 300 for w in across)
    # Section 3: the power supply keeps its FROM bracket; the male's pins get stubs.
    assert sorted(w.layer for w in pages[2].parts.wires if abs(abs(w.end[0] - w.start[0]) - 6.0) < 1e-9
                  and w.layer.startswith("WIRE ") and w.layer[-1] in "ABC") == ["WIRE A", "WIRE B", "WIRE C"]
    assert pages[-1].parts.title == "SHIPPING SPLITS" and len(pages[-1].parts.wires) == 6


def test_the_right_male_sits_at_the_pages_right_edge():
    result, pages = split_layout(lineup_of(3, 1, {1, 3}))
    middle = pages[1]
    right_male = [b for b in middle.parts.blocks if b.attributes.get("SS_NO") == "2SSM-2"][0]
    left_male = [b for b in middle.parts.blocks if b.attributes.get("SS_NO") == "2SSM-1"][0]
    page_right = TEST_SETTINGS.drawable_width - TEST_SETTINGS.margin_standard
    assert abs(right_male.position[0] + right_male.extents[2] - page_right) < 1e-6
    assert abs(left_male.position[0] + left_male.extents[0] - TEST_SETTINGS.margin_standard) < 1e-6


def test_the_supplys_outputs_stay_put_when_its_left_male_moves_to_the_page_edge():
    # Supply in section 2, a COM190 in section 1: 2SSM-1 sits flush with the page's left
    # edge (left of the supply's FROM bracket), and the 24 V still leaves from the supply.
    result, pages = split_layout(lineup_of(2, 2, {1, 2}))
    page = pages[1]
    supply = placed(page, "TEST_PS")[0]
    male = [b for b in page.parts.blocks if b.block == "TEST_SSM"][0]
    assert abs(male.position[0] + male.extents[0] - TEST_SETTINGS.margin_standard) < 1e-6
    sx, sy = supply.position
    plus_starts = {w.start for w in page.parts.wires if w.layer == "WIRE 24+"}
    assert (sx + 14.5, sy - 2.5) in plus_starts
    assert (male.position[0] + 7.0, male.position[1] - 2.5) in plus_starts
