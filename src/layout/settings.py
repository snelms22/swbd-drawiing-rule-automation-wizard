"""Loads the editable layout numbers from config/layout_settings.json.

Every number that controls page layout lives in that file, not in code (see CLAUDE.md).
This module only reads and checks them, so a typo in the file gives a clear message
instead of a confusing crash somewhere inside the layout engine.
"""
import json
from dataclasses import dataclass
from pathlib import Path


class SettingsError(Exception):
    """The settings file is missing, unreadable, or has a bad value."""


@dataclass(frozen=True)
class DividerSettings:
    layer: str
    bottom_y: float   # dividers run from here...
    top_y: float      # ...up to here, on every page


@dataclass(frozen=True)
class GroundBusSettings:
    layer: str
    y: float
    start_x: float                  # where the ground bus line starts on every page
    gap_before_title_block: float   # the line stops this far left of the title block
    label_text: str
    label_offset_x: float           # label's left edge, measured from the line's start
    label_gap_above_bus: float      # label's bottom, measured up from the line
    symbol_offset_x: float          # ground symbol stem, measured from the line's start
    symbol_stem_length: float
    symbol_bar_widths: tuple[float, ...]   # widest bar first
    symbol_bar_spacing: float


@dataclass(frozen=True)
class TextSettings:
    layer: str
    style: str
    height: float
    # Average character width as a fraction of text height (measured from "SECTION 1" in
    # Sammy's ES_01). Used to estimate how wide a label is without AutoCAD.
    char_width_factor: float
    # Multi-line text: each extra line adds height x this (AutoCAD's MText line spacing).
    line_spacing_factor: float

    def estimated_width(self, text: str) -> float:
        return len(text) * self.height * self.char_width_factor

    def extra_height_for_lines(self, text: str) -> float:
        """How much taller `text` is than one line, from the line breaks typed in it."""
        return text.count("\n") * self.height * self.line_spacing_factor


@dataclass(frozen=True)
class SectionLabelSettings:
    text_format: str   # e.g. "SECTION {number}"
    bottom_y: float
    gap_above_title_block: float   # used when a label is moved up out of the title block


@dataclass(frozen=True)
class GroupMountedSettings:
    gap_to_first_level: float     # main bus to the nearest level
    level_pitch: float            # level to level
    level_height: float           # one level (a breaker's three poles)
    vertical_bus_overhang: float  # vertical bus continues this far past the last level
    single_mount_first_side: str  # "left" or "right": side of the first single level
    # A part too tall for the page continues in a column beside it (decision 2026-10-13).
    column_pitch: float           # column to column, A phase to A phase
    continuation_start_gap: float # main bus (nearest phase) to where a continuation column starts
    column_clearance: float       # least room between the breakers of neighbouring columns


@dataclass(frozen=True)
class PlaceholderSizes:
    """Stand-in sizes until the real blocks are catalogued. Widths include labels."""
    main_breaker_width: float
    main_breaker_height: float
    single_breaker_width: float
    single_breaker_height: float
    group_mounted_width: float
    tie_breaker_width: float


@dataclass(frozen=True)
class MainBusSettings:
    layer: str
    phase_spacing: float     # A-B and B-C; A to C is twice this
    step_width: float        # width of the bus's vertical run (A to C) where it changes height
    step_clearance: float    # space kept between that vertical run and anything else
    tie_step_height: float   # how far the bus moves up or down at a tie breaker
    page_break_overrun_max: float   # bus runs this far past the last divider when there's room
    page_break_overrun_min: float   # ...and never less than this
    page_break_label_space: float   # room after that for the break block's to/from label
    content_top_y: float     # nothing in a section goes above this
    content_bottom_y: float  # nothing in a section goes below this (clear of the ground bus)
    junction_dot_block: str  # library block for bus junction dots ("BUS_NODE")


