"""Surface mixin for `series` and `parallel` (EA5); supplies and cables are its two bases."""

from functools import cached_property
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._cable import Cables
from fransys_author.surface._ends import Parallel, branches, is_bridge, width_of
from fransys_author.surface._pairing import Ends, PartFacts, pair
from fransys_author.surface._supplies import Supplies
from fransys_author.surface._wire import Colour, wiring_for

if TYPE_CHECKING:
    from .design import Design

_MINIMUM = 2


def _width(design: Design, elements: tuple[object, ...]) -> int:
    for element in elements:
        width = width_of(design, element)
        if width is not None:
            return width
    msg = "name a supply, a rail or a function with poles to set the width"
    raise AuthorError(msg)


def _entered(found: list[Ends], element: object, before: tuple[object, ...]) -> list[Ends]:
    """A strip after a cable is entered from its field side: its outer ends are the line ends."""
    if before and is_bridge(before[0]) and getattr(element, "_enters_from_field", False):
        return [Ends(e.load, e.line, e.pe) for e in found]
    return found


def _resolve(design: Design, elements: tuple[object, ...], width: int) -> list[list[Ends]]:
    """The ends of every element; a bridge has none and needs a plain element on each side."""
    last = len(elements) - 1
    found: list[list[Ends]] = []
    for i, element in enumerate(elements):
        if is_bridge(element):
            beside = [elements[j] for j in (i - 1, i + 1) if 0 <= j <= last]
            if len(beside) < _MINIMUM or any(is_bridge(other) for other in beside):
                msg = "a cable sits between two elements that are not cables"
                raise AuthorError(msg)
            found.append([])
        else:
            found.append(_entered(branches(design, element, width), element, elements[i - 1 : i]))
    return found


def _wire_pairs(maker, found: list[list[Ends]], elements: tuple[object, ...]) -> None:  # noqa: ANN001 -- the engine's Wiring
    for i in range(len(elements) - 1):
        for a in found[i]:
            for b in found[i + 1]:
                for port_a, port_b in pair(a.load, b.line):
                    maker(port_a, port_b)


def _land_bridges(design: Design, elements: tuple[object, ...], found: list[list[Ends]]) -> None:
    """Hand each bridge its two neighbours and their ends."""
    for i, element in enumerate(elements):
        if is_bridge(element):
            before, after = (elements[i - 1], found[i - 1][0]), (elements[i + 1], found[i + 1][0])
            element._series_between(design, before, after)


class Series(Supplies, Cables):
    """The calls of this mixin: `series` and `parallel`."""

    @cached_property
    def _pairing_facts(self: Design) -> PartFacts:
        """The part facts of this design, indexed once (poles, sides, conductor marks)."""
        return PartFacts(self.library, self._engine._design.draft())

    def series(
        self: Design,
        *elements: object,
        wire: tuple[Colour, float],
    ) -> None:
        """Wire the elements end to end: each one's load to the next one's line, one wire per pole.

        Does not create devices; does not cross a unit's boundary (use mate).
        Does not decide the drawing.
        """
        if len(elements) < _MINIMUM:
            msg = f"d.series joins at least {_MINIMUM} elements, got {len(elements)}"
            raise AuthorError(msg)
        maker = wiring_for(self, wire)
        found = _resolve(self, elements, _width(self, elements))
        _wire_pairs(maker, found, elements)
        _land_bridges(self, elements, found)

    def parallel(self: Design, *members: object) -> Parallel:
        """Group `members` so a series puts each between the previous load and the next line.

        Does not connect anything by itself.
        """
        if len(members) < _MINIMUM:
            msg = f"d.parallel groups at least {_MINIMUM} members, got {len(members)}"
            raise AuthorError(msg)
        return Parallel(members)
