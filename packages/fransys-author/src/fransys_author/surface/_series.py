"""Surface mixin for `series` and `parallel`; supplies and cables are its two bases."""

from functools import cached_property
from typing import TYPE_CHECKING
lazy from collections.abc import Callable

from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_author.surface._bare import bare_series
from fransys_author.surface._block_ports import series_ports
from fransys_author.surface._cable import Cables
from fransys_author.surface._carry import series_name
from fransys_author.surface._channels import take_channels
from fransys_author.surface._detail_rows import hint_maker, row_wiring
from fransys_author.surface._ends import Parallel, branches, is_bridge, width_of
from fransys_author.surface._pairing import Ends, PartFacts
from fransys_author.surface._partless_end import only_last
from fransys_author.surface._poles import Poles, group
from fransys_author.surface._potential import Given, hops, wire_rows
from fransys_author.surface._rows import AC_N
from fransys_author.surface._shorts import refuse_lone_tied_poles, refuse_tied_poles
from fransys_author.surface._supplies import Supplies, _Rails
from fransys_author.surface._wire import PoleWire, RowWire, WireArg, read_wire

if TYPE_CHECKING:
    from fransys_author.handles import Port
    from fransys_author.surface._potential import Hop, PortId, Walked, Wire
    from fransys_author.surface._rows import WiringRow
    from fransys_author.wiring import Wiring

    from .design import Design

type _Maker = Callable[[Port, Port, int], Callable[..., None]]  # the pole is the pair's index

_MINIMUM = 2


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
            f"{label} has {count} pole{'' if count == 1 else 's'}, the path from {supply._name} "
            f"carries {len(phases)} ({', '.join(phases)}) or {total} (with N): run each pole "
            f"between the rails with its own "
            f"d.series({supply._name}.<rail>, {label}, ..., <rail>), "
            f"or use a {len(phases)}-pole function"
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


def _entered(found: list[Ends], element: object, around: tuple[object, ...]) -> list[Ends]:
    """A strip is entered from its field side after a cable: its outer ends are the line ends.

    A strip that starts a series and goes on to a plain element leaves inward (its inner ends are
    the load ends); one that goes on to a cable keeps the outer side for the field cable.
    """
    if not getattr(element, "_enters_from_field", False):
        return found
    before, after = around
    if is_bridge(before) or (before is None and not is_bridge(after)):
        return [Ends(e.load, e.line, e.pe) for e in found]
    return found


def _refuse_shorts(element: object, width: int, before: Ends | None) -> None:
    """A bridged run takes every pole of the series, alone or in a parallel, and shorts them."""
    if isinstance(element, Parallel):
        refuse_tied_poles(element, width, before)
    else:
        refuse_lone_tied_poles(element, width, before)


def _resolve(design: Design, elements: tuple[object, ...], width: int) -> list[list[Ends]]:
    """The ends of every element; a bridge has none and needs a plain element on each side."""
    only_last(design._pairing_facts, elements)
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
            _refuse_shorts(element, width, found[i - 1][0] if i and found[i - 1] else None)
            around = (elements[i - 1] if i else None, elements[i + 1] if i < last else None)
            found.append(_entered(branches(design, element, width), element, around))
    return found


def _wire_hops(maker: _Maker, joins: list[Hop], skip: set[PortId]) -> set[PortId]:
    """Wire each join a cable does not land; a common a series wired is skipped (S7).

    Returns the port ids the wires touched.
    """
    touched: set[PortId] = set()
    for hop in joins:
        for pole, (port_a, port_b) in enumerate(hop.pairs if hop.made else ()):
            if not {port_a.id, port_b.id} & skip:
                maker(port_a, port_b, pole)(port_a, port_b)
                touched |= {port_a.id, port_b.id}
    return touched


def _commons(elements: tuple[object, ...]) -> set[PortId]:
    """The common ports of every changeover throw in the series."""
    return {port.id for element in elements for port in getattr(element, "_commons", ())}


def _row_makers(design: Design, wire: RowWire, rows: dict[Wire, WiringRow]) -> _Maker:
    """The maker of each wire from its row; a wire with no row is hinted (model-0260)."""
    makers = {row: row_wiring(design, row, wire) for row in set(rows.values())}
    hinted = hint_maker(design, wire)
    return lambda a, b, _p: makers[rows[a.id, b.id]] if (a.id, b.id) in rows else hinted


