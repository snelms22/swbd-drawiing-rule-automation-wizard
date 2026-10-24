"""What a section holds (docs/DECISIONS.md, 2026-10-09 "What a section holds").

A section has an ABOVE part (above the main bus) and a BELOW part. Each part holds one
arrangement, or nothing. Any section may also hold a tie breaker.

    SectionContents
      above: None | MainBreaker | IncomingFeed | LineSideBreaker | SingleBreaker | GroupMounted
      below: None | MainBreaker | IncomingFeed | LineSideBreaker | SingleBreaker | GroupMounted
      tie:   None | TieBreaker

A main breaker and its incoming feed are separate things (decision 2026-10-22, option B):
the IncomingFeed is where power comes in (the termination, and what hangs on the line side
before any breaker: voltage taps now; CPTs, relays and load-bank ties later); the
MainBreaker holds the breaker itself (and its CTs, on the load side). A main's feed is
either in its own riser (`feed`), or an IncomingFeed standing as a part by itself in the
section next to it (`feed` None, `feed_from` its id). A feed by itself that no main breaker
points at is "main lugs only": it runs straight to the main bus (see src/model/feeds.py).
A LineSideBreaker (a load-bank breaker, like 52-LBBA in Sabey-011475) is fed from the line
side of an incoming feed in the section next to it, before that feed's main breaker.

Main breakers and single breakers have two feed directions (decision 2026-10-13), each
"top" or "bottom":
    breaker_feed:      which end of the breaker the cables connect to
                       ("a bottom-fed breaker")
    termination_feed:  which side of the cabinet the cables come in from
                       ("fed from a top termination")
Left empty, both are the side away from the main bus (top above the bus, bottom below
it): the straight run. When the two differ, the bus makes a U-turn between the breaker
and the termination. Both will later feed the breaker part-number configurator.

GroupMounted is a list of levels counted OUTWARD from the main bus (level 1 is nearest
the bus). A level is either:
    TwinLevel:   a left and a right slot on the same level
    SingleLevel: one slot. Sides alternate automatically; `flipped` swaps one level.
A slot is a Breaker, a Provision (room left for a future breaker: the bus is tapped
out to it and a note says what it is for, e.g. "PROVISION FOR" / "3VA62 250AF"), or a
Space (an unused position: tapped out the same way, labelled just "SPACE"; 2026-10-19).
"""
import uuid
from dataclasses import dataclass, field


@dataclass
class Breaker:
    label: str                      # e.g. "52-F1"; sections have no names, components do
    block: str = ""                 # block name from blocks/ (chosen once blocks are catalogued)
    # Values for the block's attributes, by tag. Empty or missing = the block's default.
    attributes: dict[str, str] = field(default_factory=dict)
    # Communication module, e.g. "Siemens COM190"; "" = none (decision 2026-10-21; the
    # choices are in config/devices.json). What it draws is worked out later.
    comms_module: str = ""


@dataclass
class CurrentTransformers:
    """A CT set measuring current for a power meter (decision 2026-10-21). The engineer
    picks what it measures (by putting it on a main, single breaker, tie, or the base of a
    group-mounted bus), the meter and the ratio; the program places it wherever it fits."""
    meter_id: str = ""              # the PowerMeter it feeds; "" = not chosen yet
    ratio: str = ""                 # e.g. "5000:5A"
    attributes: dict[str, str] = field(default_factory=dict)   # other CT block attributes
    on_main_bus: bool = False       # mains only: on the main bus after the mains have joined


def new_device_id() -> str:
    """A short id that stays with a device, so CTs keep pointing at the right meter even
    when meters are added, removed or renumbered."""
    return uuid.uuid4().hex[:8]


@dataclass
class PowerMeter:
    """A power meter mounted in a section (decision 2026-10-21). Named PM-s-n (s = its section,
    n through the lineup, decision 2026-10-23); the model is labelled with its brand, e.g. "Janitza UMG 801"."""
    model: str = ""
    id: str = field(default_factory=new_device_id)
    remote_display: bool = False    # a remote display (RD-s-n) on its USB (decision 2026-10-23)


@dataclass
class VoltageTap:
    """A fused voltage tap for a power meter's voltage input (decision 2026-10-22): on a
    feed (a main breaker's line side) or on a main breaker's load side, between the
    breaker and the main bus (decision 2026-10-23). Its fuse is numbered FA-s-n (s = the tap's section, n through
    the lineup) and is drawn on the device pages; the 3-line shows the tap and
    "TO FA-s-n SHEET #"."""
    meter_id: str = ""              # the PowerMeter it feeds; "" = not chosen yet
    # Values for its fuse block's attributes, e.g. the rating (decision 2026-10-23).
    fuse_attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class IncomingFeed:
    """Where power comes into a riser: the termination (input block) and the line side."""
    # Values for the input block's attributes, by tag (e.g. LOCATION, TERMINATION).
    input_attributes: dict[str, str] = field(default_factory=dict)
    termination_feed: str = ""      # "top" / "bottom"; "" = the side away from the bus
    voltage_taps: list[VoltageTap] = field(default_factory=list)
    # Stays with the feed, so a breaker (or a load-bank tie) in another section can point
    # at it later.
    id: str = field(default_factory=new_device_id)


