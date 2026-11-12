"""Shared test settings and helpers.

Tests use these fixed settings, not config/layout_settings.json, so editing the config
file can never break them. The numbers are round on purpose so the arithmetic in each
test is easy to follow:

    page 500 wide x 300 tall, margins 10 standard / 5 relaxed, section clearance 5,
    title block keep-out 100 x 100 in the bottom-right corner (x 400-500, y 0-100).

    Dividers run y 10-290. Ground bus at y 20, from x 7.5 to 9 short of the title block
    (x 391). Section labels at y 15 (or 2 above the title block). Label width estimate:
    9 characters x 1.25 x 0.8 = 9 for "SECTION n".

Main bus (B phase): content between y 30 and 280; phases 5 apart; a step adds 20 width
(10 for the bus's vertical run + 10 clearance);
a tie moves the bus 70.

Useful facts:
- A section's footprint on the page = width + 10 (5 clearance each side).
- Room between standard margins = 480. Between relaxed margins = 490.
- Sections hang from y = 290 (top margin).
"""
from src.layout.block_catalog import BlockInfo
from src.layout.settings import (
    CurrentTransformerSettings, DevicePageSettings, DividerSettings, InterlockSettings, LineSideBreakerSettings,
    PageTitleSettings, WireLabelSettings,
    VoltageTapSettings, GroundBusSettings, GroupMountedSettings, LayoutSettings,
    BusBreakSettings, FeederSettings, InputOutputSettings, MainBreakerSettings, MainBusSettings, PlaceholderSizes,
    SectionLabelSettings, TextSettings,
)