@dataclass(frozen=True)
class MainBreakerSettings:
    blocks: dict                # library block per mounting: {"fixed": ..., "draw-out": ...}
    block_layer: str
    label_attribute: str        # the attribute the breaker's Label fills (e.g. "BREAKER_NAME")
    visibility: str             # the block's visibility state to use (e.g. "1 BOM")
    gap_bus_to_breaker: float   # main bus (nearest phase) to the breaker's near terminals
    gap_breaker_to_input: float # breaker's far terminals to the input end of the bus
    input_box_height: float     # room kept for the input block and its label
    # U-turn when the termination is fed from the other side than the breaker (2026-10-13).
    u_turn_depth: float         # U-turns of a breaker fed on the bus side: start to nearest phase
    u_turn_width: float         # from the breaker's leg to the termination's leg
    u_turn_termination_rise: float  # out of the U-turn this far, then the termination block
    u_turn_text_clearance: float    # termination's text to the breaker and its text


@dataclass(frozen=True)
class BusBreakSettings:
    """Tilde + bracket marking where a bus is cut (page break or too-tall column)."""
    layer: str
    tilde_block: str
    tilde_state_horizontal_bus: str
    tilde_state_vertical_bus: str
    tilde_flip_horizontal_bus: str   # the one flip setting that mirrors the tilde left-right
    tilde_flip_vertical_bus: str     # ... that mirrors it up-down (on a vertical bus)
    bracket_flip_horizontal_bus: str # the bracket's left-right flip
    bracket_flip_vertical_bus: str   # the bracket's up-down flip
    bracket_block: str
    bracket_state_horizontal_bus: str
    bracket_state_vertical_bus: str
    bracket_gap: float          # from the bus end to the bracket's base point
    label_attribute_horizontal_bus: str   # bracket label tag in its horizontal-bus state
    label_attribute_vertical_bus: str     # ...and in its vertical-bus state
    page_reference: str         # how a page is named in labels, e.g. "ES_{number:02d}"
    to_label: str               # e.g. "TO {page}"
    from_label: str             # e.g. "FROM {page}"
    # Too-tall split: where a column is cut, and where the next column starts.
    column_cut_label: str           # e.g. "BUS CONTINUES"
    continued_from_below_label: str # e.g. "FROM BELOW" (a part below the main bus)
    continued_from_above_label: str # e.g. "FROM ABOVE" (a part above the main bus)

    def label(self, direction: str, page_number: int) -> str:
        page = self.page_reference.format(number=page_number)
        return (self.to_label if direction == "to" else self.from_label).format(page=page)


@dataclass(frozen=True)
class CurrentTransformerSettings:
    """The CT set block and how the program fills it (decision 2026-10-21)."""
    block: str
    layer: str
    vertical_state_source_above: str   # on a vertical run, source above (polarity up)
    vertical_state_source_below: str   # ... source below
    vertical_marker_suffix: str        # markers used on a vertical run, e.g. "_L"
    clearance: float                   # from the CT set to the bus or breaker beside it
    ct_number_attributes: list         # the three CT numbers (A, B, C)
    shorting_kit_attribute: str        # shorting-kit number
    meter_attribute: str               # the meter it feeds ("PM-3-1")
    sheet_attribute: str               # the sheet that meter is on
    ratio_attribute: str               # current ratio


@dataclass(frozen=True)
class DevicePageSettings:
    """Device pages: meters and fuses, grouped by section (decision 2026-10-23)."""
    heading_format: str          # e.g. "SECTION {number}"
    heading_gap: float           # heading text to the devices under it
    unit_gap: float              # between devices side by side
    row_gap: float               # between rows
    group_gap: float             # extra space before the next section's heading
    wire_spacing: float          # between the wires' corners (and wires to the fuse)
    stub_length: float           # wire stub to a TO / FROM bracket
    from_tap_label: str          # a fuse's line side, e.g. "FROM {page}" (the 3-line page)
    to_meter_label: str          # a fuse's load side when its meter is in another section
    sheet_format: str            # how a sheet number is written, e.g. "{page}"
    placeholder_width: float     # a meter whose block isn't built yet
    placeholder_height: float
    wire_break_block: str        # tilde on each wire end at a TO / FROM bracket
    wire_break_state: str        # its state on a vertical wire
    wire_break_marker: str       # its connection point (on the wire end)
    wire_break_text_attribute: str   # its text, left empty
    wire_break_state_horizontal: str # its state on a horizontal wire (beside a power supply)
    wire_break_flip_horizontal: str  # the flip that mirrors it left-right there
    from_fuse_label: str         # a power supply's inputs when its fuse is in another section
    remote_display_gap: float    # meter USB to the remote display, sideways
    remote_display_rise: float   # ... then up into the display's USB


