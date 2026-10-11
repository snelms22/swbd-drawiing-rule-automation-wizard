"""What a section holds (docs/DECISIONS.md, 2026-10-09 "What a section holds").

A section has an ABOVE part (above the main bus) and a BELOW part. Each part holds one
arrangement, or nothing. Any section may also hold a tie breaker.

    SectionContents
      above: None | MainBreaker | SingleBreaker | GroupMounted
      below: None | MainBreaker | SingleBreaker | GroupMounted
      tie:   None | TieBreaker

A MainBreaker in the above part is fed from the top; in the below part, from the bottom.

GroupMounted is a list of levels counted OUTWARD from the main bus (level 1 is nearest
the bus). A level is either:
    TwinLevel:   a left and a right slot on the same level
    SingleLevel: one slot. Sides alternate automatically; `flipped` swaps one level.
A slot is a Breaker or a Space (an empty position, e.g. "PROVISION FOR 3VA41").
"""
from dataclasses import dataclass, field


@dataclass
class Breaker:
    label: str                      # e.g. "52-F1"; sections have no names, components do
    block: str = ""                 # block name from blocks/ (chosen once blocks are catalogued)
    ratings: dict[str, str] = field(default_factory=dict)   # values for the block's attributes


@dataclass
class Space:
    text: str = "SPACE"             # e.g. "PROVISION FOR 3VA41 SIEMENS CB"


Slot = Breaker | Space


@dataclass
class MainBreaker:
    breaker: Breaker


@dataclass
class SingleBreaker:
    breaker: Breaker


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


@dataclass
class SectionContents:
    above: Arrangement | None = None
    below: Arrangement | None = None
    tie: TieBreaker | None = None