TEST_SETTINGS = LayoutSettings(
    drawable_width=500.0,
    drawable_height=300.0,
    margin_standard=10.0,
    margin_relaxed=5.0,
    divider_clearance=5.0,
    keepout_width=100.0,
    keepout_height=100.0,
    divider=DividerSettings(layer="DEVIDER", bottom_y=10.0, top_y=290.0),
    ground_bus=GroundBusSettings(
        layer="GROUND",
        y=20.0,
        start_x=7.5,
        gap_before_title_block=9.0,
        label_text="GROUND BUS",
        label_offset_x=0.5,
        label_gap_above_bus=1.5,
        symbol_offset_x=6.0,
        symbol_stem_length=2.0,
        symbol_bar_widths=(5.0, 3.75, 2.5),
        symbol_bar_spacing=1.25,
    ),
    text=TextSettings(layer="0", style="Hyper_Text", height=1.25, char_width_factor=0.8,
                      line_spacing_factor=1.6),
    section_label=SectionLabelSettings(
        text_format="SECTION {number}", bottom_y=15.0, gap_above_title_block=2.0
    ),
    group_mounted=GroupMountedSettings(
        gap_to_first_level=15.0, level_pitch=25.0, level_height=10.0,
        vertical_bus_overhang=10.0, single_mount_first_side="left",
        column_pitch=100.0, continuation_start_gap=15.0, column_clearance=10.0,
    ),
    placeholder_sizes=PlaceholderSizes(
        main_breaker_width=30.0, main_breaker_height=75.0,
        single_breaker_width=30.0, single_breaker_height=45.0,
        group_mounted_width=145.0, tie_breaker_width=30.0,
    ),
    main_bus=MainBusSettings(
        layer="BUS", phase_spacing=5.0, step_width=10.0, step_clearance=10.0,
        tie_step_height=70.0,
        page_break_overrun_max=30.0, page_break_overrun_min=0.0, page_break_label_space=0.0,
        content_top_y=280.0, content_bottom_y=30.0, junction_dot_block="BUS_NODE",
    ),
    main_breaker=MainBreakerSettings(
        blocks={"fixed": "TEST_BKR", "draw-out": "TEST_BKR_DO"}, block_layer="0",
        label_attribute="BREAKER_NAME",
        visibility="1 BOM",
        gap_bus_to_breaker=15.0, gap_breaker_to_input=30.0, input_box_height=15.0,
        u_turn_depth=30.0, u_turn_width=35.0, u_turn_termination_rise=5.0,
        u_turn_text_clearance=5.0,
    ),
    input_output=InputOutputSettings(
        block="TEST_LUGS", neutral_block="TEST_LUGS_N", layer="0",
        input_state="INPUT", output_state="OUTPUT",
    ),
    feeder=FeederSettings(
        block="TEST_FEEDER", layer="0", visibility="3 PHASE-3 WIRE",
        mirror_parameter="MIRROR-3W", label_attribute="DEVICE_ID", tap_length=10.0,
        provision_heading="PROVISION FOR", provision_heading_without_info="PROVISION",
        provision_text_gap=10.0, space_text="SPACE",
    ),
    current_transformers=CurrentTransformerSettings(
        block="TEST_CT", layer="0", vertical_state_source_above="CT LEFT - POLARITY TOP",
        vertical_state_source_below="CT LEFT - POLARITY BOTTOM", vertical_marker_suffix="_L",
        clearance=5.0, ct_number_attributes=["CT_A_DWG#", "CT_B_DWG#", "CT_C_DWG#"],
        shorting_kit_attribute="STB#", meter_attribute="LOCATION", ratio_attribute="CURRENT_RATIO",
        sheet_attribute="SHEET#",
    ),
    device_pages=DevicePageSettings(
        unit_gap=10.0, row_gap=10.0, wire_spacing=5.0, stub_length=8.0, from_tap_label="FROM {page}",
        to_meter_label="TO {meter} SHEET {sheet}", sheet_format="{sheet}",
        placeholder_width=100.0, placeholder_height=40.0,
        ethernet_switch_text="ETHERNET SWITCH", ethernet_switch_width=80.0, ethernet_switch_height=30.0,
        comms_width=60.0, comms_height=20.0,
        feed_rail_gap=8.0, feed_box_gap=8.0, feed_box_spacing=6.0, feed_into_box=2.0,
        shipping_split_cable=40.0, split_stub_length=6.0,
        wire_break_block="TEST_WIRE_TILDE", wire_break_state="VERTICAL", wire_break_marker="CONN",
        wire_break_text_attribute="TEXT_H", remote_display_gap=12.0, remote_display_rise=6.0,
        wire_break_state_horizontal="HORIZONTAL", from_fuse_label="FROM {fuse} SHEET {sheet}",
        wire_break_flip_horizontal="Flip state1",
    ),
    line_side_breakers=LineSideBreakerSettings(tie_gap=10.0, gap_to_breaker=15.0,
                                               gap_breaker_to_output=25.0),
    wire_labels=WireLabelSettings(
        layer="TEXT", height=1.25, gap=1.0, digits=3,
        prefixes={"WIRE A": "4A", "WIRE B": "4B", "WIRE C": "4C"},
    ),
    page_title=PageTitleSettings(
        layer="0", x=390.0, y=5.0, height=3.0, mtext_format="{{\\L{title}}}",
        three_line_format="THREE-LINE DIAGRAM {page:02d}",
        device_page_format="ELECTRICAL SCHEMATIC SECTION {section}",
        shipping_split_page="SHIPPING SPLITS",
    ),
    interlocks=InterlockSettings(
        layer="INTERLOCK", start_past_left_c=2.5, end_before_right_a=1.0, background_mask=True,
        text_mechanical=("MECHANICAL INTERLOCK",), text_electrical=("ELECTRICAL INTERLOCK",),
        text_both=("MECHANICAL AND", "ELECTRICAL INTERLOCK"),
    ),
    voltage_taps=VoltageTapSettings(
        block="TEST_TAP", layer="0", vertical_state="FROM_LEFT", vertical_markers=["LA", "LB", "LC"],
        clearance=5.0, fuse_number_attribute="FUSE_DRW_NUM", sheet_attribute="TO_SHEET",
    ),
    bus_break=BusBreakSettings(
        layer="0", tilde_block="TEST_TILDE", tilde_state_horizontal_bus="HORIZONTAL",
        tilde_state_vertical_bus="VERTICAL", tilde_flip_horizontal_bus="Flip state1",
        tilde_flip_vertical_bus="Flip state2", bracket_flip_horizontal_bus="Flip state1",
        bracket_flip_vertical_bus="Flip state2",
        bracket_block="TEST_BRACKET",
        bracket_state_horizontal_bus="VERTICAL BRACKET",
        bracket_state_vertical_bus="HORIZONTAL BRACKET", bracket_gap=2.0,
        label_attribute_horizontal_bus="VERTICAL_LABLE",
        label_attribute_vertical_bus="HORIZONTAL_LABLE", page_reference="SHEET {sheet}",
        to_label="TO {page}", from_label="FROM {page}",
        column_cut_label="BUS CONTINUES", continued_from_below_label="FROM BELOW",
        continued_from_above_label="FROM ABOVE",
    ),
)

SHORT = 50.0  # tall enough to see, short enough to never reach the title block


def make_lineup(*boxes):
    """A lineup of section boxes, left to right (what fit_boxes() takes)."""
    return list(boxes)


def numbers_per_page(result):
    """Section numbers on each page, e.g. [[1, 2], [3]]."""
    return [[p.number for p in page.placed_sections] for page in result.pages]


