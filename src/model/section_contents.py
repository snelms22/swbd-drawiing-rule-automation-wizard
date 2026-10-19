"""What a section holds (docs/DECISIONS.md, 2026-10-09 "What a section holds").

A section has an ABOVE part (above the main bus) and a BELOW part. Each part holds one
arrangement, or nothing. Any section may also hold a tie breaker.

    SectionContents
      above: None | MainBreaker | SingleBreaker | GroupMounted
      below: None | MainBreaker | SingleBreaker | GroupMounted
      tie:   None | TieBreaker

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
from dataclasses import dataclass, field


@dataclass
class Breaker:
    label: str                      # e.g. "52-F1"; sections have no names, components do
    block: str = ""                 # block name from blocks/ (chosen once blocks are catalogued)
    # Values for the block's attributes, by tag. Empty or missing = the block's default.
    attributes: dict[str, str] = field(default_factory=dict)


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
    # Values for the input block's attributes, by tag (e.g. LOCATION, TERMINATION).
    input_attributes: dict[str, str] = field(default_factory=dict)
    breaker_feed: str = ""          # "top" / "bottom"; "" = the side away from the bus
    termination_feed: str = ""      # "top" / "bottom"; "" = the side away from the bus


@dataclass
class SingleBreaker:
    breaker: Breaker
    # Values for the output block's attributes, by tag (e.g. LOCATION, TERMINATION).
    output_attributes: dict[str, str] = field(default_factory=dict)
    breaker_feed: str = ""          # "top" / "bottom"; "" = the side away from the bus
    termination_feed: str = ""      # "top" / "bottom"; "" = the side away from the bus


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


Arrangement = MainBreaker | SingleBreaker | GroupMounted


@dataclass
class TieBreaker:
    breaker: Breaker
    bus_steps: str = "down"         # "up" or "down": where the bus goes after the tie
    mounting: str = FIXED           # "fixed" or "draw-out", same blocks as main breakers


@dataclass
class SectionContents:
    above: Arrangement | None = None
    below: Arrangement | None = None
    tie: TieBreaker | None = None


def side_away_from_bus(part: str) -> str:
    """The cabinet side a part reaches toward: "top" above the main bus, "bottom" below."""
    return TOP if part == "above" else BOTTOM


def feed_directions(arrangement, part: str) -> tuple[str, str]:
    """(breaker feed, termination feed) of a main or single breaker in `part` ("above" or
    "below"), with empty values filled in as the side away from the bus."""
    away = side_away_from_bus(part)
    return arrangement.breaker_feed or away, arrangement.termination_feed or away
