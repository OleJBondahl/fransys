"""The row each wire of a series takes (SERIES-GAPS S2 to S4): the one home of that rule.

A power path keeps each pole's conductor row; a control path takes a rail's row near a rail.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple, cast

from fransys_author.surface._ends import is_bridge
from fransys_author.surface._pairing import label_of, pair
from fransys_author.surface._rows import WiringRow, control_of, is_control
from fransys_author.surface._strip import TerminalStrip

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_author.handles import Port
    from fransys_author.surface._pairing import Ends
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port as ModelPort

type PortId = Id[ModelPort]
type Wire = tuple[PortId, PortId]
type Walked = tuple[dict[Wire, WiringRow], bool]  # each wire's row, and whether a power path
type _State = tuple[WiringRow | None, WiringRow | None]  # the row, and the rail's row when near


class Given(NamedTuple):
    """The row an earlier series gave a port, and whether that series was a power path."""

    row: WiringRow
    power: bool


class Hop(NamedTuple):
    """The ports joined between element `a` and element `b`; a cable between makes no wire."""

    a: int
    b: int
    pairs: list[tuple[Port, Port]]
    made: bool


@dataclass
class _Walk:
    """The states a series walk finds, keyed by port id: forward, near a rail, backward."""

    power: bool
    family: WiringRow | None
    ahead: dict[PortId, WiringRow] = field(default_factory=dict)
    near: dict[PortId, WiringRow] = field(default_factory=dict)
    behind: dict[PortId, WiringRow] = field(default_factory=dict)


def _rails(element: object) -> tuple[WiringRow, ...]:
    """The conductor rows of a supply or rail element, in its ends' order; none for the rest."""
    rows = getattr(element, "_conductor_rows", None)
    return () if rows is None else cast("tuple[WiringRow, ...]", rows())


def _passes(element: object) -> bool:
    """A strip, run or cable carries a rail's potential on: no other element does (S2)."""
    return isinstance(element, TerminalStrip) or is_bridge(element)


def hops(elements: Sequence[object], found: list[list[Ends]]) -> list[Hop]:
    """Every join of neighbouring elements; a cable joins the elements on its two sides."""
    joins: list[Hop] = []
    for i in range(len(elements) - 1):
        if is_bridge(elements[i]):
            continue
        if is_bridge(elements[i + 1]):
            pairs = pair(
                found[i][0].load,
                found[i + 2][0].line,
                (label_of(elements[i]), label_of(elements[i + 2])),
            )
            joins.append(Hop(i, i + 2, pairs, made=False))
            continue
        names = (label_of(elements[i]), label_of(elements[i + 1]))
        pairs = [
            (x, y) for a in found[i] for b in found[i + 1] for x, y in pair(a.load, b.line, names)
        ]
        joins.append(Hop(i, i + 1, pairs, made=True))
    return joins


def _start(ends: list[Ends], record: dict[PortId, Given]) -> Given | None:
    """What an earlier series gave the first element: at its load ports, else its line ports."""
    for side in ("load", "line"):
        for end in ends:
            for one in getattr(end, side):
                if one.port.id in record:
                    return record[one.port.id]
    return None


def _walk(
    elements: Sequence[object], found: list[list[Ends]], record: dict[PortId, Given]
) -> _Walk:
    """The path kind (S2, S3) and the control row of its wires with no rail's potential."""
    first = elements[0]
    if getattr(first, "_whole_supply", False):
        return _Walk(power=True, family=None)
    if rows := _rails(first):
        return _Walk(power=False, family=control_of(rows[0]))
    given = _start(found[0], record)
    if given is not None:
        return _Walk(power=given.power, family=control_of(given.row))
    rails = [row for element in elements for row in _rails(element)]
    return _Walk(power=False, family=control_of(rails[0]) if rails else None)


def _state(given: Given) -> _State:
    """A recorded row as a walk state: a rail's row is near its rail, a control row is not."""
    return given.row, None if is_control(given.row) else given.row


