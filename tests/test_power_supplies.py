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


def segments(page, layer):
    """The wire pieces on `layer`, each written top/left end first."""
    return {tuple(sorted((w.start, w.end), key=lambda p: (p[0], -p[1])))
            for w in page.parts.wires if w.layer == layer}


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


# --- 24 V through fuses and terminal blocks (Sammy, 2026-11-13; plan approved 2026-11-16) ---
# Test blocks shaped like the library's: Terminal_Block (4 points; 1 and 2 take wires from the
# left, 3 and 4 from the right; bridge points at x -1) and the fixed 1-pole fuse (line at x 0,
# load at x 10).

from dataclasses import replace  # noqa: E402

from src.layout.control_power import control_power_loads, plan_control_power  # noqa: E402
from src.model.devices import ControlPowerSettings  # noqa: E402

TB_MARKERS = {"1_LEFT": (-5.5, -1.0), "1_TOP": (-5.0, -0.5), "1_BOTTOM": (-5.0, -1.5),
              "2_LEFT": (-3.0, 1.5), "2_TOP": (-2.5, 2.0), "2_BOTTOM": (-2.5, 1.0),
              "3_RIGHT": (3.0, 1.5), "3_TOP": (2.5, 2.0), "3_BOTTOM": (2.5, 1.0),
              "4_RIGHT": (5.5, -1.0), "4_TOP": (5.0, -0.5), "4_BOTTOM": (5.0, -1.5),
              "BRIDGE_TOP": (-1.0, 2.5), "BRIDGE_BOTTOM": (-1.0, -2.0)}
CONTROL_POWER = ControlPowerSettings(
    "TEST_FD", "FUSE_NAME", "FD-{number}", "CONN_A_LINE", "CONN_A_LOAD", "0", "TEST_TB", "#", "0",
    "BRIDGE_TOP", "BRIDGE_BOTTOM", "BRIDGE", 0.5, "{section}TB24{sign}", "TEXT", 1.25, 0.75,
    "{breaker} TRIP UNIT", "COM800-{number}")
POWER_SETTINGS = replace(TEST_SETTINGS, wire_labels=replace(
    TEST_SETTINGS.wire_labels, prefixes={**TEST_SETTINGS.wire_labels.prefixes, "WIRE 24+": "2+", "WIRE 24-": "2-"}))


def power_catalog(fuse_markers=True, terminal=True):
    catalog = {**split_catalog(),
               "TEST_FD": BlockInfo("TEST_FD", (), (), extents=(-1.0, -1.0, 12.0, 18.0),
                                    markers={"CONN_A_LINE": (0.0, 0.0), "CONN_A_LOAD": (10.0, 0.0)}
                                    if fuse_markers else {})}
    if terminal:
        catalog["TEST_TB"] = BlockInfo("TEST_TB", (), (), extents=(-6.25, -2.25, 6.25, 2.75), markers=TB_MARKERS)
    return catalog


def power_devices():
    d = split_devices()
    return DeviceSettings(comms_modules=[], power_meters={}, fuse=d.fuse, power_supply=d.power_supply,
                          shipping_split=d.shipping_split, control_power=CONTROL_POWER)


def power_layout(board, catalog=None):
    result = fit_pages(board, POWER_SETTINGS, catalog or power_catalog(), power_devices())
    return result, [p for p in result.pages if not p.placed_sections]


def plan_for(board, supply_section):
    loads = control_power_loads(board, CONTROL_POWER, POWER_SETTINGS.device_pages)
    layers = {"+": "WIRE 24+", "-": "WIRE 24-"}
    return plan_control_power(loads, CONTROL_POWER, supply_section,
                              lambda sign, n: POWER_SETTINGS.wire_labels.label(layers[sign], n))


def at_point(point, other, tolerance=1e-6):
    return abs(point[0] - other[0]) < tolerance and abs(point[1] - other[1]) < tolerance


def test_the_plan_one_fuse_for_the_trip_units_one_each_for_the_rest():
    # Three sections, a 3WA main in each (a trip unit each), the Ethernet switch in section 1,
    # the supply in section 1.
    board = lineup_of(3, 1, set())
    board.sections[0].contents.ethernet_switch = True
    plan = plan_for(board, 1)
    assert [load.name for load in plan.loads] == ["TU-1", "TU-2", "TU-3", "ES-1"]
    assert [load.text for load in plan.loads][:2] == ["52-M1 TRIP UNIT", "52-M2 TRIP UNIT"]
    assert plan.fuses == [("FD-1", "+FD-1"), ("FD-2", "+FD-2")]
    assert [c.key for c in plan.circuits] == ["+FD-1", "+FD-2", "-"]
    # Split on a terminal block where a circuit meets three or more points.
    assert plan.terminals == {(1, "+FD-1"), (2, "+FD-1"), (1, "-"), (2, "-")}
    # The trip units' + and the - cross both boundaries; the switch's + stays in section 1.
    assert plan.crossings() == [(1, 3, ["+FD-1"]), (1, 3, ["-"])]


def test_every_wire_has_its_own_number_and_keeps_it_through_a_split():
    board = lineup_of(3, 1, set())
    board.sections[0].contents.ethernet_switch = True
    plan = plan_for(board, 1)
    labels = {(s, k): [(e.start, e.end, e.label) for e in edges] for (s, k), edges in plan.edges.items()}
    assert plan.supply_label == "2+001"
    assert labels[(1, "+FD-1")] == [(("source",), ("terminal",), "2+002"),
                                    (("terminal",), ("load", "TU-1"), "2+003"),
                                    (("terminal",), ("split", 1), "2+004")]
    # Section 2: the wire in from the split is the same wire (2+004).
    assert labels[(2, "+FD-1")][0] == (("split", 1), ("terminal",), "2+004")
    # Section 3: only the trip unit: one wire straight from the split, still 2+006.
    assert labels[(3, "+FD-1")] == [(("split", 2), ("load", "TU-3"), "2+006")]
    assert labels[(1, "+FD-2")] == [(("source",), ("load", "ES-1"), "2+007")]
    assert labels[(1, "-")][0] == (("source",), ("terminal",), "2-001")
    assert plan.split_labels == {(1, "+FD-1"): "2+004", (2, "+FD-1"): "2+006", (1, "-"): "2-004", (2, "-"): "2-006"}


def test_a_supply_in_the_middle_sends_its_circuits_both_ways():
    plan = plan_for(lineup_of(3, 2, set()), 2)
    assert plan.crossings() == [(1, 3, ["+FD-1"]), (1, 3, ["-"])]
    # In section 2: in from the fuse; out to the trip unit and to both splits.
    assert [(e.start, e.end) for e in plan.edges[(2, "+FD-1")]] == [
        (("source",), ("terminal",)), (("terminal",), ("load", "TU-2")),
        (("terminal",), ("split", 1)), (("terminal",), ("split", 2))]


def test_com800_one_per_section_with_com060s_and_no_wires_to_the_comms_modules():
    from src.model.devices import com800s_in
    from src.model.section_contents import GroupMounted, TwinLevel
    board = lineup_of(2, 1, set())
    board.sections[1].contents.below = GroupMounted(levels=[TwinLevel(
        left=Breaker("52-F1", comms_module="Siemens COM060"), right=Breaker("52-F2", comms_module="Siemens COM060"))])
    assert [(c.number, c.section_number) for c in com800s_in(board)] == [(1, 2)]
    plan = plan_for(board, 1)
    assert [load.name for load in plan.loads] == ["TU-1", "TU-2", "COM800-1"]
    assert plan.fuses[-1] == ("FD-2", "+FD-2")


