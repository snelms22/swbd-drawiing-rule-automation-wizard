"""Devices (decision 2026-10-21): the choices the engineer picks from (communication
modules and power meter models, config/devices.json), and how meters and CT sets are named
and numbered through the lineup. Pure Python.

    Meter models:  each model's block and the blocks wired into it (voltage input, one
                   current input per CT set), with the meter marker each input marker
                   lands on (decision 2026-10-22). pairing_problems() checks them.
Device names hold the section the device lives in (decision 2026-10-23): fuse 12 in
section 3 is FA-3-12. Numbers count through the whole lineup; the block holds the prefix
("FA-") and the program fills the rest ("3-12", the device's `code`).

    Power meters:  PM-s-n, n in lineup order; s = the section it is mounted in. Its remote
                   display, if it has one: RD-s-n, n counting displays through the lineup.
    CT sets:       numbered in lineup order: in each section the part above the bus, the
                   part below it, then the tie. Set k in section s has CTs s-(3k-2),
                   s-(3k-1), s-3k and shorting kit STB-s-k.
    Voltage taps:  fuses FA-s-n, n in lineup order (per section: above, below; each feed's
                   taps in the order entered); s = the tap's section, where the fuse lives.
                   A tap feeds a power meter or a power supply (decision 2026-11-05).
    Power supplies: PS-s-n, n in lineup order; s = the section it is mounted in.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from src.layout.settings import SettingsError
from src.model.section_contents import GroupMounted, IncomingFeed, MainBreaker, SingleBreaker


@dataclass(frozen=True)
class InputBlock:
    """A block wired into a device, e.g. a meter's voltage input."""
    block: str
    lands_on: dict          # {this block's marker: the device marker it connects to}
    number_attribute: str = ""   # gets the number of what it comes from (after "FA-", "STB-")
    sheet_attribute: str = ""    # gets the sheet that is on


@dataclass(frozen=True)
class MeterModel:
    name: str                       # what the engineer picks, e.g. "Janitza UMG 801"
    block: str                      # "" = block not built yet
    voltage_input: InputBlock | None
    current_inputs: tuple           # InputBlock per CT set, in the order sets are wired
    number_attribute: str = ""      # gets the meter's number after "PM-"
    usb_marker: str = ""            # where a remote display's USB line starts

    def voltage_terminals(self) -> dict:
        """{phase: meter marker} for wiring a fuse straight to the meter: from the voltage
        input's pairs, whose markers are named V_A, V_B, V_C."""
        if self.voltage_input is None:
            return {}
        return {marker[-1]: target for marker, target in self.voltage_input.lands_on.items()}

    def input_blocks(self) -> list[tuple[str, InputBlock]]:
        """(what it is, the input) for each input, for messages."""
        found = [("voltage input", self.voltage_input)] if self.voltage_input else []
        found += [(f"current input {n}", i) for n, i in enumerate(self.current_inputs, start=1)]
        return found


@dataclass(frozen=True)
class FuseSettings:
    """The fuse a voltage tap feeds, on the device pages (decision 2026-10-23)."""
    block: str
    state: str                      # visibility state it is drawn in (standing up)
    line_markers: dict              # {phase: marker} line side (up)
    load_markers: dict              # {phase: marker} load side (down)
    number_attribute: str           # gets the fuse's number after "FA-"
    layer: str
    wire_layers: dict               # {phase: layer} for the wires the program draws
    # Lying down beside a device whose inputs face sideways, e.g. a power supply (decision
    # 2026-11-05): its state and markers then. "" / None = can't be drawn that way.
    horizontal_state: str = ""
    horizontal_line_markers: dict = None    # {phase: marker} line side (left)
    horizontal_load_markers: dict = None    # {phase: marker} load side (right)


@dataclass(frozen=True)
class RemoteDisplaySettings:
    """A meter's remote display, on its USB (decision 2026-10-23)."""
    block: str
    usb_marker: str
    number_attribute: str           # gets its number after "RD-"
    layer: str
    usb_layer: str                  # the USB line from the meter


@dataclass(frozen=True)
class PowerSupplySettings:
    """The control power supply (decision 2026-11-05): 3-pole, 480 V to 24 V, for now."""
    block: str
    inputs: dict                    # {phase: marker} where its fuse's wires land (A: L1, ...)
    number_attribute: str           # gets its number after "PS-"
    layer: str


