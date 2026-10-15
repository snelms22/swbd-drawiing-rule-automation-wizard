"""Project data: a switchboard and its sections.

Sections have no names: on the drawing they are "SECTION 1", "SECTION 2", ... by their
position in the lineup. Names like "52-F1" belong to components, not sections.

A section's size is not typed in; it is worked out from its contents
(src/layout/section_builder.py).
"""
from dataclasses import dataclass, field

from src.model.section_contents import SectionContents


@dataclass
class Section:
    # What is above the main bus, below it, and an optional tie breaker.
    contents: SectionContents = field(default_factory=SectionContents)
    # Start this section on a new page, even if it would fit on the current one.
    push_to_next_page: bool = False
    # Keep this section on the same page as the section after it.
    link_with_next: bool = False


@dataclass
class Switchboard:
    name: str
    # Order matters: it is the order of sections along the main bus, left to right.
    sections: list[Section] = field(default_factory=list)


def new_switchboard() -> Switchboard:
    """What the app opens with, and what File > New makes: one empty section (decision
    2026-10-12). Saved projects are opened with File > Open; ready-made ones, like the
    sample, with File > Open from Library."""
    return Switchboard(name="New switchboard", sections=[Section()])