@dataclass(frozen=True)
class LineSideBreakerSettings:
    """A line-side (load-bank) breaker's tie into a main's feed (decision 2026-10-22)."""
    tie_gap: float               # main breaker's line-side terminals to the tie's nearest phase
    gap_to_breaker: float        # tie's outer phase to the line-side breaker's terminals
    gap_breaker_to_output: float # the line-side breaker's other end to its output termination


@dataclass(frozen=True)
class VoltageTapSettings:
    """The voltage tap block and how the program places and fills it (decision 2026-10-22)."""
    block: str
    layer: str
    vertical_state: str                # visibility state on a vertical run (e.g. "FROM_LEFT")
    vertical_markers: list             # its A, B, C markers in that state (e.g. LA, LB, LC)
    clearance: float                   # from the breaker, the next tap, the termination
    fuse_number_attribute: str         # after "FA-": "s-n" (section-number)
    sheet_attribute: str               # the sheet the fuse is on


@dataclass(frozen=True)
class FeederSettings:
    """Group-mounted feeder breakers."""
    block: str              # library block, drawn as a left-side breaker
    layer: str
    visibility: str         # e.g. "3 PHASE-3 WIRE"
    mirror_parameter: str   # the ONE mirror setting for right-side breakers in that state
    label_attribute: str    # the attribute the breaker's Label fills (e.g. "DEVICE_ID")
    tap_length: float       # tap from the nearest vertical-bus phase to the breaker
    provision_heading: str                # first line of a provision note, e.g. "PROVISION FOR"
    provision_heading_without_info: str   # ...when the engineer gave no info, e.g. "PROVISION"
    provision_text_gap: float             # from the provision's tap ends to its note
    space_text: str                       # the note on a SPACE slot, e.g. "SPACE"

    def note_lines(self, slot) -> list[str]:
        """The note beside an empty slot: a provision's note, or the SPACE text."""
        info = getattr(slot, "info", None)
        return self.provision_lines(info) if info is not None else [self.space_text]

    def provision_lines(self, info: str) -> list[str]:
        """The lines of a provision's note."""
        info = info.strip()
        return [self.provision_heading, info] if info else [self.provision_heading_without_info]


@dataclass(frozen=True)
class InterlockSettings:
    """The dashed line and text between two interlocked main breakers (decision 2026-10-26)."""
    layer: str                  # the line's layer (its own layer, INTERLOCK, in HYPER_A)
    start_past_left_c: float    # line starts this far right of the left main's C terminal
    end_before_right_a: float   # ...and ends this far left of the right main's A terminal
    background_mask: bool       # mask behind the text, so the dashes don't run through it
    text_mechanical: tuple[str, ...]   # the text, one entry per line
    text_electrical: tuple[str, ...]
    text_both: tuple[str, ...]

    def text_lines(self, interlock) -> tuple[str, ...]:
        if interlock.mechanical and interlock.electrical:
            return self.text_both
        return self.text_mechanical if interlock.mechanical else self.text_electrical


@dataclass(frozen=True)
class InputOutputSettings:
    block: str          # library block for the input/output bus connection
    neutral_block: str  # the same with a neutral (not placed yet; checked by Audit Blocks)
    layer: str
    input_state: str    # visibility state for power coming in (e.g. "INPUT")
    output_state: str   # visibility state for power going out (e.g. "OUTPUT")


