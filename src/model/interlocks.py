"""Interlocks between main breakers (decision 2026-10-26). Pure Python.

The engineer marks two main breakers as interlocked: mechanically, electrically or both. The
interlock is kept on ONE of the two mains (`MainBreaker.interlock`, pointing at the other
main by its id): the one it was set on. Both mains' editors show it, and editing it from
either main changes that one record, so the two can never disagree.

For now an interlock is drawn only between mains in sections next to each other, on the
same side of the main bus, and a main is in one interlock at most. Anything else is
reported here in plain words and not drawn.
"""
from dataclasses import dataclass

from src.model.section_contents import Interlock, MainBreaker


@dataclass
class MainPlace:
    main: MainBreaker
    section_index: int      # 0 = section 1
    part: str               # "above" or "below"

    @property
    def name(self) -> str:
        """How the editor and the warnings name it, e.g. "52-M1 (section 2 above)"."""
        return f"{self.main.breaker.label or 'Main breaker'} (section {self.section_index + 1} {self.part})"


@dataclass
class InterlockLink:
    """An interlock that can be drawn: `left` is the main in the lower-numbered section."""
    left: MainPlace
    right: MainPlace
    interlock: Interlock


def mains_in(switchboard) -> list[MainPlace]:
    """Every main breaker in the lineup, in lineup order."""
    found = []
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            arrangement = getattr(section.contents, part)
            if isinstance(arrangement, MainBreaker):
                found.append(MainPlace(arrangement, index, part))
    return found


def interlock_of(switchboard, main) -> tuple[Interlock, str] | None:
    """The interlock `main` is in, and the other main's id; None if it has none. Its own
    record comes first, then one set on another main that points at it."""
    if main.interlock is not None:
        return main.interlock, main.interlock.with_main
    for place in mains_in(switchboard):
        lock = place.main.interlock
        if lock is not None and lock.with_main == main.id:
            return lock, place.main.id
    return None


def set_interlock(switchboard, main, other_id: str, mechanical: bool = False, electrical: bool = False):
    """Interlock `main` with the main whose id is `other_id` ("" = with nothing). Any
    interlock either of them was in before is removed first (one per main for now)."""
    involved = {main.id, other_id} - {""}
    for place in mains_in(switchboard):
        lock = place.main.interlock
        if lock is not None and (place.main.id in involved or lock.with_main in involved):
            place.main.interlock = None
    main.interlock = None
    if other_id:
        main.interlock = Interlock(other_id, mechanical, electrical)


def interlock_links(switchboard) -> tuple[list[InterlockLink], list[str]]:
    """The interlocks that can be drawn, and the problems found, in plain words."""
    places = mains_in(switchboard)
    by_id = {place.main.id: place for place in places}
    links, problems, interlocked = [], [], set()
    for place in places:
        lock = place.main.interlock
        if lock is None:
            continue
        where = f"Section {place.section_index + 1} {place.part} ({place.main.breaker.label or 'main breaker'})"
        other = by_id.get(lock.with_main)
        if other is None or other is place:
            problems.append(f"{where}: the main breaker it is interlocked with no longer exists.")
        elif not (lock.mechanical or lock.electrical):
            problems.append(f"{where}: its interlock with {other.name} is not drawn until it is "
                            f"marked mechanical, electrical or both.")
        elif {place.main.id, other.main.id} & interlocked:
            problems.append(f"{where}: a main breaker can only have one interlock for now; the "
                            f"interlock with {other.name} is not drawn.")
        elif abs(other.section_index - place.section_index) != 1:
            problems.append(f"{where}: it is interlocked with {other.name}, which is not in the "
                            f"section next to it; only interlocks between neighbouring sections "
                            f"are drawn for now.")
        elif other.part != place.part:
            problems.append(f"{where}: it is interlocked with {other.name} on the other side of "
                            f"the main bus; that interlock line is not drawn (it would cross the "
                            f"main bus).")
        else:
            left, right = sorted((place, other), key=lambda p: p.section_index)
            links.append(InterlockLink(left, right, lock))
            interlocked |= {place.main.id, other.main.id}
    return links, problems