@dataclass
class Provision:
    info: str = ""                  # one line from the engineer, e.g. "3VA62 250AF"


@dataclass
class Space:
    """An unused position: bussed like a Provision, labelled "SPACE" (decision 2026-10-19)."""


Slot = Breaker | Provision | Space


# Main breaker mounting options; each maps to a library block in config.
FIXED = "fixed"
DRAW_OUT = "draw-out"
MOUNTINGS = [FIXED, DRAW_OUT]

# Feed directions for main breakers and single breakers.
TOP = "top"
BOTTOM = "bottom"
FEED_DIRECTIONS = [TOP, BOTTOM]


@dataclass
class MainBreaker:
    breaker: Breaker
    mounting: str = FIXED           # "fixed" or "draw-out"
    breaker_feed: str = ""          # "top" / "bottom"; "" = the side away from the bus
    cts: CurrentTransformers | None = None
    # Its incoming feed when it is in this riser; None when it comes from a feed in another
    # section (`feed_from` = that IncomingFeed's id; "" = not chosen yet).
    feed: IncomingFeed | None = field(default_factory=IncomingFeed)
    feed_from: str = ""
    # Voltage taps on its load side, between the breaker and the main bus (decision
    # 2026-10-23). Line-side taps belong to its feed.
    load_side_taps: list[VoltageTap] = field(default_factory=list)


@dataclass
class LineSideBreaker:
    """A breaker fed from the line side of an incoming feed (decision 2026-10-22), e.g. a
    load-bank breaker: tied into the feed's run between its termination and its main
    breaker, with its own output termination (e.g. a bus duct "BY OTHERS")."""
    breaker: Breaker
    mounting: str = FIXED           # "fixed" or "draw-out", same blocks as main breakers
    # Values for the output block's attributes, by tag (e.g. LOCATION, TERMINATION).
    output_attributes: dict[str, str] = field(default_factory=dict)
    fed_from: str = ""              # the IncomingFeed's id; "" = not chosen yet


@dataclass
class SingleBreaker:
    breaker: Breaker
    # Values for the output block's attributes, by tag (e.g. LOCATION, TERMINATION).
    output_attributes: dict[str, str] = field(default_factory=dict)
    breaker_feed: str = ""          # "top" / "bottom"; "" = the side away from the bus
    termination_feed: str = ""      # "top" / "bottom"; "" = the side away from the bus
    cts: CurrentTransformers | None = None
    mounting: str = FIXED           # "fixed" or "draw-out", same blocks as main breakers (2026-10-23)


@dataclass
class TwinLevel:
    left: Slot
    right: Slot


@dataclass
class SingleLevel:
    slot: Slot
    flipped: bool = False           # put this level on the other side from the automatic one


@dataclass
class GroupMounted:
    levels: list[TwinLevel | SingleLevel] = field(default_factory=list)
    base_cts: CurrentTransformers | None = None     # CTs at the base of the vertical bus


Arrangement = MainBreaker | IncomingFeed | LineSideBreaker | SingleBreaker | GroupMounted


@dataclass
class TieBreaker:
    breaker: Breaker
    bus_steps: str = "down"         # "up" or "down": where the bus goes after the tie
    mounting: str = FIXED           # "fixed" or "draw-out", same blocks as main breakers
    cts: CurrentTransformers | None = None


@dataclass
class SectionContents:
    above: Arrangement | None = None
    below: Arrangement | None = None
    tie: TieBreaker | None = None
    # Devices mounted in this section (decision 2026-10-21).
    power_meters: list[PowerMeter] = field(default_factory=list)


def side_away_from_bus(part: str) -> str:
    """The cabinet side a part reaches toward: "top" above the main bus, "bottom" below."""
    return TOP if part == "above" else BOTTOM


def feed_directions(arrangement, part: str) -> tuple[str, str]:
    """(breaker feed, termination feed) of a main or single breaker in `part` ("above" or
    "below"), with empty values filled in as the side away from the bus. A main breaker's
    termination is its incoming feed's."""
    away = side_away_from_bus(part)
    if isinstance(arrangement, MainBreaker):
        # A main fed from another section: its feed's run is worked out with that feed.
        termination = arrangement.feed.termination_feed if arrangement.feed is not None else ""
    else:
        termination = arrangement.termination_feed
    return arrangement.breaker_feed or away, termination or away