# A breaker block shaped like the library's 3P_CB_FM_1: poles at x 0 / 5 / 10, 10 long,
# hanging down from the base point.
TEST_CATALOG = {
    "TEST_BKR": BlockInfo(
        name="TEST_BKR",
        top_terminals=((0.0, 0.0), (5.0, 0.0), (10.0, 0.0)),
        bottom_terminals=((0.0, -10.0), (5.0, -10.0), (10.0, -10.0)),
        extents=(-0.5, -11.0, 25.0, 3.5),
    ),
    "TEST_BKR_DO": BlockInfo(
        name="TEST_BKR_DO",
        top_terminals=((0.0, 0.0), (5.0, 0.0), (10.0, 0.0)),
        bottom_terminals=((0.0, -10.0), (5.0, -10.0), (10.0, -10.0)),
        extents=(-1.0, -11.0, 25.5, 3.5),
    ),
    # Shaped like PHASE_LUGS_3L_R0: connections 5 above the base point when not flipped
    # (block below the bus end), 5 below it when flipped (block above).
    "TEST_LUGS": BlockInfo(
        name="TEST_LUGS",
        top_terminals=(), bottom_terminals=(),
        extents=(-3.0, -10.0, 18.0, 5.0),
        connections={
            "not_flipped": {"A": (0.0, 5.0), "B": (5.0, 5.0), "C": (10.0, 5.0), "N": (15.0, 5.0)},
            "flipped": {"A": (0.0, -5.0), "B": (5.0, -5.0), "C": (10.0, -5.0), "N": (15.0, -5.0)},
        },
        extents_flipped=(-3.0, -5.0, 18.0, 10.0),
    ),
    # Shaped like 3P_TIDE_R0 and BRACKET_TEXT_R0.
    "TEST_TILDE": BlockInfo(
        name="TEST_TILDE", top_terminals=(), bottom_terminals=(),
        extents=(-1.25, -11.25, 11.25, 2.3),
        connections={"not_flipped": {"A": (0.0, 0.0)}},
    ),
    # Shaped like SIE_BKR_3P_3L_ASSY_R0: connections at x 0 (A 10, B 5, C 0), body and
    # text to the left, up to 23 above C.
    "TEST_FEEDER": BlockInfo(
        name="TEST_FEEDER", top_terminals=(), bottom_terminals=(),
        extents=(-23.0, -1.0, 0.0, 23.0), extents_flipped=(0.0, -1.0, 23.0, 23.0),
        connections={"not_flipped": {"A": (0.0, 10.0), "B": (0.0, 5.0), "C": (0.0, 0.0)},
                     "flipped": {"A": (0.0, 10.0), "B": (0.0, 5.0), "C": (0.0, 0.0)}},
    ),
    # Shaped like 3_CTS_3L_R1 on a vertical run (CT LEFT states): A marker at the base
    # point, B 5 right and 10 down, C 10 right and 20 down; the set (with its shorting
    # block) reaches 20 left, 60 right, 10 up and 35 down.
    "TEST_CT": BlockInfo(
        name="TEST_CT", top_terminals=(), bottom_terminals=(),
        extents=(-20.0, -35.0, 60.0, 10.0),
        visibility_states=("CT LEFT - POLARITY TOP", "CT LEFT - POLARITY BOTTOM"),
        states={state: {"markers": {"A_L": (0.0, 0.0), "B_L": (5.0, -10.0), "C_L": (10.0, -20.0)},
                        "extents": (-20.0, -35.0, 60.0, 10.0)}
                for state in ("CT LEFT - POLARITY TOP", "CT LEFT - POLARITY BOTTOM")},
    ),
    # Shaped like 3P_Voltage_Tap in its FROM_LEFT state: A marker at the base point, B 5
    # right and 5 down, C 10 right and 10 down; reaches 1 left, 30 right, 2 up, 12 down.
    "TEST_TAP": BlockInfo(
        name="TEST_TAP", top_terminals=(), bottom_terminals=(),
        extents=(-1.0, -31.0, 30.0, 21.0),
        visibility_states=("FROM_LEFT", "FROM_TOP", "FROM_BOTTOM"),
        states={"FROM_LEFT": {"markers": {"LA": (0.0, 0.0), "LB": (5.0, -5.0), "LC": (10.0, -10.0)},
                              "extents": (-1.0, -12.0, 30.0, 2.0)}},
    ),
    # Shaped like TILDE_R0: a small squiggle centred on its CONN point.
    "TEST_WIRE_TILDE": BlockInfo(
        name="TEST_WIRE_TILDE", top_terminals=(), bottom_terminals=(), extents=(-1.25, -1.25, 1.25, 1.25),
        visibility_states=("HORIZONTAL", "VERTICAL"),
        states={"VERTICAL": {"markers": {"CONN": (0.0, 0.0)}, "extents": (-1.25, -0.83, 1.25, 0.83)},
                "HORIZONTAL": {"markers": {"CONN": (0.0, 0.0)}, "extents": (-0.83, -1.25, 0.83, 1.25)}},
    ),
    "TEST_BRACKET": BlockInfo(
        name="TEST_BRACKET", top_terminals=(), bottom_terminals=(),
        extents=(-6.0, -6.0, 6.7, 6.0),
    ),
}