def test_the_fuses_stand_in_a_column_bridged_with_the_supplys_plus_into_the_first():
    board = lineup_of(2, 1, set())
    board.sections[0].contents.ethernet_switch = True
    result, pages = power_layout(board)
    page = pages[0]
    supply = placed(page, "TEST_PS")[0]
    sx, sy = supply.position
    fuses = placed(page, "TEST_FD")
    assert [f.attributes for f in fuses] == [{"FUSE_NAME": "FD-1"}, {"FUSE_NAME": "FD-2"}]
    # Line side 10 right of the supply's box (15.5), the first level with its + (y -2.5),
    # the next 20 below.
    line_x = sx + 15.5 + 10.0
    assert [f.position for f in fuses] == [(line_x, sy - 2.5), (line_x, sy - 22.5)]
    assert ((sx + 14.5, sy - 2.5), (line_x, sy - 2.5)) in segments(page, "WIRE 24+")
    bridges = [p for p in page.parts.polylines if p.points == [(line_x, sy - 2.5), (line_x, sy - 22.5)]]
    assert len(bridges) == 1 and bridges[0].layer == "BRIDGE" and bridges[0].width == 0.5
    # The supply's - drops in a lane between the supply and the fuses, to below them.
    minus = segments(page, "WIRE 24-")
    lane = sx + 15.5 + 5.0
    assert ((sx + 14.5, sy - 7.5), (lane, sy - 7.5)) in minus
    assert any(a == (lane, sy - 7.5) and b[0] == lane and b[1] < sy - 22.5 - 1.0 for a, b in minus)


def test_terminal_blocks_split_a_circuit_one_wire_per_point():
    board = lineup_of(2, 1, set())
    board.sections[0].contents.ethernet_switch = True
    result, pages = power_layout(board)
    page = pages[0]
    terminals = placed(page, "TEST_TB")
    # + : FD-1 in, the trip unit and the split out (one terminal). - : the supply in, the trip
    # unit, the switch and the split out (two terminals, bridged).
    assert sorted(t.text for t in page.parts.texts) == ["1TB24+", "1TB24-"]
    assert sorted(t.attributes["#"] for t in terminals) == ["1", "1", "2"]
    terminal_bridges = [p for p in page.parts.polylines if abs(abs(p.points[0][1] - p.points[1][1]) - 9.5) < 1e-6]
    assert len(terminal_bridges) == 1           # from 2.5 above the top one to 2 below the second
    # One wire per point: no terminal point has two wire ends on it, and every point used has one.
    ends = [w.start for w in page.parts.wires] + [w.end for w in page.parts.wires]
    used = 0
    for t in terminals:
        for marker, (mx, my) in TB_MARKERS.items():
            if marker.startswith("BRIDGE"):
                continue
            count = sum(1 for e in ends if at_point(e, (t.position[0] + mx, t.position[1] + my)))
            assert count <= 1
            used += count
    assert used == 3 + 4
    assert "The trip units and the Ethernet switch are drawn as boxes until their blocks exist." in result.warnings


def test_the_plus_terminals_sit_at_the_top_fed_from_below_and_the_minus_at_the_bottom_from_above():
    # Sammy, 2026-11-17: the + group above the devices, its wire in on a BOTTOM point; the -
    # group below them, its wire in on a TOP point.
    board = lineup_of(2, 1, set())
    board.sections[0].contents.ethernet_switch = True
    result, pages = power_layout(board)
    page = pages[0]
    boxes = [p for p in page.parts.placeholders if "TRIP UNIT" in p.text or p.text == "ETHERNET SWITCH"]
    tops, bottoms = {b.top_y for b in boxes}, {b.bottom_y for b in boxes}
    assert len(tops) == 1                       # tops lined up
    plus = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TB24+")]
    minus = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TB24-")]
    assert all(t.position[1] - 2.25 > max(tops) for t in plus)
    assert all(t.position[1] + 2.75 < min(bottoms) for t in minus)
    ends = {w.end for w in page.parts.wires} | {w.start for w in page.parts.wires}
    bottom_block = min(plus, key=lambda t: t.position[1])
    assert (bottom_block.position[0] - 5.0, bottom_block.position[1] - 1.5) in ends       # 1_BOTTOM
    top_block = max(minus, key=lambda t: t.position[1])
    assert (top_block.position[0] - 2.5, top_block.position[1] + 2.0) in ends             # 2_TOP


def test_the_split_pins_and_the_cables_carry_each_wires_number():
    result, pages = power_layout(lineup_of(3, 1, set()))
    assert [p.parts.title for p in pages][-1] == "SHIPPING SPLITS"
    assert [names_on(p, "TEST_SSM") for p in pages[:3]] == [["1SSM-1"], ["2SSM-1", "2SSM-2"], ["3SSM-1"]]
    # + on pin 1, - on pin 2; a new number each side of section 2's terminal blocks.
    assert sorted(label.text for label in pages[-1].parts.wire_labels) == ["2+004", "2+006", "2-003", "2-005"]


def test_a_wire_passing_through_a_section_runs_along_the_top_above_the_others():
    # The switch is in section 3, its fuse in section 1: its + passes through section 2,
    # whose splits stand at the page's ends, centred on the row (Sammy, 2026-11-17).
    board = lineup_of(3, 1, set())
    board.sections[2].contents.ethernet_switch = True
    result, pages = power_layout(board)
    middle = pages[1]
    left_male = [b for b in middle.parts.blocks if b.attributes.get("SS_NO") == "2SSM-1"][0]
    right_male = [b for b in middle.parts.blocks if b.attributes.get("SS_NO") == "2SSM-2"][0]
    page_right = TEST_SETTINGS.drawable_width - TEST_SETTINGS.margin_standard
    assert abs(right_male.position[0] + right_male.extents[2] - page_right) < 1e-6
    assert abs(left_male.position[0] + left_male.extents[0] - TEST_SETTINGS.margin_standard) < 1e-6
    assert left_male.position[1] == right_male.position[1]
    # The switch's + (the farthest-going) runs highest, across the page.
    plus = [w for w in middle.parts.wires if w.layer == "WIRE 24+" and w.start[1] == w.end[1]]
    highest = max(plus, key=lambda w: w.start[1])
    assert highest.label == "2+002" and abs(highest.end[0] - highest.start[0]) > 300


def test_the_supplys_outputs_stay_put_when_a_male_comes_in_on_the_left():
    # Supply in section 2: the trip unit in section 1 is fed back through 2SSM-1, which sits
    # flush with the page's left edge, centred on the row; the supply stands right of it.
    result, pages = power_layout(lineup_of(2, 2, set()))
    page = pages[1]
    supply = placed(page, "TEST_PS")[0]
    male = [b for b in page.parts.blocks if b.block == "TEST_SSM"][0]
    assert abs(male.position[0] + male.extents[0] - TEST_SETTINGS.margin_standard) < 1e-6
    assert male.position[0] + male.extents[2] < supply.position[0]
    sx, sy = supply.position
    assert (sx + 14.5, sy - 2.5) in {w.start for w in page.parts.wires if w.layer == "WIRE 24+"}
    assert crossings_on(page) == [] and crossings_on(pages[0]) == []


def test_a_boxs_plus_lands_at_the_top_of_its_left_edge_and_its_minus_at_the_bottom():
    # Sammy, 2026-11-17: the boxes are shaped like the blocks to come, + at the top and - at
    # the bottom of the left edge, 2.5 in (box_plus_pin_from_top, box_minus_pin_from_bottom).
    result, pages = power_layout(lineup_of(1, 1, set()))
    box = next(p for p in pages[0].parts.placeholders if p.text.startswith("52-M1 TRIP UNIT"))
    ends = {w.end for w in pages[0].parts.wires} | {w.start for w in pages[0].parts.wires}
    inside = box.left_x + POWER_SETTINGS.device_pages.feed_into_box
    assert (inside, box.top_y - 2.5) in ends and (inside, box.bottom_y + 2.5) in ends


def test_a_3wa_com190_is_named_in_its_trip_units_box_not_boxed_on_its_own():
    # Sammy, 2026-11-17: the trip unit's block will hold the COM190, wired inside it.
    result, pages = power_layout(lineup_of(2, 1, {1}))
    texts = [p.text for page in pages for p in page.parts.placeholders]
    assert "52-M1 TRIP UNIT\nSiemens COM190" in texts
    assert "52-M2 TRIP UNIT" in texts
    assert not any(t == "52-M1\nSiemens COM190" for t in texts)
    assert not any("comms modules" in w for w in result.warnings)


