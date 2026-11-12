"""Tests for the device pages (decision 2026-10-23; src/layout/device_pages.py).

Test blocks are shaped like Sammy's: a meter with voltage terminals on top (VN, V3, V1 at
x -44.5 / -39.5 / -29.5, y 14) and current inputs underneath (I1+ ... at y -14); input
blocks that land on them; a fuse standing up with its line side at y 12.5 and its load
side at y -1.5 (A, B, C at x -19.5 / -14.5 / -9.5).
"""
from dataclasses import replace

from src.layout.block_catalog import BlockInfo
from src.layout.page_fitter import fit_pages
from src.model.devices import DeviceSettings, FuseSettings, InputBlock, MeterModel, RemoteDisplaySettings
from src.model.section_contents import (
    Breaker, CurrentTransformers, GroupMounted, IncomingFeed, MainBreaker, PowerMeter, SectionContents,
    SingleLevel, TwinLevel, VoltageTap,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS

METER_MARKERS = {"VN": (-44.5, 14.0), "V3": (-39.5, 14.0), "V2": (-34.5, 14.0), "V1": (-29.5, 14.0),
                 "USB": (-46.5, -6.0),
                 "I1+": (-44.0, -14.0), "I1-": (-39.0, -14.0), "I2+": (-34.0, -14.0),
                 "I2-": (-29.0, -14.0), "I3+": (-24.0, -14.0), "I3-": (-19.0, -14.0)}
FUSE_STATE = "3-POLE VERTICAL"
CATALOG = {
    **TEST_CATALOG,
    "TEST_METER": BlockInfo("TEST_METER", (), (), extents=(-47.0, -14.0, 55.0, 23.0), markers=METER_MARKERS),
    "TEST_V_IN": BlockInfo("TEST_V_IN", (), (), extents=(-2.0, 0.0, 20.0, 14.0),
                           markers={"V_B": (0.0, 0.0), "V_C": (5.0, 0.0), "V_A": (15.0, 0.0)}),
    "TEST_RD": BlockInfo("TEST_RD", (), (), extents=(0.0, 0.0, 15.0, 22.0), markers={"USB": (7.5, 0.5)}),
    "TEST_CT_IN": BlockInfo("TEST_CT_IN", (), (), extents=(-2.5, -15.0, 27.5, 0.0),
                            markers={"CT_A+": (0.0, 0.0), "CT_A-": (5.0, 0.0)}),
    "TEST_FUSE": BlockInfo("TEST_FUSE", (), (), extents=(-22.0, -15.0, 14.5, 13.0),
                           visibility_states=(FUSE_STATE,),
                           states={FUSE_STATE: {"markers": {}, "extents": (-22.0, -2.0, 14.5, 13.0)}},
                           markers={f"{p}_{side}": (x, y) for p, x in (("A", -19.5), ("B", -14.5), ("C", -9.5))
                                    for side, y in (("LINE", 12.5), ("LOAD", -1.5))}),
}
LAYERS = {"A": "WIRE A", "B": "WIRE B", "C": "WIRE C"}
DEVICES = DeviceSettings(
    comms_modules=[],
    power_meters={
        "Meter": MeterModel("Meter", "TEST_METER",
                            InputBlock("TEST_V_IN", {"V_A": "V1", "V_B": "VN", "V_C": "V3"}, "FA_NO", "FA_SHEET"),
                            (InputBlock("TEST_CT_IN", {"CT_A+": "I1+", "CT_A-": "I1-"}, "STB_NO", "STB_SHEET"),),
                            number_attribute="NO.", usb_marker="USB"),
        "Later": MeterModel("Later", "", None, ()),
    },
    fuse=FuseSettings("TEST_FUSE", FUSE_STATE, {p: f"{p}_LINE" for p in "ABC"},
                      {p: f"{p}_LOAD" for p in "ABC"}, "FUSE_NO", "0", LAYERS),
    remote_display=RemoteDisplaySettings("TEST_RD", "USB", "RD_NO", "0", "USB LINE"),
)


def main(tap_meter="m1", cts_meter="m1", label="52-M1"):
    return MainBreaker(Breaker(label), cts=CurrentTransformers(cts_meter, "4000:5A"),
                       feed=IncomingFeed(voltage_taps=[VoltageTap(tap_meter, {"CURRENT": "1A"})]))


def layout(*contents):
    return fit_pages(Switchboard("Test", [Section(c) for c in contents]), TEST_SETTINGS, CATALOG, DEVICES)


def device_pages_of(result):
    """The device pages (the pages after the 3-line), in order."""
    return [p for p in result.pages if not p.placed_sections]


def device_page(result):
    pages = device_pages_of(result)
    assert len(pages) == 1
    return pages[0]


def all_blocks(pages, name):
    return [b for page in pages for b in blocks(page, name)]


def blocks(page, name):
    return [b for b in page.parts.blocks if b.block == name]


def test_a_fuse_and_its_meter_in_the_same_section_are_wired():
    result = layout(SectionContents(above=main(), power_meters=[PowerMeter("Meter", id="m1")]))
    page = device_page(result)
    assert page.number == 2                                   # after the one 3-line page
    meter, fuse = blocks(page, "TEST_METER")[0], blocks(page, "TEST_FUSE")[0]
    assert meter.attributes == {"NO.": "1"}
    assert fuse.attributes == {"CURRENT": "1A", "FUSE_NO": "1"} and fuse.visibility == FUSE_STATE
    assert not blocks(page, "TEST_V_IN")                      # wired, so no voltage input block
    # One wire run per phase, on its own layer, ending on the meter's terminal for it.
    mx, my = meter.position
    ends = {w.layer: w.end for w in page.parts.wires if abs(w.end[1] - (my + 14.0)) < 1e-6}
    assert ends == {"WIRE A": (mx - 29.5, my + 14.0), "WIRE B": (mx - 44.5, my + 14.0),
                    "WIRE C": (mx - 39.5, my + 14.0)}
    # The fuse's line side comes FROM the 3-line page of its tap.
    labels = [b.attributes for b in blocks(page, "TEST_BRACKET")]
    assert labels == [{"HORIZONTAL_LABLE": "FROM SHEET 1"}]
    assert len(blocks(page, "TEST_WIRE_TILDE")) == 3        # only the FROM side: the rest is wired


def test_cts_come_from_their_shorting_kit_and_both_pages_point_at_each_other():
    result = layout(SectionContents(above=main(), power_meters=[PowerMeter("Meter", id="m1")]))
    page = device_page(result)
    assert blocks(page, "TEST_CT_IN")[0].attributes == {"STB_NO": "1", "STB_SHEET": "1"}
    three_line = result.pages[0]
    ct = [b for b in three_line.parts.blocks if b.block == "TEST_CT"][0]
    tap = [b for b in three_line.parts.blocks if b.block == "TEST_TAP"][0]
    assert ct.attributes["SHEET#"] == "2" and tap.attributes["TO_SHEET"] == "2"


def test_a_fuse_in_another_section_goes_TO_its_meter():
    result = layout(SectionContents(above=main()),
                    SectionContents(above=MainBreaker(Breaker("52-M2")), power_meters=[PowerMeter("Meter", id="m1")]))
    # One page per section (decision 2026-11-09): sheet 2 is section 1, sheet 3 section 2.
    first, second = device_pages_of(result)
    assert (first.number, first.parts.title) == (2, "ELECTRICAL SCHEMATIC SECTION 1")
    assert (second.number, second.parts.title) == (3, "ELECTRICAL SCHEMATIC SECTION 2")
    labels = [b.attributes for b in blocks(first, "TEST_BRACKET")]
    assert labels == [{"HORIZONTAL_LABLE": "FROM SHEET 1"}, {"HORIZONTAL_LABLE": "TO PM-1 SHEET 3"}]
    to_bracket = blocks(first, "TEST_BRACKET")[1]
    assert to_bracket.flipped and to_bracket.flip_parameter == "Flip state2"
    # A tilde on every wire end that goes through a bracket: 3 above the fuse, 3 below,
    # text set empty (not the block's default).
    tildes = blocks(first, "TEST_WIRE_TILDE")
    assert len(tildes) == 6 and all(t.attributes == {"TEXT_H": ""} and t.visibility == "VERTICAL" for t in tildes)
    wire_ends = {w.end for w in first.parts.wires}
    assert {t.position for t in tildes} <= wire_ends
    # The meter, on its section's page, gets its voltage input block, FROM the fuse.
    assert blocks(second, "TEST_V_IN")[0].attributes == {"FA_NO": "1", "FA_SHEET": "2"}
    assert not blocks(first, "TEST_METER") and blocks(second, "TEST_METER")


def test_sheet_references_count_the_pages_before_the_3_line():
    # Decision 2026-11-10: TOC, legend and BOM come first, so ES_01 is sheet 4 and the
    # device pages ES_02 / ES_03 are sheets 5 / 6; labels name sheets too ("FROM SHEET 4").
    settings = replace(TEST_SETTINGS, device_pages=replace(TEST_SETTINGS.device_pages, sheets_before_pages=3))
    switchboard = Switchboard("Test", [Section(SectionContents(above=main())),
                                       Section(SectionContents(above=MainBreaker(Breaker("52-M2")),
                                                               power_meters=[PowerMeter("Meter", id="m1")]))])
    first, second = device_pages_of(fit_pages(switchboard, settings, CATALOG, DEVICES))
    labels = [b.attributes for b in blocks(first, "TEST_BRACKET")]
    assert labels == [{"HORIZONTAL_LABLE": "FROM SHEET 4"}, {"HORIZONTAL_LABLE": "TO PM-1 SHEET 6"}]
    assert blocks(second, "TEST_V_IN")[0].attributes == {"FA_NO": "1", "FA_SHEET": "5"}


def test_generate_warns_when_the_sheet_count_and_the_kept_pages_disagree():
    from types import SimpleNamespace
    from src.autocad.generate import sheet_count_problems
    kept = SimpleNamespace(keep_layouts=["TOC_ES", "LEG_ES", "BOM_ES"])
    three = replace(TEST_SETTINGS, device_pages=replace(TEST_SETTINGS.device_pages, sheets_before_pages=3))
    assert sheet_count_problems(three, kept) == []
    assert "off by 3" in sheet_count_problems(TEST_SETTINGS, kept)[0]


def test_a_meter_without_a_block_is_a_box_and_says_so():
    result = layout(SectionContents(above=MainBreaker(Breaker("52-M1")),
                                    power_meters=[PowerMeter("Later", id="m1")]))
    page = device_page(result)
    assert [p.text for p in page.parts.placeholders] == ["PM-1 Later"]
    assert "PM-1 (Later): its block isn't built yet, so a box is drawn in its place." in result.warnings


def test_no_device_pages_without_devices():
    result = layout(SectionContents(above=MainBreaker(Breaker("52-M1"))))
    assert all(p.placed_sections for p in result.pages)


def test_a_section_fills_its_page_left_to_right_then_down():
    # Fourteen fuses in section 1 (their meter is in section 2): they go across section 1's page
    # from the top left, then on in a row below; section 2 gets a page of its own.
    taps = [VoltageTap("m1") for _ in range(14)]
    first = SectionContents(above=MainBreaker(Breaker("52-M1"), feed=IncomingFeed(voltage_taps=taps)))
    second = SectionContents(above=MainBreaker(Breaker("52-M2")), power_meters=[PowerMeter("Meter", id="m1")])
    pages = device_pages_of(layout(first, second))
    assert [p.parts.title for p in pages] == ["ELECTRICAL SCHEMATIC SECTION 1", "ELECTRICAL SCHEMATIC SECTION 2"]
    fuses = blocks(pages[0], "TEST_FUSE")
    assert len(fuses) == 14
    rows = sorted({round(f.position[1], 3) for f in fuses}, reverse=True)
    assert len(rows) > 1                                        # carried on in a row below
    first_row = [f.position[0] for f in fuses if round(f.position[1], 3) == rows[0]]
    assert first_row == sorted(first_row) and len(first_row) > 1                # left to right
    assert not page_notes(pages)                                # no "SECTION n" headings now


def page_notes(pages):
    return [n for page in pages for n in page.parts.notes]


def test_a_remote_display_sits_beside_its_meter_on_its_usb():
    contents = SectionContents(above=MainBreaker(Breaker("52-M1")),
                               power_meters=[PowerMeter("Meter", id="m1", remote_display=True)])
    page = device_page(layout(contents))
    meter, display = blocks(page, "TEST_METER")[0], blocks(page, "TEST_RD")[0]
    assert display.attributes == {"RD_NO": "1"}
    mx, my = meter.position
    # From the meter's USB (-46.5, -6): 12 to the left, then 6 up into the display's USB.
    usb = [(w.start, w.end) for w in page.parts.wires if w.layer == "USB LINE"]
    assert usb == [((mx - 46.5, my - 6), (mx - 58.5, my - 6)), ((mx - 58.5, my - 6), (mx - 58.5, my))]
    assert (display.position[0] + 7.5, display.position[1] + 0.5) == (mx - 58.5, my)


def test_upright_wires_get_their_label_turned():
    result = layout(SectionContents(above=main(), power_meters=[PowerMeter("Meter", id="m1")]))
    page = device_page(result)
    labels = {label.text: label for label in page.parts.wire_labels}
    # The fuse's line side stubs stand up: labels turned 90 degrees, 1 to their left.
    stub = [w for w in page.parts.wires if w.label == "4A001"][0]
    assert labels["4A001"].rotation == 90.0 and labels["4A001"].x == stub.start[0] - 1.0
    # Fuse to meter (routed down, across, down): on the across piece, not turned.
    assert labels["4A002"].rotation == 0.0


def box_texts(page):
    return [p.text for p in page.parts.placeholders]


def test_comms_modules_and_the_ethernet_switch_are_boxes_until_their_blocks_exist():
    # Sammy, 2026-11-11: a box in each one's place, in its section, after the other devices.
    result = layout(
        SectionContents(above=MainBreaker(Breaker("52-M1", comms_module="Siemens COM190"))),
        SectionContents(above=GroupMounted([TwinLevel(Breaker("52-F1", comms_module="Siemens COM060"),
                                                      Breaker("52-F2")),
                                            SingleLevel(Breaker("52-F3", comms_module="Siemens COM060"))]),
                        ethernet_switch=True))
    first, second = device_pages_of(result)
    assert first.parts.title.endswith("SECTION 1") and box_texts(first) == ["52-M1 Siemens COM190"]
    assert box_texts(second) == ["ETHERNET SWITCH", "52-F1 Siemens COM060", "52-F3 Siemens COM060"]
    assert "The Ethernet switch and the comms modules are drawn as boxes until their blocks exist."         in result.warnings


def test_the_boxes_come_after_the_devices_already_drawn():
    result = layout(SectionContents(above=main(), power_meters=[PowerMeter("Meter", id="m1")],
                                    ethernet_switch=True))
    page = device_page(result)
    meter = blocks(page, "TEST_METER")[0]
    box = page.parts.placeholders[0]
    assert box.text == "ETHERNET SWITCH"
    assert box.left_x > meter.position[0] or box.top_y < meter.position[1]   # right of it, or a row below