@dataclass(frozen=True)
class DeviceSettings:
    comms_modules: list          # e.g. ["Siemens COM190", "Siemens COM800"]
    power_meters: dict           # {model name: MeterModel}
    fuse: FuseSettings | None = None
    remote_display: RemoteDisplaySettings | None = None
    power_supply: PowerSupplySettings | None = None

    @property
    def power_meter_models(self) -> list[str]:
        return list(self.power_meters)

    def device_blocks(self) -> list[str]:
        """Every library block the meters use (for Audit Blocks)."""
        names = []
        for model in self.power_meters.values():
            if model.block:
                names.append(model.block)
                names += [i.block for _, i in model.input_blocks()]
        if self.fuse is not None:
            names.append(self.fuse.block)
        if self.remote_display is not None:
            names.append(self.remote_display.block)
        if self.power_supply is not None:
            names.append(self.power_supply.block)
        return sorted(set(names))


def load_device_settings(path) -> DeviceSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DeviceSettings(
            comms_modules=list(data["comms_modules"]),
            power_meters={name: _meter_model(name, entry) for name, entry in data["power_meters"].items()},
            fuse=_fuse(data["voltage_tap_fuse"]) if "voltage_tap_fuse" in data else None,
            remote_display=RemoteDisplaySettings(**data["remote_display"]) if "remote_display" in data else None,
            power_supply=_power_supply(data["power_supply"]) if "power_supply" in data else None,
        )
    except FileNotFoundError:
        raise SettingsError(f"Settings file not found: {path}")
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise SettingsError(f"{path.name} is missing something or is not valid JSON: {error}")


def _meter_model(name, entry) -> MeterModel:
    def input_block(data):
        return InputBlock(block=str(data["block"]), lands_on={str(k): str(v) for k, v in data["lands_on"].items()},
                          number_attribute=str(data.get("number_attribute", "")),
                          sheet_attribute=str(data.get("sheet_attribute", "")))
    voltage = entry.get("voltage_input")
    return MeterModel(name=name, block=str(entry.get("block", "")),
                      voltage_input=input_block(voltage) if voltage else None,
                      current_inputs=tuple(input_block(i) for i in entry.get("current_inputs", [])),
                      number_attribute=str(entry.get("number_attribute", "")),
                      usb_marker=str(entry.get("usb_marker", "")))


def _fuse(data) -> FuseSettings:
    return FuseSettings(block=str(data["block"]), state=str(data["state"]),
                        line_markers=dict(data["line_markers"]), load_markers=dict(data["load_markers"]),
                        number_attribute=str(data["number_attribute"]), layer=str(data.get("layer", "0")),
                        wire_layers=dict(data["wire_layers"]),
                        horizontal_state=str(data.get("horizontal_state", "")),
                        horizontal_line_markers=dict(data.get("horizontal_line_markers") or {}) or None,
                        horizontal_load_markers=dict(data.get("horizontal_load_markers") or {}) or None)


def _power_supply(data) -> PowerSupplySettings:
    return PowerSupplySettings(block=str(data["block"]), inputs=dict(data["inputs"]),
                               number_attribute=str(data["number_attribute"]),
                               layer=str(data.get("layer", "0")))


TOLERANCE = 0.05     # markers closer than this count as the same point


def pairing_problems(model: MeterModel, markers: dict) -> list[str]:
    """Check a meter model's pairs against its blocks' markers: every marker exists, and
    with each input block placed so its first pair connects, every other pair connects too.
    `markers` is {block name: {marker name: (x, y)}} for the blocks read. Plain words."""
    if not model.block or model.block not in markers:
        return []                       # not built yet, or not read (reported elsewhere)
    meter = markers[model.block]
    problems = []
    for what, connected in model.input_blocks():
        if connected.block not in markers:
            continue
        own = markers[connected.block]
        where = f"{model.name} {what} ({connected.block} on {model.block})"
        missing_own = [m for m in connected.lands_on if m not in own]
        if missing_own:
            problems.append(f"{where}: {connected.block} has no marker {', '.join(missing_own)}.")
        usable = [(m, t) for m, t in connected.lands_on.items() if m in own and t in meter]
        if not usable:
            problems.append(f"{where}: none of its markers can be matched to the meter's.")
            continue
        first, first_target = usable[0]
        dx = meter[first_target][0] - own[first][0]
        dy = meter[first_target][1] - own[first][1]
        for marker, target in connected.lands_on.items():
            if marker not in own:
                continue
            x, y = own[marker][0] + dx, own[marker][1] + dy
            if target not in meter:
                there = [name for name, (mx, my) in meter.items()
                         if abs(mx - x) <= TOLERANCE and abs(my - y) <= TOLERANCE]
                hint = f" The marker where it should be is named {there[0]}." if there else ""
                problems.append(f"{where}: {model.block} has no marker {target} (for {marker}).{hint}")
            elif abs(meter[target][0] - x) > TOLERANCE or abs(meter[target][1] - y) > TOLERANCE:
                problems.append(f"{where}: {marker} would land at ({x:g}, {y:g}) but {target} is at "
                                f"({meter[target][0]:g}, {meter[target][1]:g}); they don't line up.")
    return problems