def test_without_a_supply_to_feed_the_trip_units_the_com190_keeps_its_box():
    board = lineup_of(2, 1, {1})
    board.sections[0].contents.power_supplies.clear()
    result, pages = power_layout(board)
    texts = [p.text for page in pages for p in page.parts.placeholders]
    assert "52-M1\nSiemens COM190" in texts and not any("TRIP UNIT" in t for t in texts)


def test_without_the_fuse_markers_the_fuses_are_boxes():
    result, pages = power_layout(lineup_of(1, 1, set()), power_catalog(fuse_markers=False))
    assert [p.text for p in pages[0].parts.placeholders if p.text.startswith("FD-")] == ["FD-1"]
    assert any("The 24 V fuses are drawn as boxes until block TEST_FD has its markers" in w for w in result.warnings)


def test_without_the_terminal_block_the_24v_isnt_wired():
    result, pages = power_layout(lineup_of(2, 1, set()), power_catalog(terminal=False))
    assert any('The 24 V isn\'t wired: block "TEST_TB"' in w for w in result.warnings)
    assert not any(w.layer.startswith("WIRE 24") for p in pages for w in p.parts.wires)


def test_a_second_power_supply_is_drawn_but_not_wired():
    board = lineup_of(2, 1, set())
    board.sections[1].contents.power_supplies.append(PowerSupply())
    result, _ = power_layout(board)
    assert "A lineup has one 24 V power supply (Sammy, 2026-11-11); PS-2 is drawn but not wired." \
        in result.warnings


# --- A meter wired straight into its pins: the UMG 801 Rev2 (Sammy, 2026-11-17) -------------
# A test block shaped like Janitzia_UMG801_Rev2: every pin on its edge, 5 apart; 24 V at the top
# of the left edge, then the voltage pins, then the CT inputs; a second CT set and the USB on
# the right edge.

from src.model.devices import MeterModel  # noqa: E402
from src.model.section_contents import CurrentTransformers  # noqa: E402

REV2_MARKERS = {
    "24V+": (0.0, -2.5), "24V-": (0.0, -7.5), "VN": (0.0, -12.5), "V3": (0.0, -17.5), "V2": (0.0, -22.5),
    "V1": (0.0, -27.5), "I1+": (0.0, -32.5), "I1-": (0.0, -37.5), "I2+": (0.0, -42.5), "I2-": (0.0, -47.5),
    "I3+": (0.0, -52.5), "I3-": (0.0, -57.5), "I5+": (15.0, -27.5), "I5-": (15.0, -32.5), "I6+": (15.0, -37.5),
    "I6-": (15.0, -42.5), "I7+": (15.0, -47.5), "I7-": (15.0, -52.5), "USB": (14.5, -18.5)}
REV2 = MeterModel(
    "Janitza UMG 801", "TEST_REV2", None, (), name_attribute="NAME", usb_marker="USB",
    voltage_pins={"A": "V1", "B": "VN", "C": "V3"},
    current_pins=({"A+": "I1+", "A-": "I1-", "B+": "I2+", "B-": "I2-", "C+": "I3+", "C-": "I3-"},
                  {"A+": "I5+", "A-": "I5-", "B+": "I6+", "B-": "I6-", "C+": "I7+", "C-": "I7-"}),
    current_wire_layers={"+": "WIRE CT+", "-": "WIRE CT-"}, supply_pins={"+": "24V+", "-": "24V-"})


def meter_catalog():
    return {**power_catalog(),
            "TEST_REV2": BlockInfo("TEST_REV2", (), (), extents=(-0.2, -82.8, 15.5, 7.5), markers=REV2_MARKERS)}


def meter_devices(control_power=True):
    d = power_devices()
    return DeviceSettings(comms_modules=[], power_meters={"Janitza UMG 801": REV2}, fuse=d.fuse,
                          power_supply=d.power_supply, shipping_split=d.shipping_split,
                          control_power=CONTROL_POWER if control_power else None)


def lineup_with_a_meter(supply=True):
    """One section: 52-M1's feed taps its power supply and its meter; its CTs feed the meter."""
    board = lineup_of(1, 1, set())
    contents = board.sections[0].contents
    if not supply:
        contents.power_supplies.clear()
        contents.above.feed.voltage_taps.clear()
    meter = PowerMeter("Janitza UMG 801", id="m1")
    contents.power_meters.append(meter)
    contents.above.feed.voltage_taps.append(VoltageTap("m1", {"CURRENT": "1A"}))
    contents.above.cts = CurrentTransformers("m1", "4000:5A")
    return board


METER_SETTINGS = replace(POWER_SETTINGS, wire_labels=replace(
    POWER_SETTINGS.wire_labels, prefixes={**POWER_SETTINGS.wire_labels.prefixes, "WIRE CT+": "3+", "WIRE CT-": "3-"}))


def meter_layout(board, devices=None):
    result = fit_pages(board, METER_SETTINGS, meter_catalog(), devices or meter_devices())
    return result, [p for p in result.pages if not p.placed_sections]


def test_a_pin_wired_meter_is_a_24v_load_on_its_own_fuse():
    result, pages = meter_layout(lineup_with_a_meter())
    page = pages[0]
    meter = placed(page, "TEST_REV2")[0]
    assert meter.attributes == {"NAME": "PM-1"}
    assert [f.attributes["FUSE_NAME"] for f in placed(page, "TEST_FD")] == ["FD-1", "FD-2"]    # trip unit, meter
    mx, my = meter.position
    # Its 24 V wires end on its 24 V pins.
    ends = {w.end for w in page.parts.wires} | {w.start for w in page.parts.wires}
    assert (mx, my - 2.5) in {w.end for w in page.parts.wires if w.layer == "WIRE 24+"} | \
           {w.start for w in page.parts.wires if w.layer == "WIRE 24+"}
    assert any(at_point(e, (mx, my - 7.5)) for e in ends)


def test_the_meters_fuse_lies_to_its_left_with_phase_a_straight_into_its_pin():
    result, pages = meter_layout(lineup_with_a_meter())
    page = pages[0]
    mx, my = placed(page, "TEST_REV2")[0].position
    fuse = [b for b in placed(page, "TEST_FUSE") if b.label == "FA-2"][0]
    assert fuse.visibility == LYING
    # A: one straight wire from the fuse's load side into V1.
    a = [w for w in page.parts.wires if w.layer == "WIRE A" and w.end == (mx, my - 27.5)]
    assert len(a) == 1 and a[0].start[1] == my - 27.5 and a[0].start[0] == fuse.position[0] + 7.0
    # B into VN and C into V3, each turning in its own lane (C's to the right of B's).
    b_up = [w for w in page.parts.wires if w.layer == "WIRE B" and w.start[0] == w.end[0]]
    c_up = [w for w in page.parts.wires if w.layer == "WIRE C" and w.start[0] == w.end[0]]
    assert len(b_up) == 1 and len(c_up) == 1 and b_up[0].start[0] < c_up[0].start[0]
    assert any(w.end == (mx, my - 12.5) for w in page.parts.wires if w.layer == "WIRE B")
    assert any(w.end == (mx, my - 17.5) for w in page.parts.wires if w.layer == "WIRE C")


def test_ct_wires_come_from_the_shorting_kit_through_tildes_and_a_bracket():
    result, pages = meter_layout(lineup_with_a_meter())
    page = pages[0]
    mx, my = placed(page, "TEST_REV2")[0].position
    stubs = {w.label: w for w in page.parts.wires if w.layer in ("WIRE CT+", "WIRE CT-")}
    assert sorted(stubs) == ["3+001", "3+002", "3+003", "3-001", "3-002", "3-003"]
    # Each a stub from its pin out to the left, stub_length long.
    assert stubs["3+001"].start == (mx, my - 32.5) and stubs["3+001"].end == (mx - 8.0, my - 32.5)
    brackets = [b.attributes for b in placed(page, "TEST_BRACKET")]
    assert {"VERTICAL_LABLE": "FROM STB-1 SHEET 1"} in brackets


