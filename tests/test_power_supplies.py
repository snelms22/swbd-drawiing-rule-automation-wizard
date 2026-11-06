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


def test_power_supplies_are_named_by_section_through_the_lineup():
    switchboard, supply, _ = lineup_with_a_supply()
    assert [(info.name, info.supply is supply) for info in power_supplies_in(switchboard)] == [
        ("PS-1-1", False), ("PS-2-2", True)]


def test_a_tap_can_feed_a_power_supply():
    switchboard, _, _ = lineup_with_a_supply()
    # Only the unfed PS-1-1 is reported; FA-2-1 feeding PS-2-2 is fine.
    assert device_problems(switchboard) == [
        'PS-1-1 (section 1): no voltage tap feeds it yet; pick it in a voltage tap\'s "Feeds" list.']


def test_a_tap_feeding_a_removed_device_is_reported():
    switchboard, _, _ = lineup_with_a_supply(tap_feeds="gone")
    assert "Section 2 above (feed of 52-M1): voltage tap FA-2-1 feeds a device that no longer exists." \
        in device_problems(switchboard)


def test_two_taps_on_one_power_supply_are_reported():
    switchboard, supply, _ = lineup_with_a_supply()
    switchboard.sections[1].contents.above.feed.voltage_taps.append(VoltageTap(feeds=supply.id))
    assert any("PS-2-2 is fed by more than one voltage tap (FA-2-1, FA-2-2)" in p
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
    assert devices_box.supplies_list.item(0).text().startswith("PS-1-1")
    # One field per block attribute, by its prompt; the number is the program's.
    tags = [devices_box.supply_attributes_form.itemAt(row, QFormLayout.FieldRole).widget().toolTip()
            for row in range(devices_box.supply_attributes_form.rowCount())]
    assert "Attribute RATING" in tags and "Attribute PS_DRW_NUM" not in tags

    editor.load(section, 1)                          # the taps editor sees the new supply
    taps_editor = editor.above_editor.taps_editor
    taps_editor._add_tap()
    taps_editor.feeds_combo.setCurrentIndex(taps_editor.feeds_combo.findData(supply.id))
    assert main.feed.voltage_taps[0].feeds == supply.id
    assert taps_editor.taps_list.item(0).text() == "FA-1-1   to PS-1-1   (line side)"
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


def ps_page(switchboard, devices=None):
    result = fit_pages(switchboard, TEST_SETTINGS, PS_CATALOG, devices or ps_devices())
    pages = [p for p in result.pages if not p.placed_sections]
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
    assert supply.attributes == {"RATING": "240W-10A", "PS_NO": "1-1"}
    assert fuse.visibility == LYING and fuse.attributes == {"CURRENT": "3A", "FUSE_NO": "1-1"}
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
    assert bracket.attributes == {"VERTICAL_LABLE": "FROM ES_01"} and bracket.visibility == "VERTICAL BRACKET"
    assert bracket.flipped and bracket.flip_parameter == "Flip state1"
    assert bracket.position == (fuse.position[0] - 7.0 - 8.0 - 2.0, sy - 10.0)
    # The 3-line tap points at the device page its fuse is on.
    tap = [b for b in result.pages[0].parts.blocks if b.block == "TEST_TAP"][0]
    assert tap.attributes["TO_SHEET"] == "2"


def test_a_power_supply_fed_from_another_section():
    result, page = ps_page(lineup(2))
    labels = sorted(next(iter(b.attributes.values())) for b in placed(page, "TEST_BRACKET"))
    # The fuse, alone in section 1: FROM the 3-line, TO the supply. The supply: FROM the fuse.
    assert labels == ["FROM ES_01", "FROM FA-1-1 SHEET 2", "TO PS-2-1 SHEET 2"]
    assert placed(page, "TEST_FUSE")[0].visibility == UP
    assert [n.lines[0] for n in page.parts.notes] == ["SECTION 1", "SECTION 2"]


def test_a_power_supply_with_no_tap_is_drawn_alone():
    switchboard = lineup(1)
    switchboard.sections[0].contents.above.feed.voltage_taps.clear()
    _, page = ps_page(switchboard)
    assert len(placed(page, "TEST_PS")) == 1
    assert not placed(page, "TEST_FUSE") and not page.parts.wires


def test_without_a_lying_fuse_state_the_fuse_goes_to_the_supply_by_bracket():
    _, page = ps_page(lineup(1), ps_devices(lying=False))
    labels = sorted(next(iter(b.attributes.values())) for b in placed(page, "TEST_BRACKET"))
    assert labels == ["FROM ES_01", "FROM FA-1-1 SHEET 2", "TO PS-1-1 SHEET 2"]


def test_the_power_supply_comes_first_in_its_section():
    """Top left, before the meters (Sammy, 2026-11-05): it powers what comes after it."""
    switchboard = lineup(1)
    switchboard.sections[0].contents.power_meters.append(PowerMeter(""))     # drawn as a box
    _, page = ps_page(switchboard)
    supply = placed(page, "TEST_PS")[0]
    meter_box = page.parts.placeholders[0]
    assert supply.position[1] + 11.5 > meter_box.top_y          # the supply is above the meter
