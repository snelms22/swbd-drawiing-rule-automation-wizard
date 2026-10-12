"""Shared test settings and helpers.

Tests use these fixed settings, not config/layout_settings.json, so editing the config
file can never break them. The numbers are round on purpose so the arithmetic in each
test is easy to follow:

    page 500 wide x 300 tall, margins 10 standard / 5 relaxed, section clearance 5,
    title block keep-out 100 x 100 in the bottom-right corner (x 400-500, y 0-100).

    Dividers run y 10-290. Ground bus at y 20, from x 7.5 to 9 short of the title block
    (x 391). Section labels at y 15 (or 2 above the title block). Label width estimate:
    9 characters x 1.25 x 0.8 = 9 for "SECTION n".

Main bus (B phase): content between y 30 and 280; phases 5 apart; a step adds 10 width;
a tie moves the bus 70.

Useful facts:
- A section's footprint on the page = width + 10 (5 clearance each side).
- Room between standard margins = 480. Between relaxed margins = 490.
- Sections hang from y = 290 (top margin).
"""
from src.layout.block_catalog import BlockInfo
from src.layout.settings import (
    DividerSettings, GroundBusSettings, GroupMountedSettings, LayoutSettings,
    MainBreakerSettings, MainBusSettings, PlaceholderSizes, SectionLabelSettings, TextSettings,
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
    text=TextSettings(layer="0", style="Hyper_Text", height=1.25, char_width_factor=0.8),
    section_label=SectionLabelSettings(
        text_format="SECTION {number}", bottom_y=15.0, gap_above_title_block=2.0
    ),
    group_mounted=GroupMountedSettings(
        gap_to_first_level=15.0, level_pitch=25.0, level_height=10.0,
        vertical_bus_overhang=10.0, single_mount_first_side="left",
    ),
    placeholder_sizes=PlaceholderSizes(
        main_breaker_width=30.0, main_breaker_height=75.0,
        single_breaker_width=30.0, single_breaker_height=45.0,
        group_mounted_width=145.0, tie_breaker_width=30.0,
    ),
    main_bus=MainBusSettings(
        layer="BUS", phase_spacing=5.0, step_width=10.0, tie_step_height=70.0,
        content_top_y=280.0, content_bottom_y=30.0, junction_dot_block="BUS_NODE",
    ),
    main_breaker=MainBreakerSettings(
        block="TEST_BKR", block_layer="0", visibility="1 BOM",
        gap_bus_to_breaker=15.0, gap_breaker_to_input=30.0, input_box_height=15.0,
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
}