def test_the_ct_bracket_stretches_so_its_grip_lines_up_with_the_outer_wires():
    # Sammy, 2026-11-17. The six CT wires run 25 from top to bottom: half of that is 12.5,
    # 7.5 more than the grip's 5 at rest, so the stretch goes from 10 to 17.5 and the bracket
    # grows 7.5 at each end, still centred on the wires.
    result, pages = meter_layout(lineup_with_a_meter())
    page = pages[0]
    mx, my = placed(page, "TEST_REV2")[0].position
    ct = next(b for b in placed(page, "TEST_BRACKET") if b.attributes == {"VERTICAL_LABLE": "FROM STB-1 SHEET 1"})
    assert ct.distances == {"Distance1": 17.5}
    assert ct.position[1] == my - 45.0                  # the middle of I1+ (-32.5) and I3- (-57.5)
    assert (ct.extents[1], ct.extents[3]) == (-13.5, 13.5)


def test_a_bracket_on_three_wires_5_apart_is_left_as_drawn():
    # Three phases 5 apart: the grip is already on the outer wire, so the stretch isn't set.
    # A meter's voltage FROM another section lands on VN, V3 and V1 (15 apart): 12.5.
    from src.layout.device_pages import Unit, _Builder
    builder = _Builder(lineup_with_a_meter(), POWER_SETTINGS, meter_devices(), meter_catalog(), {}, [])
    layers = {"A": "WIRE A", "B": "WIRE B", "C": "WIRE C"}

    def bracket_on(points):
        unit = Unit(1)
        builder._pin_bracket(unit, points, layers, {}, "FROM FA-1 SHEET 4", "left")
        return next(b for b in unit.blocks if b.block == "TEST_BRACKET")

    assert bracket_on({"A": (0.0, 0.0), "B": (0.0, -5.0), "C": (0.0, -10.0)}).distances == {}
    assert bracket_on({"A": (0.0, -27.5), "B": (0.0, -12.5), "C": (0.0, -17.5)}).distances == {"Distance1": 12.5}


def test_without_a_supply_the_meter_is_drawn_on_its_own_and_unpowered():
    result, pages = meter_layout(lineup_with_a_meter(supply=False))
    page = pages[0]
    assert placed(page, "TEST_REV2") and not any(w.layer.startswith("WIRE 24") for w in page.parts.wires)


# --- The 24 V ladder (Sammy, 2026-11-17; src/layout/power_ladder.py) -----------------------

def crossings_on(page, layers=("WIRE 24+", "WIRE 24-")):
    """[(across label, upright label)] where two wire pieces of different runs cross (not
    where one ends on the other)."""
    pieces = [w for w in page.parts.wires if w.layer in layers]
    across = [w for w in pieces if abs(w.start[1] - w.end[1]) < 1e-6]
    upright = [w for w in pieces if abs(w.start[0] - w.end[0]) < 1e-6]
    found = []
    for a in across:
        x0, x1, y = min(a.start[0], a.end[0]), max(a.start[0], a.end[0]), a.start[1]
        for u in upright:
            y0, y1, x = min(u.start[1], u.end[1]), max(u.start[1], u.end[1]), u.start[0]
            if (a.layer, a.label) != (u.layer, u.label) and x0 + 1e-6 < x < x1 - 1e-6 and y0 + 1e-6 < y < y1 - 1e-6:
                found.append((a.label, u.label))
    return found


def busy_lineup():
    """Four sections, a 3WA main in each; the supply and the Ethernet switch in section 1, a
    COM800 (for two COM060s) in section 2 and another (for one) in section 3."""
    from src.model.section_contents import GroupMounted, SingleLevel, TwinLevel
    board = lineup_of(4, 1, set())
    board.sections[0].contents.ethernet_switch = True
    board.sections[1].contents.below = GroupMounted(levels=[TwinLevel(
        left=Breaker("52-F1", comms_module="Siemens COM060"), right=Breaker("52-F2", comms_module="Siemens COM060"))])
    board.sections[2].contents.below = GroupMounted(levels=[SingleLevel(Breaker("52-F3", comms_module="Siemens COM060"))])
    return board


def test_no_24v_wire_crosses_another():
    # Sammy, 2026-11-17: wires don't cross unless they have to; with the ladder none has to here.
    with_switches = lineup_of(3, 1, set())
    with_switches.sections[0].contents.ethernet_switch = True
    for board in (with_switches, lineup_of(3, 2, set()), lineup_of(3, 3, set())):
        result, pages = power_layout(board)
        assert [crossings_on(page) for page in pages] == [[] for _ in pages]


def test_a_wire_ending_where_the_trip_units_branch_and_go_on_crosses_their_branch_once():
    # The one crossing the ladder can't avoid: the trip units' wire branches in every
    # section and goes on, so a wire that passes one such section and ends in the next has
    # to cross the branch down to a trip unit once. Here the two COM800s' (sections 2 and 3):
    # two crossings in all, one each.
    result, pages = power_layout(busy_lineup())
    found = [c for page in pages for c in crossings_on(page)]
    assert len(found) == 2


def test_the_devices_stand_in_a_row_in_row_order_tops_lined_up():
    # Meters, the Ethernet switch, each COM800 with its COM060s next to it, the trip units.
    result, pages = power_layout(busy_lineup())
    section_2 = pages[1]
    row = sorted(section_2.parts.placeholders, key=lambda p: p.left_x)
    assert [p.text for p in row] == ["COM800-1", "52-F1\nSiemens COM060", "52-F2\nSiemens COM060",
                                     "52-M2 TRIP UNIT"]
    assert len({p.top_y for p in row}) == 1
    section_1 = pages[0]
    assert [p.text for p in sorted(section_1.parts.placeholders, key=lambda p: p.left_x)
            if not p.text.startswith("FD-")] == ["ETHERNET SWITCH", "52-M1 TRIP UNIT"]


def test_the_fuse_column_follows_where_the_wires_go():
    # Top down: the wires out through the right split (the farthest next stop first), then
    # the section's own devices, the one furthest right first (Sammy, 2026-11-17).
    plan = plan_for(busy_lineup(), 1)
    by_fuse = {fuse: [load.name for load in next(c for c in plan.circuits if c.key == key).loads]
               for fuse, key in plan.fuses}
    assert by_fuse == {"FD-1": ["COM800-2"], "FD-2": ["TU-1", "TU-2", "TU-3", "TU-4"], "FD-3": ["COM800-1"],
                       "FD-4": ["ES-1"]}


def test_the_split_pins_put_the_farthest_next_stop_on_top_and_the_minus_last():
    plan = plan_for(busy_lineup(), 1)
    # Into section 2: section 3's COM800's + (next stop 3) over the trip units' (next stop 2,
    # and it goes on) over section 2's COM800's (2, ends there), then the -.
    assert plan.boundary_keys(1) == ["+FD-1", "+FD-2", "+FD-3", "-"]
    # Into section 3: both stop there; the trip units' goes on, so it comes first.
    assert plan.boundary_keys(2) == ["+FD-2", "+FD-1", "-"]
    assert plan.boundary_keys(3) == ["+FD-2", "-"]