def _read(design: Design, wire: WireArg, width: int) -> Wiring | RowWire | PoleWire:
    """`wire=` read once; a per-pole tuple must give one spec for each of the `width` poles."""
    read = read_wire(design, wire)
    if isinstance(read, PoleWire) and len(read.wirings) != width:
        msg = (
            f"wire= has {len(read.wirings)} specs but the series has {width} poles: "
            f"give one (colour, size) per pole, or one (colour, size) for all"
        )
        raise AuthorError(msg)
    return read


def _maker(design: Design, wire: Wiring | RowWire | PoleWire, walked: Walked | None) -> _Maker:
    """One `(colour, size)` for all wires, one per pole, else each made wire's row, else a hint."""
    if isinstance(wire, PoleWire):
        return lambda _a, _b, pole: wire.wirings[pole % len(wire.wirings)]  # parallel: next branch
    if not isinstance(wire, RowWire):
        return lambda _a, _b, _p: wire
    return _row_makers(design, wire, walked[0] if walked is not None else {})


def _land_bridges(design: Design, elements: tuple[object, ...], found: list[list[Ends]]) -> None:
    """Hand each bridge its two neighbours and their ends, and the series' name."""
    series = series_name(elements)
    for i, element in enumerate(elements):
        if is_bridge(element):
            before, after = (elements[i - 1], found[i - 1][0]), (elements[i + 1], found[i + 1][0])
            element._series_between(design, before, after, series)


class Series(Supplies, Cables):
    """The calls of this mixin: `series` and `parallel`."""

    @cached_property
    def _pairing_facts(self: "Design") -> PartFacts:
        """The part facts of this design, indexed once (poles, sides, conductor marks)."""
        return PartFacts(self.library, self._engine._design._draft)

    def series(self: "Design", *elements: object, wire: WireArg = None) -> None:
        """Wire the elements end to end: each one's load to the next one's line, one wire per pole.

        `wire=` is a size, a table of rows, one `(colour, size)`, or one per pole in a tuple.
        Does not create devices, cross a unit's boundary (use mate) or decide the drawing.
        """
        if len(elements) < _MINIMUM:
            msg = f"d.series joins at least {_MINIMUM} elements, got {len(elements)}"
            raise AuthorError(msg)
        elements = bare_series(self, take_channels(self, elements))
        width = _width(self, elements)
        found = _resolve(self, elements, width)
        commons, joins = _commons(elements), hops(elements, found)
        walked = wire_rows(elements, found, joins, self._given)
        maker = _maker(self, _read(self, wire, width), walked)
        touched = _wire_hops(maker, joins, commons & self._wired_commons)
        _land_bridges(self, elements, found)
        self._wired_commons |= commons & touched
        self._remember(walked)
        self._note_block(elements, found)

    def _note_block(self: "Design", elements: tuple[object, ...], found: list[list[Ends]]) -> None:
        """Tell the engine which block this series was written in (author-0050)."""
        if self._group is not None:
            ports = tuple(port.id for port in series_ports(elements, found))
            self._engine._design._series_blocks.collect(self._group.id, ports, caller_origin())

    def _remember(self: "Design", walked: Walked | None) -> None:
        """Keep the row each wire took, for a later series that starts on its net (S4)."""
        rows, power = walked or ({}, False)
        for (a, b), row in rows.items():
            self._given[a] = self._given[b] = Given(row, power)

    def poles(self: "Design", *functions: object, selector: bool = False) -> Poles:
        """Group one-pole contacts of one device, in pole order, as one element drawn multi-pole.

        A changeover group gives `q.no` and `q.nc`; `selector=True` turns its throws to the line.
        Does not wire anything: a series wires the group.
        """
        return group(self, functions, selector=selector)

    def parallel(self: "Design", *members: object) -> Parallel:
        """Group `members` so a series puts each between the previous load and the next line.

        Does not connect anything by itself.
        """
        if len(members) < _MINIMUM:
            msg = f"d.parallel groups at least {_MINIMUM} members, got {len(members)}"
            raise AuthorError(msg)
        return Parallel(members)