@dataclass
class MeterInfo:
    number: int             # n of PM-s-n, through the lineup
    section_number: int     # s: where it is mounted
    meter: object           # the PowerMeter
    display_number: int = 0  # n of its remote display RD-s-n (through the lineup); 0 = none

    @property
    def display_code(self) -> str:
        """What the program fills in after the remote display block's "RD-": "s-n"."""
        return f"{self.section_number}-{self.display_number}"

    @property
    def code(self) -> str:
        """What the program fills in after the block's "PM-": "s-n"."""
        return f"{self.section_number}-{self.number}"

    @property
    def name(self) -> str:
        return f"PM-{self.code}"


@dataclass
class CtSetInfo:
    number: int             # 1, 2, ... (CT numbers 3n-2..3n, shorting kit n)
    where: str              # e.g. "Section 2 above (52-M1)"
    cts: object             # the CurrentTransformers
    section_number: int     # 1, 2, ...
    part: str               # "above", "below" or "tie"

    @property
    def ct_numbers(self) -> list[str]:
        """The three CTs' numbers, "s-n"."""
        return [f"{self.section_number}-{3 * self.number - 2 + i}" for i in range(3)]

    @property
    def code(self) -> str:
        """The shorting kit's number after "STB-": "s-k"."""
        return f"{self.section_number}-{self.number}"

    @property
    def shorting_kit(self) -> str:
        return f"STB-{self.code}"


def meters_in(switchboard) -> list[MeterInfo]:
    found, displays = [], 0
    for number, section in enumerate(switchboard.sections, start=1):
        for meter in section.contents.power_meters:
            displays += int(meter.remote_display)
            found.append(MeterInfo(len(found) + 1, number, meter, displays if meter.remote_display else 0))
    return found


@dataclass
class PowerSupplyInfo:
    number: int             # n of PS-s-n, through the lineup
    section_number: int     # s: where it is mounted
    supply: object          # the PowerSupply

    @property
    def code(self) -> str:
        """What the program fills in after the block's "PS-": "s-n"."""
        return f"{self.section_number}-{self.number}"

    @property
    def name(self) -> str:
        return f"PS-{self.code}"


def power_supplies_in(switchboard) -> list[PowerSupplyInfo]:
    found = []
    for number, section in enumerate(switchboard.sections, start=1):
        for supply in section.contents.power_supplies:
            found.append(PowerSupplyInfo(len(found) + 1, number, supply))
    return found


def ct_sets_in(switchboard) -> list[CtSetInfo]:
    found = []
    for number, section in enumerate(switchboard.sections, start=1):
        contents = section.contents
        for part in ("above", "below"):
            arrangement = getattr(contents, part)
            if isinstance(arrangement, (MainBreaker, SingleBreaker)) and arrangement.cts:
                label = arrangement.breaker.label or "breaker"
                found.append(CtSetInfo(len(found) + 1, f"Section {number} {part} ({label})", arrangement.cts,
                                       number, part))
            elif isinstance(arrangement, GroupMounted) and arrangement.base_cts:
                found.append(CtSetInfo(len(found) + 1, f"Section {number} {part} (group-mounted base)",
                                       arrangement.base_cts, number, part))
        if contents.tie is not None and contents.tie.cts:
            label = contents.tie.breaker.label or "tie"
            found.append(CtSetInfo(len(found) + 1, f"Section {number} tie ({label})", contents.tie.cts,
                                   number, "tie"))
    return found