def test_a_ladder_wider_than_a_page_carries_on_with_one_bracket_each_side():
    # Sammy, 2026-11-17 (option C): every wire that carries on ends in one bracket spanning the
    # side and picks up from one on the next page, no tildes; the splits stay at the ends.
    board = lineup_of(2, 1, set())
    board.sections[0].contents.ethernet_switch = True
    narrow = replace(POWER_SETTINGS, drawable_width=230.0)
    result = fit_pages(board, narrow, power_catalog(), power_devices())
    pages = [p for p in result.pages if not p.placed_sections]
    section_1 = [p for p in pages if p.parts.title.endswith("SECTION 1")]
    assert len(section_1) == 2
    first, second = section_1
    to = [b for b in placed(first, "TEST_BRACKET") if b.attributes["VERTICAL_LABLE"].startswith("TO ")]
    back = [b for b in placed(second, "TEST_BRACKET") if b.attributes["VERTICAL_LABLE"].startswith("FROM ")]
    assert len(to) == 1 and len(back) == 1
    assert to[0].attributes == {"VERTICAL_LABLE": f"TO SHEET {second.number}"}
    assert back[0].attributes == {"VERTICAL_LABLE": f"FROM SHEET {first.number}"} and back[0].flipped
    assert not placed(first, "TEST_TILDE") and not placed(second, "TEST_TILDE")
    # The same wires on both sides of the break, by number.
    cut_x = to[0].position[0] - narrow.bus_break.bracket_gap
    out = sorted(w.label for w in first.parts.wires if abs(max(w.start[0], w.end[0]) - cut_x) < 1e-6
                 and w.start[1] == w.end[1])
    back_x = back[0].position[0] + narrow.bus_break.bracket_gap
    into = sorted(w.label for w in second.parts.wires if abs(min(w.start[0], w.end[0]) - back_x) < 1e-6
                  and w.start[1] == w.end[1])
    assert out == into and len(out) >= 2
    # The bracket spans them all: stretched so its grip is on the outer ones.
    ys = [w.start[1] for w in first.parts.wires if abs(max(w.start[0], w.end[0]) - cut_x) < 1e-6
          and w.start[1] == w.end[1]]
    half = (max(ys) - min(ys)) / 2
    assert to[0].distances == {"Distance1": 10.0 + half - 5.0}
    # The split carrying the + and - on to section 2 is on the second page.
    assert names_on(second, "TEST_SSM") == ["1SSM-1"] and not names_on(first, "TEST_SSM")
    assert all(crossings_on(p) == [] for p in section_1)


# --- Ground (Sammy, 2026-11-17) -----------------------------------------------------------

from src.model.devices import GroundSettings  # noqa: E402

GROUND = GroundSettings("{section}TBG", "WIRE G", ("G",), "TO GROUND BUS", "TO {strip}", "FROM {device}", 12.0,
                        strip_rotation=-90.0)
GROUND_SETTINGS = replace(POWER_SETTINGS, wire_labels=replace(
    POWER_SETTINGS.wire_labels, prefixes={**POWER_SETTINGS.wire_labels.prefixes, "WIRE G": "G"}))


def ground_layout(board):
    """The 24 V test lineup with the power supply's ground pin G (as on 3P_PWR_SUP) and the
    ground settings."""
    catalog = power_catalog()
    supply = catalog["TEST_PS"]
    catalog["TEST_PS"] = replace(supply, markers={**supply.markers, "G": (0.5, -27.5)})
    result = fit_pages(board, GROUND_SETTINGS, catalog, replace(power_devices(), ground=GROUND))
    return result, [p for p in result.pages if not p.placed_sections]


def test_the_ground_strip_takes_the_supplys_ground_and_sends_one_wire_to_the_ground_bus():
    # As in NTT-013628 (PS ground G002 -> TB1-G -> G001 TO GROUND BUS), named 1TBG, under
    # the supply, left of the - terminals; its blocks turned right (Sammy, 2026-11-23).
    result, pages = ground_layout(lineup_of(2, 1, set()))
    page = pages[0]
    assert "1TBG" in [t.text for t in page.parts.texts]
    strip = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TBG")]
    assert len(strip) == 1
    terminal = strip[0]
    assert terminal.rotation == -90.0
    sx, sy = placed(page, "TEST_PS")[0].position
    # G002: out of the supply's ground pin, down into a point facing up: 2_LEFT (-3.0, 1.5)
    # turned right is (1.5, 3.0) (point 1 is taken by the wire to the ground bus).
    g002 = [w for w in page.parts.wires if w.label == "G002"]
    assert (sx + 0.5, sy - 27.5) in {w.start for w in g002}
    assert (terminal.position[0] + 1.5, terminal.position[1] + 3.0) in {w.end for w in g002}
    # G001: out on the left, a tilde, the bracket TO GROUND BUS.
    g001 = [w for w in page.parts.wires if w.label == "G001"]
    assert len(g001) == 1 and g001[0].end[0] < g001[0].start[0]
    assert {"VERTICAL_LABLE": "TO GROUND BUS"} in [b.attributes for b in placed(page, "TEST_BRACKET")]
    assert any(at_point(b.position, g001[0].end) for b in placed(page, "TEST_WIRE_TILDE"))
    minus = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TB24-")]
    assert terminal.position[0] < min(t.position[0] for t in minus)
    assert crossings_on(page, layers=("WIRE 24+", "WIRE 24-", "WIRE G")) == []


def test_every_other_device_with_a_ground_pin_is_wired_by_reference_with_tildes():
    # Sammy, 2026-11-17: a stub with a tilde that says TO 1TBG, the same idea as a wire
    # through a shipping split; on the strip, the same wire number to a tilde naming it.
    board = lineup_of(2, 1, set())
    board.sections[1].contents.power_supplies.append(PowerSupply())     # PS-2, drawn but not feeding
    result, pages = ground_layout(board)
    section_1, section_2 = pages[0], pages[1]
    stub = [w for w in section_2.parts.wires if w.label == "G003"]
    assert len(stub) == 1 and stub[0].end[0] < stub[0].start[0]          # out to the left
    assert [b.attributes["TEXT_H"] for b in placed(section_2, "TEST_WIRE_TILDE")
            if any(at_point(b.position, w.end) for w in stub)] == ["TO 1TBG"]
    # On the strip (under the supply, its blocks turned right, Sammy 2026-11-23): straight
    # down to an upright tilde flipped up-down, its text under it.
    on_strip = [w for w in section_1.parts.wires if w.label == "G003"]
    assert len(on_strip) == 1
    down = on_strip[0]
    assert down.start[0] == down.end[0] and down.end[1] < down.start[1]
    tilde = [b for b in placed(section_1, "TEST_WIRE_TILDE") if at_point(b.position, down.end)]
    assert len(tilde) == 1 and tilde[0].visibility == "VERTICAL" and tilde[0].flip_parameter == "Flip state2"
    assert tilde[0].attributes["TEXT_V"] == "FROM PS-2"


def test_the_ground_strip_is_there_whenever_there_is_a_power_supply():
    # Sammy, 2026-11-19: better to add it than not, even with nothing else to connect.
    board = Switchboard("Test", [Section(SectionContents(power_supplies=[PowerSupply()]))])
    result, pages = ground_layout(board)
    page = pages[0]
    assert "1TBG" in [t.text for t in page.parts.texts]
    assert sorted({w.label for w in page.parts.wires if w.layer == "WIRE G"}) == ["G001", "G002"]


def test_the_meters_digital_ground_goes_to_the_strip_by_reference():
    # Sammy, 2026-11-19: the UMG 801's ground is its DIGITAL_GND for now; a tilde with a
    # label at each end, no wire across.
    catalog = meter_catalog()
    meter = catalog["TEST_REV2"]
    catalog["TEST_REV2"] = replace(meter, markers={**meter.markers, "DIGITAL_GND": (0.0, -72.5)})
    supply = catalog["TEST_PS"]
    catalog["TEST_PS"] = replace(supply, markers={**supply.markers, "G": (0.5, -27.5)})
    ground = replace(GROUND, pin_markers=("G", "DIGITAL_GND"))
    settings = replace(METER_SETTINGS, wire_labels=replace(
        METER_SETTINGS.wire_labels, prefixes={**METER_SETTINGS.wire_labels.prefixes, "WIRE G": "G"}))
    result = fit_pages(lineup_with_a_meter(), settings, catalog, replace(meter_devices(), ground=ground))
    page = [p for p in result.pages if not p.placed_sections][0]
    mx, my = placed(page, "TEST_REV2")[0].position
    stub = [w for w in page.parts.wires if w.label == "G003"]
    assert len(stub) == 2                               # the meter's, and the strip's straight down
    at_meter = next(w for w in stub if w.start == (mx, my - 72.5))
    assert at_meter.end == (mx - 12.0, my - 72.5)
    texts = {b.attributes.get("TEXT_H") or b.attributes.get("TEXT_V") for b in placed(page, "TEST_WIRE_TILDE")
             if any(at_point(b.position, w.end) for w in stub)}
    assert texts == {"TO 1TBG", "FROM PM-1"}