def _seed(walk: _Walk, element: object, ends: list[Ends], record: dict[PortId, Given]) -> None:
    """The first element's load states from the rows an earlier series gave its ports (S4).

    A recorded load port keeps its row; a recorded line port is carried through the element.
    """
    came = {
        one.port.id: _state(record[one.port.id])
        for end in ends
        for one in end.line
        if one.port.id in record
    }
    _carry(walk, element, ends, came)
    for end in ends:
        for load in end.load:
            given = record.get(load.port.id)
            if given is not None:
                walk.ahead[load.port.id] = given.row
                if not is_control(given.row):
                    walk.near[load.port.id] = given.row


def _carry(walk: _Walk, element: object, ends: list[Ends], came: dict[PortId, _State]) -> None:
    """The load states of `element` from the states that came to its line ports."""
    rows, passes = _rails(element), _passes(element)
    for end in ends:
        for k, (line, load) in enumerate(zip(end.line, end.load, strict=True)):
            if rows:
                walk.ahead[load.port.id] = walk.near[load.port.id] = rows[k]
                continue
            row, near = came.get(line.port.id, (None, None))
            if passes and near is not None:
                walk.near[load.port.id] = near
            if row is not None:
                walk.ahead[load.port.id] = row if walk.power or passes else control_of(row)


def _forward(
    walk: _Walk,
    elements: Sequence[object],
    found: list[list[Ends]],
    joins: list[Hop],
    record: dict[PortId, Given],
) -> None:
    """Walk from the first element to the last, carrying each pole's state on (S3)."""
    came: dict[PortId, _State] = {}
    by_start = {hop.a: hop for hop in joins}
    for i, element in enumerate(elements):
        if is_bridge(element):
            continue
        if i == 0 and not _rails(element):
            _seed(walk, element, found[0], record)
        else:
            _carry(walk, element, found[i], came)
        for a, b in by_start[i].pairs if i in by_start else ():
            came[b.id] = (walk.ahead.get(a.id), walk.near.get(a.id))


def _backward(
    walk: _Walk, elements: Sequence[object], found: list[list[Ends]], joins: list[Hop]
) -> None:
    """Walk from the last element back: a line port near a rail ahead of it (S2)."""
    out: dict[PortId, WiringRow] = {}
    by_end = {hop.b: hop for hop in joins}
    for i in range(len(elements) - 1, -1, -1):
        element = elements[i]
        rows, passes = _rails(element), _passes(element)
        for end in found[i]:
            for k, (line, load) in enumerate(zip(end.line, end.load, strict=True)):
                row = rows[k] if rows else (out.get(load.port.id) if passes else None)
                if row is not None:
                    walk.behind[line.port.id] = row
        for a, b in by_end[i].pairs if i in by_end else ():
            if b.id in walk.behind:
                out[a.id] = walk.behind[b.id]


def _row(walk: _Walk, a: Port, b: Port) -> WiringRow | None:
    if walk.power:
        return walk.ahead.get(a.id)
    return walk.near.get(a.id) or walk.behind.get(b.id) or walk.ahead.get(a.id) or walk.family


def wire_rows(
    elements: Sequence[object],
    found: list[list[Ends]],
    joins: list[Hop],
    record: dict[PortId, Given],
) -> Walked | None:
    """The row of every wire the series makes, and whether it is a power path.

    `None` when the series touches no rail and starts on no net an earlier series made (S4).
    """
    walk = _walk(elements, found, record)
    if not walk.power and walk.family is None:
        return None
    _forward(walk, elements, found, joins, record)
    _backward(walk, elements, found, joins)
    rows: dict[Wire, WiringRow] = {}
    for hop in joins:
        for a, b in hop.pairs if hop.made else ():
            row = _row(walk, a, b)
            if row is None:
                return None  # a power-path pole no supply pole reaches
            rows[a.id, b.id] = row
    return rows, walk.power
