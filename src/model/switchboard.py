"""Project data: a switchboard and its sections.

For Milestone 1 each section's size is a typed-in placeholder. Later it will be
calculated from the real block footprints in catalog/.
"""
from dataclasses import dataclass, field


@dataclass
class Section:
    name: str
    # Width from the outermost component on the left to the outermost component on the
    # right. The dividing lines are NOT included; the layout engine adds that clearance.
    width: float
    # Height from the top of the highest component to the bottom of the lowest one.
    height: float
    # Start this section on a new page, even if it would fit on the current one.
    push_to_next_page: bool = False
    # Keep this section on the same page as the section after it.
    link_with_next: bool = False


@dataclass
class Switchboard:
    name: str
    # Order matters: it is the order of sections along the main bus, left to right.
    sections: list[Section] = field(default_factory=list)
