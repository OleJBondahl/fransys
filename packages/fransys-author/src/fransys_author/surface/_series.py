"""Surface mixin for `series` and `parallel`; supplies and cables are its two bases."""

from functools import cached_property
from typing import TYPE_CHECKING
lazy from collections.abc import Callable, Mapping
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.surface._cable import Cables
from fransys_author.surface._ends import Parallel, branches, is_bridge, width_of
from fransys_author.surface._pairing import Ends, PartFacts
from fransys_author.surface._potential import Given, hops, wire_rows
from fransys_author.surface._rows import AC_N, table
from fransys_author.surface._supplies import Supplies, _Rails
from fransys_author.surface._wire import Colour, _gauge, wiring_for

if TYPE_CHECKING:
    from fransys_author.handles import Port
    from fransys_author.surface._potential import Hop, PortId, Walked, Wire
    from fransys_author.surface._rows import RowValue, WiringRow
    from fransys_author.wiring import Wiring

    from .design import Design

type WireArg = tuple[Colour, float] | float | str | Decimal | Mapping[WiringRow, RowValue] | None
type _Maker = Callable[[Port, Port], Wiring]

_MINIMUM = 2
_NO_SUPPLY = "this series reaches no supply: give wire=(colour, size)"
_NO_SIZE = "give a size: wire=0.75, or a row with a size"


def _supply_width(design: Design, supply: _Rails, after: tuple[object, ...]) -> int:
    """The phases, or the phases and N, as the first fixed pole count after the supply says (S3)."""
    total = len(supply._rails)
    phases = [rail.name for rail in supply._rails if rail.row is not AC_N]
    if len(phases) == total:
        return total
    for element in after:
        count = None if isinstance(element, _Rails) else width_of(design, element)
        if count is None:
            continue
        if count in (len(phases), total):
            return count
        label = getattr(element, "_label", type(element).__name__)
        msg = (
            f"{label} has {count} poles; a path from {supply._name} takes "
            f"{len(phases)} ({', '.join(phases)}) or {total} (with N)"
        )
        raise AuthorError(msg)
    return total


def _width(design: Design, elements: tuple[object, ...]) -> int:
    for i, element in enumerate(elements):
        width = width_of(design, element)
        if width is None:
            continue
        if isinstance(element, _Rails):
            return _supply_width(design, element, elements[i + 1 :])
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


def _wire_hops(maker: _Maker, joins: list[Hop], skip: set[PortId]) -> set[PortId]:
    """Wire each join a cable does not land; a common a series wired is skipped (S7).

    Returns the port ids the wires touched.
    """
    touched: set[PortId] = set()
    for hop in joins:
        for port_a, port_b in hop.pairs if hop.made else ():
            if not {port_a.id, port_b.id} & skip:
                maker(port_a, port_b)(port_a, port_b)
                touched |= {port_a.id, port_b.id}
    return touched


def _commons(elements: tuple[object, ...]) -> set[PortId]:
    """The common ports of every changeover throw in the series."""
    return {port.id for element in elements for port in getattr(element, "_commons", ())}


def _row_makers(design: Design, wire: WireArg, rows: dict[Wire, WiringRow]) -> _Maker:
    """The maker of each wire from its row: the series' table or size over the scope's rows."""
    scope = table(wire, design._wiring) if isinstance(wire, Mapping) else design._wiring
    size = None if wire is None or isinstance(wire, Mapping) else _gauge(wire)
    if size is not None and size <= 0:
        msg = f"wire= size is a positive cross-section in mm2, got {wire!r}"
        raise AuthorError(msg)
    makers: dict[WiringRow, Wiring] = {}
    for row in set(rows.values()):
        colour, gauge = scope[row]
        gauge = gauge if size is None else size
        if gauge is None:
            raise AuthorError(_NO_SIZE)
        makers[row] = design._engine.wiring(colour=colour, gauge=gauge)
    return lambda a, b: makers[rows[a.id, b.id]]


def _maker(design: Design, wire: WireArg, walked: Walked | None) -> _Maker:
    """One `(colour, size)` for every wire, else each wire's row; no row reached raises (S4)."""
    if isinstance(wire, tuple):
        spec = wiring_for(design, wire)
        return lambda _a, _b: spec
    if walked is None:
        raise AuthorError(_NO_SUPPLY)
    return _row_makers(design, wire, walked[0])


def _land_bridges(design: Design, elements: tuple[object, ...], found: list[list[Ends]]) -> None:
    """Hand each bridge its two neighbours and their ends."""
    for i, element in enumerate(elements):
        if is_bridge(element):
            before, after = (elements[i - 1], found[i - 1][0]), (elements[i + 1], found[i + 1][0])
            element._series_between(design, before, after)


class Series(Supplies, Cables):
    """The calls of this mixin: `series` and `parallel`."""

    @cached_property
    def _pairing_facts(self: "Design") -> PartFacts:
        """The part facts of this design, indexed once (poles, sides, conductor marks)."""
        return PartFacts(self.library, self._engine._design._draft)

    def series(self: "Design", *elements: object, wire: WireArg = None) -> None:
        """Wire the elements end to end: each one's load to the next one's line, one wire per pole.

        `wire=` is a size (colours from the rows), a table of rows, or one `(colour, size)`.
        Does not create devices, cross a unit's boundary (use mate) or decide the drawing.
        """
        if len(elements) < _MINIMUM:
            msg = f"d.series joins at least {_MINIMUM} elements, got {len(elements)}"
            raise AuthorError(msg)
        found = _resolve(self, elements, _width(self, elements))
        commons, joins = _commons(elements), hops(elements, found)
        walked = wire_rows(elements, found, joins, self._given)
        maker = _maker(self, wire, walked)
        touched = _wire_hops(maker, joins, commons & self._wired_commons)
        _land_bridges(self, elements, found)
        self._wired_commons |= commons & touched
        self._remember(walked)

    def _remember(self: "Design", walked: Walked | None) -> None:
        """Keep the row each wire took, for a later series that starts on its net (S4)."""
        rows, power = walked or ({}, False)
        for (a, b), row in rows.items():
            self._given[a] = self._given[b] = Given(row, power)

    def parallel(self: "Design", *members: object) -> Parallel:
        """Group `members` so a series puts each between the previous load and the next line.

        Does not connect anything by itself.
        """
        if len(members) < _MINIMUM:
            msg = f"d.parallel groups at least {_MINIMUM} members, got {len(members)}"
            raise AuthorError(msg)
        return Parallel(members)