@dataclass(frozen=True)
class LayoutSettings:
    drawable_width: float
    drawable_height: float
    margin_standard: float
    margin_relaxed: float
    divider_clearance: float
    keepout_width: float
    keepout_height: float
    divider: DividerSettings
    ground_bus: GroundBusSettings
    text: TextSettings
    section_label: SectionLabelSettings
    group_mounted: GroupMountedSettings
    placeholder_sizes: PlaceholderSizes
    main_bus: MainBusSettings
    main_breaker: MainBreakerSettings
    input_output: InputOutputSettings
    bus_break: BusBreakSettings
    feeder: FeederSettings
    current_transformers: CurrentTransformerSettings
    voltage_taps: VoltageTapSettings
    line_side_breakers: LineSideBreakerSettings
    device_pages: DevicePageSettings
    interlocks: InterlockSettings

    @property
    def keepout_left_x(self) -> float:
        """x where the title block keep-out begins (it runs to the right edge)."""
        return self.drawable_width - self.keepout_width


def load_settings(path) -> LayoutSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"Settings file not found: {path}")
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path} is not valid JSON: {error}")

    # Only the bottom-right corner is supported so far; fail loudly rather than
    # silently putting the keep-out somewhere other than the file says.
    corner = _read_text(data, "title_block_keepout", "corner")
    if corner != "bottom_right":
        raise SettingsError(
            f'title_block_keepout.corner is "{corner}", but only "bottom_right" is supported.'
        )

    first_side = _read_text(data, "group_mounted", "single_mount_first_side")
    if first_side not in ("left", "right"):
        raise SettingsError(
            f'group_mounted.single_mount_first_side must be "left" or "right", got "{first_side}".'
        )

    section_label_format = _read_text(data, "section_label", "text_format")
    if "{number}" not in section_label_format:
        raise SettingsError('section_label.text_format must contain "{number}".')

    return LayoutSettings(
        drawable_width=_read_number(data, "page", "drawable_width"),
        drawable_height=_read_number(data, "page", "drawable_height"),
        margin_standard=_read_number(data, "page", "margin_standard"),
        margin_relaxed=_read_number(data, "page", "margin_relaxed"),
        divider_clearance=_read_number(data, "section", "divider_clearance"),
        keepout_width=_read_number(data, "title_block_keepout", "width"),
        keepout_height=_read_number(data, "title_block_keepout", "height"),
        divider=DividerSettings(
            layer=_read_text(data, "divider", "layer"),
            bottom_y=_read_number(data, "divider", "bottom_y"),
            top_y=_read_number(data, "divider", "top_y"),
        ),
        ground_bus=GroundBusSettings(
            layer=_read_text(data, "ground_bus", "layer"),
            y=_read_number(data, "ground_bus", "y"),
            start_x=_read_number(data, "ground_bus", "start_x"),
            gap_before_title_block=_read_number(data, "ground_bus", "gap_before_title_block"),
            label_text=_read_text(data, "ground_bus", "label_text"),
            label_offset_x=_read_number(data, "ground_bus", "label_offset_x"),
            label_gap_above_bus=_read_number(data, "ground_bus", "label_gap_above_bus"),
            symbol_offset_x=_read_number(data, "ground_bus", "symbol_offset_x"),
            symbol_stem_length=_read_number(data, "ground_bus", "symbol_stem_length"),
            symbol_bar_widths=_read_number_list(data, "ground_bus", "symbol_bar_widths"),
            symbol_bar_spacing=_read_number(data, "ground_bus", "symbol_bar_spacing"),
        ),
        text=TextSettings(
            layer=_read_text(data, "text", "layer"),
            style=_read_text(data, "text", "style"),
            height=_read_number(data, "text", "height"),
            char_width_factor=_read_number(data, "text", "char_width_factor"),
            line_spacing_factor=_read_number(data, "text", "line_spacing_factor"),
        ),
        section_label=SectionLabelSettings(
            text_format=section_label_format,
            bottom_y=_read_number(data, "section_label", "bottom_y"),
            gap_above_title_block=_read_number(data, "section_label", "gap_above_title_block"),
        ),
        group_mounted=GroupMountedSettings(
            gap_to_first_level=_read_number(data, "group_mounted", "gap_to_first_level"),
            level_pitch=_read_number(data, "group_mounted", "level_pitch"),
            level_height=_read_number(data, "group_mounted", "level_height"),
            vertical_bus_overhang=_read_number(data, "group_mounted", "vertical_bus_overhang"),
            column_pitch=_read_number(data, "group_mounted", "column_pitch"),
            continuation_start_gap=_read_number(data, "group_mounted", "continuation_start_gap"),
            column_clearance=_read_number(data, "group_mounted", "column_clearance"),
            single_mount_first_side=first_side,
        ),
        placeholder_sizes=PlaceholderSizes(
            main_breaker_width=_read_number(data, "placeholder_sizes", "main_breaker_width"),
            main_breaker_height=_read_number(data, "placeholder_sizes", "main_breaker_height"),
            single_breaker_width=_read_number(data, "placeholder_sizes", "single_breaker_width"),
            single_breaker_height=_read_number(data, "placeholder_sizes", "single_breaker_height"),
            group_mounted_width=_read_number(data, "placeholder_sizes", "group_mounted_width"),
            tie_breaker_width=_read_number(data, "placeholder_sizes", "tie_breaker_width"),
        ),
        main_bus=MainBusSettings(
            layer=_read_text(data, "main_bus", "layer"),
            phase_spacing=_read_number(data, "main_bus", "phase_spacing"),
            step_width=_read_number(data, "main_bus", "step_width"),
            step_clearance=_read_number(data, "main_bus", "step_clearance"),
            tie_step_height=_read_number(data, "main_bus", "tie_step_height"),
            page_break_overrun_max=_read_number(data, "main_bus", "page_break_overrun_max"),
            page_break_overrun_min=_read_number(data, "main_bus", "page_break_overrun_min"),
            page_break_label_space=_read_number(data, "main_bus", "page_break_label_space"),
            content_top_y=_read_number(data, "main_bus", "content_top_y"),
            content_bottom_y=_read_number(data, "main_bus", "content_bottom_y"),
            junction_dot_block=_read_text(data, "main_bus", "junction_dot_block"),
        ),
        main_breaker=MainBreakerSettings(
            blocks=_read_mounting_blocks(data),
            block_layer=_read_text(data, "main_breaker", "block_layer"),
            label_attribute=_read_text(data, "main_breaker", "label_attribute"),
            visibility=_read_text(data, "main_breaker", "visibility"),
            gap_bus_to_breaker=_read_number(data, "main_breaker", "gap_bus_to_breaker"),
            gap_breaker_to_input=_read_number(data, "main_breaker", "gap_breaker_to_input"),
            input_box_height=_read_number(data, "main_breaker", "input_box_height"),
            u_turn_depth=_read_number(data, "main_breaker", "u_turn_depth"),
            u_turn_width=_read_number(data, "main_breaker", "u_turn_width"),
            u_turn_termination_rise=_read_number(data, "main_breaker", "u_turn_termination_rise"),
            u_turn_text_clearance=_read_number(data, "main_breaker", "u_turn_text_clearance"),
        ),
        input_output=InputOutputSettings(
            block=_read_text(data, "input_output", "block"),
            neutral_block=_read_text(data, "input_output", "neutral_block"),
            layer=_read_text(data, "input_output", "layer"),
            input_state=_read_text(data, "input_output", "input_state"),
            output_state=_read_text(data, "input_output", "output_state"),
        ),
        device_pages=DevicePageSettings(
            heading_format=_read_text(data, "device_pages", "heading_format"),
            heading_gap=_read_number(data, "device_pages", "heading_gap"),
            unit_gap=_read_number(data, "device_pages", "unit_gap"),
            row_gap=_read_number(data, "device_pages", "row_gap"),
            group_gap=_read_number(data, "device_pages", "group_gap"),
            wire_spacing=_read_number(data, "device_pages", "wire_spacing"),
            stub_length=_read_number(data, "device_pages", "stub_length"),
            from_tap_label=_read_text(data, "device_pages", "from_tap_label"),
            to_meter_label=_read_text(data, "device_pages", "to_meter_label"),
            sheet_format=_read_text(data, "device_pages", "sheet_format"),
            placeholder_width=_read_number(data, "device_pages", "placeholder_width"),
            placeholder_height=_read_number(data, "device_pages", "placeholder_height"),
            wire_break_block=_read_text(data, "device_pages", "wire_break_block"),
            wire_break_state=_read_text(data, "device_pages", "wire_break_state"),
            wire_break_marker=_read_text(data, "device_pages", "wire_break_marker"),
            wire_break_text_attribute=_read_text(data, "device_pages", "wire_break_text_attribute"),
            wire_break_state_horizontal=_read_text(data, "device_pages", "wire_break_state_horizontal"),
            wire_break_flip_horizontal=_read_text(data, "device_pages", "wire_break_flip_horizontal"),
            from_fuse_label=_read_text(data, "device_pages", "from_fuse_label"),
            remote_display_gap=_read_number(data, "device_pages", "remote_display_gap"),
            remote_display_rise=_read_number(data, "device_pages", "remote_display_rise"),
        ),
        interlocks=InterlockSettings(
            layer=_read_text(data, "interlocks", "layer"),
            start_past_left_c=_read_number(data, "interlocks", "start_past_left_c"),
            end_before_right_a=_read_number(data, "interlocks", "end_before_right_a"),
            background_mask=_read_true_false(data, "interlocks", "background_mask"),
            text_mechanical=_read_text_lines(data, "interlocks", "text_mechanical"),
            text_electrical=_read_text_lines(data, "interlocks", "text_electrical"),
            text_both=_read_text_lines(data, "interlocks", "text_both"),
        ),
        line_side_breakers=LineSideBreakerSettings(
            tie_gap=_read_number(data, "line_side_breakers", "tie_gap"),
            gap_to_breaker=_read_number(data, "line_side_breakers", "gap_to_breaker"),
            gap_breaker_to_output=_read_number(data, "line_side_breakers", "gap_breaker_to_output"),
        ),
        voltage_taps=VoltageTapSettings(
            block=_read_text(data, "voltage_taps", "block"),
            layer=_read_text(data, "voltage_taps", "layer"),
            vertical_state=_read_text(data, "voltage_taps", "vertical_state"),
            vertical_markers=list(data["voltage_taps"]["vertical_markers"]),
            clearance=_read_number(data, "voltage_taps", "clearance"),
            fuse_number_attribute=_read_text(data, "voltage_taps", "fuse_number_attribute"),
            sheet_attribute=_read_text(data, "voltage_taps", "sheet_attribute"),
        ),
        current_transformers=CurrentTransformerSettings(
            block=_read_text(data, "current_transformers", "block"),
            layer=_read_text(data, "current_transformers", "layer"),
            vertical_state_source_above=_read_text(data, "current_transformers", "vertical_state_source_above"),
            vertical_state_source_below=_read_text(data, "current_transformers", "vertical_state_source_below"),
            vertical_marker_suffix=_read_text(data, "current_transformers", "vertical_marker_suffix"),
            clearance=_read_number(data, "current_transformers", "clearance"),
            ct_number_attributes=list(data["current_transformers"]["ct_number_attributes"]),
            shorting_kit_attribute=_read_text(data, "current_transformers", "shorting_kit_attribute"),
            meter_attribute=_read_text(data, "current_transformers", "meter_attribute"),
            sheet_attribute=_read_text(data, "current_transformers", "sheet_attribute"),
            ratio_attribute=_read_text(data, "current_transformers", "ratio_attribute"),
        ),
        feeder=FeederSettings(
            block=_read_text(data, "feeder", "block"),
            layer=_read_text(data, "feeder", "layer"),
            visibility=_read_text(data, "feeder", "visibility"),
            mirror_parameter=_read_text(data, "feeder", "mirror_parameter"),
            label_attribute=_read_text(data, "feeder", "label_attribute"),
            tap_length=_read_number(data, "feeder", "tap_length"),
            provision_heading=_read_text(data, "feeder", "provision_heading"),
            provision_heading_without_info=_read_text(data, "feeder", "provision_heading_without_info"),
            provision_text_gap=_read_number(data, "feeder", "provision_text_gap"),
            space_text=_read_text(data, "feeder", "space_text"),
        ),
        bus_break=BusBreakSettings(
            layer=_read_text(data, "bus_break", "layer"),
            tilde_block=_read_text(data, "bus_break", "tilde_block"),
            tilde_state_horizontal_bus=_read_text(data, "bus_break", "tilde_state_horizontal_bus"),
            tilde_state_vertical_bus=_read_text(data, "bus_break", "tilde_state_vertical_bus"),
            tilde_flip_horizontal_bus=_read_text(data, "bus_break", "tilde_flip_horizontal_bus"),
            tilde_flip_vertical_bus=_read_text(data, "bus_break", "tilde_flip_vertical_bus"),
            bracket_flip_horizontal_bus=_read_text(data, "bus_break", "bracket_flip_horizontal_bus"),
            bracket_flip_vertical_bus=_read_text(data, "bus_break", "bracket_flip_vertical_bus"),
            bracket_block=_read_text(data, "bus_break", "bracket_block"),
            bracket_state_horizontal_bus=_read_text(data, "bus_break", "bracket_state_horizontal_bus"),
            bracket_state_vertical_bus=_read_text(data, "bus_break", "bracket_state_vertical_bus"),
            bracket_gap=_read_number(data, "bus_break", "bracket_gap"),
            label_attribute_horizontal_bus=_read_text(data, "bus_break", "label_attribute_horizontal_bus"),
            column_cut_label=_read_text(data, "bus_break", "column_cut_label"),
            continued_from_below_label=_read_text(data, "bus_break", "continued_from_below_label"),
            continued_from_above_label=_read_text(data, "bus_break", "continued_from_above_label"),
            label_attribute_vertical_bus=_read_text(data, "bus_break", "label_attribute_vertical_bus"),
            page_reference=_read_text(data, "bus_break", "page_reference"),
            to_label=_read_text(data, "bus_break", "to_label"),
            from_label=_read_text(data, "bus_break", "from_label"),
        ),
    )


