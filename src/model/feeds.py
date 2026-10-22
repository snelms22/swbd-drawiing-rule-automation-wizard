"""Incoming feeds standing on their own (decision 2026-10-22, option B step 2). Pure Python.

A section part ("above" / "below") may hold an IncomingFeed by itself. What it feeds is
worked out from the lineup, not entered twice:
- a main breaker whose `feed_from` is the feed's id: the feed crosses into that main;
- nothing points at it: main lugs only, the feed's riser runs straight to the main bus.

For now a feed may only cross into a main breaker in the section right next to it, on the
same side of the main bus, with both run straight (fed from the side away from the bus).
Everything else is reported here in plain words and not drawn.

A line-side breaker (load bank) is fed from a feed's line side. For now that feed must be a
main breaker's own feed (in its riser), in the section next to it, on the same side of the
bus, run straight; and one line-side breaker per feed.
"""
from dataclasses import dataclass

from src.model.section_contents import (
    IncomingFeed, LineSideBreaker, MainBreaker, feed_directions, side_away_from_bus,
)


@dataclass
class FeedPlace:
    feed: IncomingFeed
    section_index: int      # 0 = section 1
    part: str               # "above" or "below"

    @property
    def where(self) -> str:
        return f"Section {self.section_index + 1} {self.part}"


@dataclass
class FeedLink:
    """A standalone feed crossing into the main breaker it feeds."""
    feed: FeedPlace
    main: MainBreaker
    main_section_index: int
    main_part: str


def standalone_feeds(switchboard) -> list[FeedPlace]:
    """Every incoming feed that is a part by itself, in lineup order."""
    found = []
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            arrangement = getattr(section.contents, part)
            if isinstance(arrangement, IncomingFeed):
                found.append(FeedPlace(arrangement, index, part))
    return found


def feed_links(switchboard) -> tuple[list[FeedLink], list[str]]:
    """The feeds that cross into a main breaker (only those that can be drawn), and the
    problems found, in plain words."""
    places = {place.feed.id: place for place in standalone_feeds(switchboard)}
    links, problems, used = [], [], set()
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            main = getattr(section.contents, part)
            if not isinstance(main, MainBreaker) or main.feed is not None:
                continue
            where = f"Section {index + 1} {part} ({main.breaker.label or 'main breaker'})"
            place = places.get(main.feed_from)
            if not main.feed_from:
                problems.append(f"{where}: choose its incoming feed.")
            elif place is None:
                problems.append(f"{where}: its incoming feed no longer exists.")
            elif place.feed.id in used:
                problems.append(f"{where}: its incoming feed ({place.where}) already feeds another "
                                f"main breaker.")
            elif abs(place.section_index - index) != 1:
                problems.append(f"{where}: its incoming feed is in section {place.section_index + 1}; "
                                f"only a feed in the section next to it is drawn for now.")
            elif place.part != part:
                problems.append(f"{where}: its incoming feed is {place.part} the main bus; a feed on "
                                f"the other side of the bus is not drawn yet.")
            elif feed_directions(main, part)[0] != side_away_from_bus(part):
                problems.append(f"{where}: a main breaker fed from another section must be fed on the "
                                f"side away from the bus for now.")
            else:
                used.add(place.feed.id)
                links.append(FeedLink(place, main, index, part))
                if place.feed.termination_feed not in ("", side_away_from_bus(part)):
                    problems.append(f"{place.where}: a feed whose bus U-turns is not drawn yet; it is "
                                    f"drawn fed from the {side_away_from_bus(part)}.")
    for place in places.values():
        if place.feed.id not in used and place.feed.termination_feed not in ("", side_away_from_bus(place.part)):
            problems.append(f"{place.where}: a feed whose bus U-turns is not drawn yet; it is drawn "
                            f"fed from the {side_away_from_bus(place.part)}.")
    return links, problems


@dataclass
class AnyFeed:
    """Any incoming feed in the lineup: a part by itself, or a main breaker's own."""
    feed: IncomingFeed
    section_index: int
    part: str
    main: MainBreaker | None     # the main breaker whose riser it is in; None = by itself

    @property
    def where(self) -> str:
        if self.main is not None:
            return f"Feed of {self.main.breaker.label or 'the main breaker'}, section {self.section_index + 1} {self.part}"
        return f"Incoming feed, section {self.section_index + 1} {self.part}"


def all_feeds(switchboard) -> list[AnyFeed]:
    found = []
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            arrangement = getattr(section.contents, part)
            if isinstance(arrangement, IncomingFeed):
                found.append(AnyFeed(arrangement, index, part, None))
            elif isinstance(arrangement, MainBreaker) and arrangement.feed is not None:
                found.append(AnyFeed(arrangement.feed, index, part, arrangement))
    return found


@dataclass
class LineSideLink:
    """A line-side breaker tied into a main breaker's own feed in the next section."""
    breaker: LineSideBreaker
    section_index: int
    part: str
    feed: AnyFeed               # its .main is the main breaker whose riser it ties into


def line_side_links(switchboard) -> tuple[list[LineSideLink], list[str]]:
    """The line-side breakers that can be drawn, and the problems found, in plain words."""
    feeds = {found.feed.id: found for found in all_feeds(switchboard)}
    links, problems, used = [], [], set()
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            breaker = getattr(section.contents, part)
            if not isinstance(breaker, LineSideBreaker):
                continue
            where = f"Section {index + 1} {part} ({breaker.breaker.label or 'line-side breaker'})"
            found = feeds.get(breaker.fed_from)
            if not breaker.fed_from:
                problems.append(f"{where}: choose the feed it is fed from.")
            elif found is None:
                problems.append(f"{where}: the feed it is fed from no longer exists.")
            elif found.main is None:
                problems.append(f"{where}: a line-side breaker on an incoming feed by itself is not "
                                f"drawn yet; pick a main breaker's own feed.")
            elif found.feed.id in used:
                problems.append(f"{where}: {found.where.lower()} already has a line-side breaker; "
                                f"only one is drawn for now.")
            elif abs(found.section_index - index) != 1:
                problems.append(f"{where}: its feed is in section {found.section_index + 1}; only a "
                                f"feed in the section next to it is drawn for now.")
            elif found.part != part:
                problems.append(f"{where}: its feed is {found.part} the main bus; a feed on the other "
                                f"side of the bus is not drawn yet.")
            elif feed_directions(found.main, part) != (side_away_from_bus(part),) * 2:
                problems.append(f"{where}: the main breaker it ties into must be fed straight (breaker "
                                f"and termination from the {side_away_from_bus(part)}) for now.")
            else:
                used.add(found.feed.id)
                links.append(LineSideLink(breaker, index, part, found))
    return links, problems


def feeds_pointed_at(switchboard) -> set[str]:
    """Ids of the standalone feeds some main breaker says it is fed from (drawable or not).
    Such a feed is never drawn as main lugs only."""
    return {getattr(section.contents, part).feed_from
            for section in switchboard.sections for part in ("above", "below")
            if isinstance(getattr(section.contents, part), MainBreaker)
            and getattr(section.contents, part).feed is None}


def main_fed_by(switchboard, feed_id: str):
    """(section index, part, MainBreaker) of the main breaker a standalone feed feeds, or
    None (main lugs only)."""
    for index, section in enumerate(switchboard.sections):
        for part in ("above", "below"):
            main = getattr(section.contents, part)
            if isinstance(main, MainBreaker) and main.feed is None and main.feed_from == feed_id:
                return index, part, main
    return None