# --- The Ethernet switch, sized for what plugs into it (Sammy, 2026-11-19) ----------------

from src.model.devices import EthernetConnection, EthernetSwitchSettings, ethernet_connections  # noqa: E402

SWITCH = EthernetSwitchSettings(
    sizes=((5, "TEST_ES5"), (8, "TEST_ES8")), name_attribute="NAME", supply_pins={"+": "24V+", "-": "24V-"},
    port_marker="PORT_{port}", customer_connection="CUSTOMER CONNECTION", customer_port=1, spare_ports=1,
    cable_label="E-{number:03d}", to_device_label="TO {device} SECTION {section}",
    to_switch_label="TO {switch} SECTION {section}", stub_length=12.0, wire_layer="WIRE E", layer="0")


def switch_block(name, ports):
    """A test switch: 24 V on the left edge (+ top, - bottom), its ports down the right edge."""
    height = 5.0 * (ports + 1)
    markers = {"24V+": (0.0, -2.5), "24V-": (0.0, -height + 2.5),
               **{f"PORT_{n}": (20.0, -2.5 - 5.0 * n) for n in range(1, ports + 1)}}
    return BlockInfo(name, (), (), extents=(0.0, -height, 20.0, 0.0), markers=markers)


def switch_layout(board, with_blocks=True):
    catalog = power_catalog()
    if with_blocks:
        catalog.update({"TEST_ES5": switch_block("TEST_ES5", 5), "TEST_ES8": switch_block("TEST_ES8", 8)})
    result = fit_pages(board, POWER_SETTINGS, catalog, replace(power_devices(), ethernet_switch=SWITCH))
    return result, [p for p in result.pages if not p.placed_sections]


def stub_ending_in(page, text):
    """The cable stubs whose tilde says `text`."""
    tildes = [b for b in placed(page, "TEST_WIRE_TILDE") if b.attributes.get("TEXT_H") == text]
    return [w for w in page.parts.wires if w.layer == "WIRE E" and any(at_point(t.position, w.end) for t in tildes)]


def test_what_plugs_into_the_switch_is_counted():
    from src.model.section_contents import GroupMounted, TwinLevel
    board = lineup_of(2, 1, {1})
    board.sections[1].contents.below = GroupMounted(levels=[TwinLevel(
        left=Breaker("52-F1", comms_module="Siemens COM060"), right=Breaker("52-F2"))])
    # 52-M1's COM190 (on its trip unit's box), the COM800 for 52-F1's COM060 (not the COM060).
    assert ethernet_connections(board) == [EthernetConnection("52-M1 COM190", 1, "TU-1"),
                                           EthernetConnection("COM800-1", 2, "COM800-1")]
    # Those, the customer's and one spare.
    assert SWITCH.block_for(3) == (5, "TEST_ES5") and SWITCH.block_for(5) == (8, "TEST_ES8")
    assert SWITCH.block_for(20) == (8, "TEST_ES8")


def test_the_switch_is_the_smallest_block_with_a_port_for_each_the_customer_on_port_1():
    board = lineup_of(5, 1, {1, 2, 3, 4, 5})               # five COM190s, the customer, a spare: 7
    board.sections[0].contents.ethernet_switch = True
    result, pages = switch_layout(board)
    page = pages[0]
    switch = placed(page, "TEST_ES8")
    assert len(switch) == 1 and switch[0].attributes == {"NAME": "ES-1"} and not placed(page, "TEST_ES5")
    x, y = switch[0].position
    ends = {w.end for w in page.parts.wires} | {w.start for w in page.parts.wires}
    assert (x, y - 2.5) in ends and (x, y - 42.5) in ends            # its 24 V on its pins
    customer = stub_ending_in(page, "CUSTOMER CONNECTION")
    assert len(customer) == 1 and customer[0].start == (x + 20.0, y - 7.5)      # PORT_1
    assert customer[0].end == (x + 32.0, y - 7.5) and customer[0].label == "E-001"
    # The COM190s on ports 2-6, in lineup order; port 7 the spare, port 8 free.
    to_devices = [w for w in page.parts.wires if w.layer == "WIRE E" and w.start[0] == x + 20.0]
    assert sorted((w.start[1], w.label) for w in to_devices) == sorted(
        [(y - 7.5 - 5.0 * n, f"E-{n + 1:03d}") for n in range(6)])
    assert len(stub_ending_in(page, "TO 52-M1 COM190 SECTION 1")) == 1
    assert not [p for p in page.parts.placeholders if p.text.startswith("ETHERNET SWITCH")]
    assert crossings_on(page) == []


def test_both_ends_of_a_cable_show_with_its_number():
    # Sammy, 2026-11-19: at the switch "TO 52-M2 COM190 SECTION 2"; at the trip unit's box
    # (the COM190 is part of it), on its right edge half way down, "TO ES-1 SECTION 1".
    board = lineup_of(2, 1, {2})
    board.sections[0].contents.ethernet_switch = True
    result, pages = switch_layout(board)
    at_switch = stub_ending_in(pages[0], "TO 52-M2 COM190 SECTION 2")
    at_device = stub_ending_in(pages[1], "TO ES-1 SECTION 1")
    assert len(at_switch) == 1 and len(at_device) == 1 and at_switch[0].label == at_device[0].label == "E-002"
    box = next(p for p in pages[1].parts.placeholders if p.text.startswith("52-M2 TRIP UNIT"))
    assert at_device[0].start == (box.right_x, (box.top_y + box.bottom_y) / 2)
    assert at_device[0].end[0] == box.right_x + 12.0


def test_until_the_switch_block_has_its_24v_markers_it_is_a_box_naming_its_size():
    board = lineup_of(1, 1, {1})
    board.sections[0].contents.ethernet_switch = True
    result, pages = switch_layout(board, with_blocks=False)
    page = pages[0]
    assert "ETHERNET SWITCH\n5 PORT" in [p.text for p in page.parts.placeholders]
    assert any("The Ethernet switch is a box until TEST_ES5 has its 24 V markers" in w for w in result.warnings)
    # Its cables come off its right edge, a port every 5 down: the customer's first.
    box = next(p for p in page.parts.placeholders if p.text.startswith("ETHERNET SWITCH"))
    assert [w.start for w in stub_ending_in(page, "CUSTOMER CONNECTION")] == [(box.right_x, box.top_y - 5.0)]


def test_one_switch_per_lineup_for_now():
    # Sammy, 2026-11-19: with two sections ticked, the first's switch is drawn, with a warning.
    board = lineup_of(3, 1, {1})
    board.sections[0].contents.ethernet_switch = True
    board.sections[2].contents.ethernet_switch = True
    result, pages = switch_layout(board)
    assert sum(len(placed(p, "TEST_ES5")) for p in pages) == 1 and placed(pages[0], "TEST_ES5")
    assert any("One Ethernet switch per lineup for now: ES-1 is drawn in section 1" in w for w in result.warnings)


def test_the_meters_end_of_its_cable_leaves_its_ethernet_pin_under_the_remote_display():
    # Sammy, 2026-11-19: USB moved above the RJ45 ports, so the cable goes out to the right
    # under the remote display: a stub from RJ45A ending in a tilde TO ES-1.
    model = replace(REV2, ethernet_pin="RJ45A")
    catalog = {**meter_catalog(), "TEST_ES5": switch_block("TEST_ES5", 5)}
    rev2 = catalog["TEST_REV2"]
    catalog["TEST_REV2"] = replace(rev2, markers={**rev2.markers, "USB": (14.5, -8.0), "RJ45A": (14.5, -14.0)})
    devices = replace(meter_devices(), power_meters={"Janitza UMG 801": model}, ethernet_switch=SWITCH)
    board = lineup_with_a_meter()
    board.sections[0].contents.ethernet_switch = True
    result = fit_pages(board, METER_SETTINGS, catalog, devices)
    page = [p for p in result.pages if not p.placed_sections][0]
    mx, my = placed(page, "TEST_REV2")[0].position
    cable = stub_ending_in(page, "TO ES-1 SECTION 1")
    assert [(w.start, w.end) for w in cable] == [((mx + 14.5, my - 14.0), (mx + 26.5, my - 14.0))]
    at_switch = stub_ending_in(page, "TO PM-1 SECTION 1")
    assert len(at_switch) == 1 and at_switch[0].label == cable[0].label
    # Both ends are on this page: each stub carries its own label.
    assert [label.text for label in page.parts.wire_labels].count(cable[0].label) == 2
    assert not any("Ethernet switch" in w and "boxes" in w for w in result.warnings)