def _read_mounting_blocks(data) -> dict:
    blocks = _read_value(data, "main_breaker", "blocks")
    if not isinstance(blocks, dict):
        raise SettingsError('Setting "main_breaker.blocks" must list a block per mounting.')
    for mounting in ("fixed", "draw-out"):
        if not isinstance(blocks.get(mounting), str) or not blocks[mounting]:
            raise SettingsError(f'Setting "main_breaker.blocks" needs a block for "{mounting}".')
    return dict(blocks)


def _read_value(data, group, key):
    try:
        return data[group][key]
    except (KeyError, TypeError):
        raise SettingsError(f'Missing setting "{group}.{key}" in layout_settings.json.')


def _check_number(value, where) -> float:
    # bool is a kind of int in Python, so rule it out explicitly (true/false is a typo here).
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingsError(f'Setting "{where}" must be a number, got {value!r}.')
    if value < 0:
        raise SettingsError(f'Setting "{where}" must not be negative, got {value}.')
    return float(value)


def _read_number(data, group, key) -> float:
    return _check_number(_read_value(data, group, key), f"{group}.{key}")


def _read_number_list(data, group, key) -> tuple[float, ...]:
    value = _read_value(data, group, key)
    if not isinstance(value, list) or not value:
        raise SettingsError(f'Setting "{group}.{key}" must be a list of numbers.')
    return tuple(_check_number(item, f"{group}.{key}") for item in value)


def _read_text(data, group, key) -> str:
    value = _read_value(data, group, key)
    if not isinstance(value, str) or not value:
        raise SettingsError(f'Setting "{group}.{key}" must be some text, got {value!r}.')
    return value


def _read_text_lines(data, group, key) -> tuple[str, ...]:
    """Text written as a list, one entry per line on the drawing."""
    value = _read_value(data, group, key)
    if not isinstance(value, list) or not value or not all(isinstance(line, str) and line for line in value):
        raise SettingsError(f'Setting "{group}.{key}" must be a list of text lines, got {value!r}.')
    return tuple(value)


def _read_true_false(data, group, key) -> bool:
    value = _read_value(data, group, key)
    if not isinstance(value, bool):
        raise SettingsError(f'Setting "{group}.{key}" must be true or false, got {value!r}.')
    return value