# Which side of a main breaker a voltage tap is on (decision 2026-10-23).
LINE_SIDE = "line"
LOAD_SIDE = "load"


@dataclass
class TapInfo:
    number: int             # n of FA-s-n, through the lineup
    where: str              # e.g. "Section 1 above (feed of 52-M1)"
    tap: object             # the VoltageTap
    section_number: int
    part: str               # "above" or "below"
    index: int              # its place in its list of taps (the feed's, or the main's load side)
    side: str = LINE_SIDE   # LINE_SIDE (on a feed) or LOAD_SIDE (a main's load side)

    @property
    def code(self) -> str:
        """What the program fills in after the block's "FA-": "s-n"."""
        return f"{self.section_number}-{self.number}"

    @property
    def fuse(self) -> str:
        return f"FA-{self.code}"


def voltage_taps_in(switchboard) -> list[TapInfo]:
    """Every voltage tap, numbered through the lineup. In each part the feed's (line-side)
    taps come first, then a main's load-side taps; the 3-line reads them in that order."""
    found = []
    for number, section in enumerate(switchboard.sections, start=1):
        for part in ("above", "below"):
            arrangement = getattr(section.contents, part)
            lists = []
            if isinstance(arrangement, MainBreaker):
                label = arrangement.breaker.label or "main breaker"
                if arrangement.feed is not None:
                    lists.append((arrangement.feed.voltage_taps, f"feed of {label}", LINE_SIDE))
                lists.append((arrangement.load_side_taps, f"load side of {label}", LOAD_SIDE))
            elif isinstance(arrangement, IncomingFeed):
                lists.append((arrangement.voltage_taps, "incoming feed", LINE_SIDE))
            for taps, where, side in lists:
                for index, tap in enumerate(taps):
                    found.append(TapInfo(len(found) + 1, f"Section {number} {part} ({where})",
                                         tap, number, part, index, side))
    return found


def meter_name(switchboard, meter_id: str) -> str:
    """The meter's name (e.g. "PM-3-1"), or "" if there is no such meter."""
    for info in meters_in(switchboard):
        if info.meter.id == meter_id:
            return info.name
    return ""


def tap_target_names(switchboard) -> dict[str, str]:
    """{device id: name} for everything a voltage tap can feed: power meters, then power
    supplies (decision 2026-11-05)."""
    names = {info.meter.id: info.name for info in meters_in(switchboard)}
    names.update({info.supply.id: info.name for info in power_supplies_in(switchboard)})
    return names


def device_problems(switchboard) -> list[str]:
    """Warnings about CTs and meters, in plain words."""
    problems = []
    for ct_set in ct_sets_in(switchboard):
        if not ct_set.cts.meter_id:
            problems.append(f"{ct_set.where}: choose the power meter its CTs feed.")
        elif not meter_name(switchboard, ct_set.cts.meter_id):
            problems.append(f"{ct_set.where}: its CTs feed a power meter that no longer exists.")
        if ct_set.cts.on_main_bus:
            problems.append(f"{ct_set.where}: CTs on the main bus after the mains join are not drawn "
                            f"yet; they are drawn on the main's riser.")
    targets = tap_target_names(switchboard)
    taps = voltage_taps_in(switchboard)
    for tap in taps:
        if not tap.tap.feeds:
            problems.append(f"{tap.where}: choose the power meter or power supply voltage tap {tap.fuse} feeds.")
        elif tap.tap.feeds not in targets:
            problems.append(f"{tap.where}: voltage tap {tap.fuse} feeds a device that no longer exists.")
    for info in power_supplies_in(switchboard):
        feeding = [tap.fuse for tap in taps if tap.tap.feeds == info.supply.id]
        if not feeding:
            problems.append(f"{info.name} (section {info.section_number}): no voltage tap feeds it yet; "
                            f"pick it in a voltage tap's \"Feeds\" list.")
        elif len(feeding) > 1:
            problems.append(f"{info.name} is fed by more than one voltage tap ({', '.join(feeding)}); "
                            f"only {feeding[0]} is wired to it.")
    for info in meters_in(switchboard):
        if not info.meter.model:
            problems.append(f"{info.name} (section {info.section_number}): choose its model.")
    return problems