# --- A fuse's phases on their way to a meter in another section (Sammy, 2026-11-19) -------

def meter_two_sections_on():
    """Three sections, the supply in 1; PM-1 in section 3, its voltage tapped in section 1
    (FA-2); 52-M2's COM190 puts a trip unit in section 2's row."""
    board = lineup_of(3, 1, {2})
    board.sections[2].contents.power_meters.append(PowerMeter("Janitza UMG 801", id="m1"))
    board.sections[0].contents.above.feed.voltage_taps.append(VoltageTap("m1", {"CURRENT": "1A"}))
    return board


def tildes_on_phase_wires(page):
    """[(tilde text, the wire's layer)] for the tildes on the ends of the phase wires."""
    phase = [w for w in page.parts.wires if w.layer in ("WIRE A", "WIRE B", "WIRE C")]
    return sorted((t.attributes.get("TEXT_H", ""), w.layer) for t in placed(page, "TEST_WIRE_TILDE")
                  for w in phase if at_point(t.position, w.end))


def test_the_phases_go_straight_into_their_meter_with_no_tildes():
    result, pages = meter_layout(meter_two_sections_on())
    section_3 = next(p for p in pages if placed(p, "TEST_REV2"))
    assert section_3.parts.title.endswith("SECTION 3")
    mx, my = placed(section_3, "TEST_REV2")[0].position
    # No FROM bracket and no tilde: each phase runs from 3SSM-1 into its pin.
    assert not any("FA-2" in str(b.attributes) for b in placed(section_3, "TEST_BRACKET"))
    assert tildes_on_phase_wires(section_3) == []
    into = {w.layer for w in section_3.parts.wires if w.end in {(mx, my - 27.5), (mx, my - 12.5), (mx, my - 17.5)}}
    assert into == {"WIRE A", "WIRE B", "WIRE C"}
    male = [b for b in section_3.parts.blocks if b.block == "TEST_SSM"][0]
    starts = {w.layer for w in section_3.parts.wires if w.layer in into and abs(w.start[0] - (male.position[0] + 7.0)) < 1e-6}
    assert starts == into
    # The only crossings are A's over B and C (A goes to the meter's lowest voltage pin).
    assert sorted(crossings_on(section_3, ("WIRE A", "WIRE B", "WIRE C"))) == [("4A004", "4B004"), ("4A004", "4C004")]


def test_passing_a_section_with_devices_the_phases_end_in_tildes_naming_the_other_split():
    # A wire drawn through would cross the 24 V coming in above and below it, so each pin
    # gets a stub and a tilde: TO the split it leaves by, FROM the split it came in by.
    result, pages = meter_layout(meter_two_sections_on())
    section_2 = pages[1]
    assert tildes_on_phase_wires(section_2) == sorted(
        [("TO 2SSM-2", layer) for layer in ("WIRE A", "WIRE B", "WIRE C")]
        + [("FROM 2SSM-1", layer) for layer in ("WIRE A", "WIRE B", "WIRE C")])


def test_the_left_split_moves_so_phase_a_runs_straight_into_its_meter():
    # Sammy, 2026-11-20: no step in A's wire. The split, centred on the row, is nudged so
    # A's pin is level with V1.
    result, pages = meter_layout(meter_two_sections_on())
    section_3 = next(p for p in pages if placed(p, "TEST_REV2"))
    mx, my = placed(section_3, "TEST_REV2")[0].position
    a = [w for w in section_3.parts.wires if w.layer == "WIRE A"]
    assert {w.start[1] for w in a} | {w.end[1] for w in a} == {my - 27.5}


def test_a_supply_fed_from_the_left_takes_its_phases_straight_from_the_split():
    # Sammy, 2026-11-20: like a meter. The supply in section 2, its fuse in section 1; the
    # 24 V goes back left to section 1's trip unit through the same split.
    result, pages = power_layout(lineup_of(2, 2, {1}))
    section_2 = pages[1]
    sx, sy = placed(section_2, "TEST_PS")[0].position
    assert not any("FA-1" in str(b.attributes) for b in placed(section_2, "TEST_BRACKET"))
    assert tildes_on_phase_wires(section_2) == []
    for layer, pin_y in (("WIRE A", -5.0), ("WIRE B", -10.0), ("WIRE C", -15.0)):
        assert any(w.end == (sx + 0.5, sy + pin_y) for w in section_2.parts.wires if w.layer == layer)
    # L1-L3 run top to bottom like the split's pins: no crossings, A straight in.
    assert crossings_on(section_2, ("WIRE A", "WIRE B", "WIRE C", "WIRE 24+", "WIRE 24-")) == []
    assert {w.start[1] for w in section_2.parts.wires if w.layer == "WIRE A"} == {sy - 5.0}


def test_a_supply_that_doesnt_feed_the_24v_keeps_its_from_bracket():
    # No ladder draws it (no control power settings here), so its phases can't come straight in.
    result, pages = split_layout(lineup_of(3, 3, set()))
    labels = [b.attributes for b in placed(pages[2], "TEST_BRACKET")]
    assert {"VERTICAL_LABLE": "FROM FA-1 SHEET 2"} in labels


# --- Room for a tilde's text (Sammy, 2026-11-20) -------------------------------------------

from src.layout.device_units import tilde_text_box  # noqa: E402


def label_boxes(page):
    """[(text, box)] for every tilde with text on the page, its box where the text lies
    (lying: TEXT_H; upright: TEXT_V)."""
    boxes = []
    for t in placed(page, "TEST_WIRE_TILDE"):
        vertical = t.visibility == "VERTICAL"
        text = t.attributes.get("TEXT_V" if vertical else "TEXT_H", "")
        if text:
            left, bottom, right, top = tilde_text_box(text, TEST_SETTINGS.device_pages, t.flipped, vertical)
            boxes.append((text, (t.position[0] + left, t.position[1] + bottom,
                                 t.position[0] + right, t.position[1] + top)))
    return boxes


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_the_meters_and_the_switchs_labels_keep_clear_of_each_other_and_of_the_blocks():
    # Sammy, 2026-11-20: PM-1's "TO ES-1 SECTION 1" ran into the switch's labels, which now
    # sit on its left. Each tilde's size takes in its text, so the row keeps them apart.
    model = replace(REV2, ethernet_pin="RJ45A")
    catalog = {**meter_catalog(), "TEST_ES5": switch_block("TEST_ES5", 5)}
    rev2 = catalog["TEST_REV2"]
    catalog["TEST_REV2"] = replace(rev2, markers={**rev2.markers, "USB": (14.5, -8.0), "RJ45A": (14.5, -14.0)})
    devices = replace(meter_devices(), power_meters={"Janitza UMG 801": model}, ethernet_switch=SWITCH)
    board = lineup_with_a_meter()
    board.sections[0].contents.ethernet_switch = True
    result = fit_pages(board, METER_SETTINGS, catalog, devices)
    page = [p for p in result.pages if not p.placed_sections][0]
    boxes = label_boxes(page)
    assert {"TO ES-1 SECTION 1", "TO PM-1 SECTION 1", "CUSTOMER CONNECTION"} <= {text for text, _ in boxes}
    for i, (text, box) in enumerate(boxes):
        assert not [other for other, b in boxes[i + 1:] if overlap(box, b)], text
        blocks = [b for b in page.parts.blocks if b.block in ("TEST_REV2", "TEST_ES5", "TEST_PS")]
        assert not [b.block for b in blocks if overlap(box, (b.position[0] + b.extents[0], b.position[1] + b.extents[1],
                                                             b.position[0] + b.extents[2], b.position[1] + b.extents[3]))], text


def test_the_ground_strip_stands_under_the_supply_turned_its_wires_straight_down():
    # Sammy, 2026-11-20: the strip moves up under the power supply, into the room left of its
    # fuses. 2026-11-23: its blocks turned right, so every device's ground wire goes straight
    # down from its terminal (two per block, 2.5 apart) to an upright tilde, its text under it.
    board = lineup_of(2, 1, set())
    for _ in range(3):                                                  # PS-2, PS-3, PS-4
        board.sections[1].contents.power_supplies.append(PowerSupply())
    result, pages = ground_layout(board)
    page = pages[0]
    supply = placed(page, "TEST_PS")[0]
    strip = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TBG")]
    assert len(strip) == 2 and all(t.rotation == -90.0 for t in strip)
    assert max(t.position[1] + t.extents[3] for t in strip) <= supply.position[1] + supply.extents[1]
    fuses = placed(page, "TEST_FD")
    assert max(t.position[0] + t.extents[2] for t in strip) < min(f.position[0] for f in fuses)
    downs = sorted((w for w in page.parts.wires if w.layer == "WIRE G" and w.label in ("G003", "G004", "G005")),
                   key=lambda w: w.start[0])
    assert len(downs) == 3 and all(w.start[0] == w.end[0] and w.end[1] < w.start[1] for w in downs)
    assert len({w.end[1] for w in downs}) == 1                          # all end level
    assert [round(b.start[0] - a.start[0], 6) for a, b in zip(downs, downs[1:])] == [2.5, 2.5]
    texts = sorted(text for text, _ in label_boxes(page) if text.startswith("FROM PS"))
    assert texts == ["FROM PS-2", "FROM PS-3", "FROM PS-4"]             # one line each: 2.5 apart
    boxes = [box for _, box in label_boxes(page)]
    assert not [1 for i, a in enumerate(boxes) for b in boxes[i + 1:] if overlap(a, b)]
    assert crossings_on(page, layers=("WIRE 24+", "WIRE 24-", "WIRE G")) == []


# --- The supply and its fuses beside the + wires (Sammy, 2026-11-20) ------------------------

def new_crossings(page):
    """Crossings that involve a - or ground wire. (Two + wires can already cross when a fuse's
    terminal group feeds a device in its own section ahead of fuses for the split: 2026-11-23,
    open, not from the supply moving up.)"""
    return [c for c in crossings_on(page, layers=("WIRE 24+", "WIRE 24-", "WIRE G"))
            if not (c[0].startswith("2+") and c[1].startswith("2+"))]


def many_fuses(meters):
    """One section with the supply and two trip units' sections, and `meters` meters spread
    over sections 2 and 3: a fuse each, so the fuse column grows."""
    board = lineup_of(3, 1, set())
    for n in range(meters):
        board.sections[1 + n % 2].contents.power_meters.append(PowerMeter("Janitza UMG 801"))
    return board


def test_the_supply_and_its_fuses_stand_beside_the_plus_wires_the_first_running_straight_across():
    result, pages = meter_layout(many_fuses(3))
    page = pages[0]
    fuses = sorted(placed(page, "TEST_FD"), key=lambda f: -f.position[1])
    fx, fy = fuses[0].position
    load = (fx + 10.0, fy)                                      # FD-1's load side
    plus = [w for w in page.parts.wires if w.layer == "WIRE 24+"]
    first = [w for w in plus if at_point(w.start, load) or at_point(w.end, load)]
    assert len(first) == 1 and abs(first[0].start[1] - first[0].end[1]) < 1e-6      # straight across ...
    assert first[0].start[1] >= max(max(w.start[1], w.end[1]) for w in plus) - 1e-6    # ... along the top
    # The supply stands above the tops of the section's devices.
    supply = placed(page, "TEST_PS")[0]
    tops = [p.top_y for p in page.parts.placeholders if "TRIP UNIT" in p.text]
    assert supply.position[1] + supply.extents[3] > max(tops)
    assert new_crossings(page) == []


def test_the_minus_terminals_stand_right_of_the_fuses_the_supplys_minus_running_under_them():
    result, pages = meter_layout(many_fuses(3))
    page = pages[0]
    fuses = placed(page, "TEST_FD")
    minus = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TB24-")]
    assert min(t.position[0] + t.extents[0] for t in minus) > max(f.position[0] + f.extents[2] for f in fuses)
    lowest = min(f.position[1] + f.extents[1] for f in fuses)
    under = [w for w in page.parts.wires if w.label == "2-001" and abs(w.start[1] - w.end[1]) < 1e-6
             and w.start[1] < lowest]
    assert len(under) == 1


def test_when_the_fuses_reach_lower_than_the_minus_terminals_the_minus_comes_in_from_below():
    result, pages = meter_layout(many_fuses(8))
    page = pages[0]
    lowest = min(f.position[1] + f.extents[1] for f in placed(page, "TEST_FD"))
    minus = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TB24-")]
    bottom_block = min(minus, key=lambda t: t.position[1])
    assert bottom_block.position[1] > lowest                    # the fuses reach lower
    ends = {w.end for w in page.parts.wires if w.label == "2-001"} | {w.start for w in page.parts.wires if w.label == "2-001"}
    bx, by = bottom_block.position
    assert (bx - 5.0, by - 1.5) in ends or (bx + 5.0, by - 1.5) in ends      # 1_BOTTOM or 4_BOTTOM
    assert new_crossings(page) == []


def test_wires_passing_over_the_supply_keep_it_under_them():
    # The supply in section 2: section 1's trip unit takes its + over the supply to the split
    # on the left, so the supply moves up only as far as that wire lets it.
    board = lineup_of(3, 2, set())
    result, pages = power_layout(board)
    page = next(p for p in pages if placed(p, "TEST_PS"))
    supply = placed(page, "TEST_PS")[0]
    left, right = supply.position[0] + supply.extents[0], supply.position[0] + supply.extents[2]
    over = [w for w in page.parts.wires if w.layer == "WIRE 24+" and abs(w.start[1] - w.end[1]) < 1e-6
            and min(w.start[0], w.end[0]) < left and max(w.start[0], w.end[0]) > right]
    assert over
    assert supply.position[1] + supply.extents[3] < min(w.start[1] for w in over)
    assert crossings_on(page, layers=("WIRE 24+", "WIRE 24-", "WIRE G")) == []


def test_the_ground_strip_uses_all_four_connections_of_each_block_wires_going_up_too():
    # Sammy, 2026-11-23: 4 connections per terminal block; the points facing up take wires
    # too, straight up to a tilde with its text over it, the strip moved down to make room.
    board = lineup_of(2, 1, set())
    for _ in range(5):                                                  # PS-2 ... PS-6: 5 devices
        board.sections[1].contents.power_supplies.append(PowerSupply())
    result, pages = ground_layout(board)
    page = pages[0]
    supply = placed(page, "TEST_PS")[0]
    strip = [t for t in placed(page, "TEST_TB") if t.label.startswith("1TBG")]
    assert len(strip) == 2                          # 8 points: in, out to the bus, 4 down, 2 up
    wires = [w for w in page.parts.wires if w.layer == "WIRE G" and w.label in {f"G{n:03d}" for n in range(3, 8)}]
    assert len(wires) == 5 and all(w.start[0] == w.end[0] for w in wires)
    up = [w for w in wires if w.end[1] > w.start[1]]
    assert len(up) == 1
    tilde = next(b for b in placed(page, "TEST_WIRE_TILDE") if at_point(b.position, up[0].end))
    assert tilde.visibility == "VERTICAL" and not tilde.flipped and tilde.attributes["TEXT_V"] == "FROM PS-6"
    text_top = max(box[3] for text, box in label_boxes(page) if text == "FROM PS-6")
    assert text_top <= supply.position[1] + supply.extents[1] - TEST_SETTINGS.device_pages.ladder_zone_gap + 1e-6
    boxes = [box for _, box in label_boxes(page)]
    assert not [1 for i, a in enumerate(boxes) for b in boxes[i + 1:] if overlap(a, b)]
    assert crossings_on(page, layers=("WIRE 24+", "WIRE 24-", "WIRE G")) == []
