"""The ends of a harness's or a cable's line, numbered once (model-0175)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive.facts.roles import function_role
from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.vocab.cables import is_cable
from fransys_model.vocab.membership import is_harness
from fransys_model.vocab.tables import conductors, items, ports
lazy from fransys_model.vocab.core import Function, Item, Port

from .cable_end_rank import cable_end_owner
from .designation import connector_designation
from .harness import harness_cables, reading_cables
from .lookups import item_of_port, require
from .mate_rows import mate_partners
from .order import natural_key, port_designation_key
from .rows import HarnessLineEnd
from .wire_harness import harness_of_wire

if TYPE_CHECKING:
    from .rows import HarnessCable


@dataclass(frozen=True)
class _End:
    """One end item of a line: the connector a conductor lands on, if any, and its landed ports."""

    item: Id[Item]
    connector: Id[Function] | None
    ports: tuple[Id[Port], ...]


def mate_of(model: Model, plug: Id[Function]) -> Id[Function] | None:
    """The connector mated to `plug`: the first `mate_partners` entry, in designation order."""
    return next(iter(mate_partners(model).get(plug, ())), None)


def _cables_of(model: Model, subject: Id[Item]) -> tuple[HarnessCable, ...]:
    require(items(model).get(subject), "item", subject)
    if is_harness(model, subject):
        return harness_cables(model, subject)
    unit = items(model)[subject].unit
    reading = reading_cables(model, unit)
    found = tuple(cable for cable in reading if cable.cable == subject)
    if not found:
        message = f"{subject}: neither a harness nor a cable"
        raise SchemaError(message, kind="item", record_id=subject)
    return found


def _wire_ends(model: Model, subject: Id[Item]) -> list[_End]:
    """One end per port a single wire of harness `subject` lands on."""
    found = []
    for conductor in conductors(model).values():
        if harness_of_wire(model, conductor.id) == subject:
            for port in (conductor.a, conductor.b):
                function = ports(model)[port].function
                connector = function if function_role(model, function).pin_group else None
                found.append(
                    _End(cable_end_owner(model, item_of_port(model, port)), connector, (port,))
                )
    return found


def _merged(model: Model, subject: Id[Item], cables: tuple[HarnessCable, ...]) -> list[_End]:
    """Cable ends and wire ends merged by end item: one end per item, ports in first-seen order."""
    by_item: dict[Id[Item], _End] = {}
    cable_ends = (
        _End(end.item, end.connector, tuple(pin.port for pin in end.pins))
        for cable in cables
        for end in cable.ends
    )
    for end in (*cable_ends, *_wire_ends(model, subject)):
        old = by_item.get(end.item)
        if old is None:
            by_item[end.item] = end
            continue
        extra = tuple(port for port in end.ports if port not in old.ports)
        by_item[end.item] = _End(end.item, old.connector or end.connector, old.ports + extra)
    return list(by_item.values())


def plug_of(
    model: Model,
    item: Id[Item],
    connector: Id[Function] | None,
    parents: set[Id[Item]] | None = None,
) -> Id[Function] | None:
    """`connector` when `item` is a plug: a non-cable direct child of a line, a connector landed.

    The line is one of `parents`, or any cable or harness when `parents` is `None` (model-0175).
    """
    parent = items(model)[item].parent
    if connector is None or parent is None or is_cable(model, item):
        return None
    if parents is None:
        parents = {parent} if is_cable(model, parent) or is_harness(model, parent) else set()
    return connector if parent in parents else None


def _sort_key(model: Model, end: _End, plug: Id[Function] | None) -> tuple[object, ...]:
    if plug is not None:
        return (0, natural_key(connector_designation(model, plug)), end.item)
    return (1, port_designation_key(model, end.ports[0]), end.item)


def harness_line_ends(model: Model, subject: Id[Item]) -> tuple[HarnessLineEnd, ...]:
    """The ends of `subject`'s line: a harness's cables and wires, or one cable on no harness.

    The one home of branch numbering: the line-text function reads `-W13.n` from `branch` and never
    numbers on its own. A plug is an end whose item is a direct child of `subject` or of one of
    its cables and which a core or wire lands on a connector function of. Cable and wire ends
    merge by end item into one order. Plugs come first, by the natural
    order of the connector's designation, then fan-out ends by their first pin's designation;
    an end item's id breaks a tie. So `-W13.k` ends at `-W13-Pk` in the common case.

    Raises:
        SchemaError: `subject` is neither a harness nor a cable.
    """
    cables = _cables_of(model, subject)
    parents = {subject, *(cable.cable for cable in cables)}
    ends = _merged(model, subject, cables)
    plugs = {end.item: plug_of(model, end.item, end.connector, parents) for end in ends}
    ordered = sorted(ends, key=lambda end: _sort_key(model, end, plugs[end.item]))
    return tuple(
        HarnessLineEnd(
            harness=subject,
            branch=position,
            plug=(plug := plugs[end.item]),
            ports=() if plug else end.ports,
            mates=mate_of(model, plug) if plug else None,
        )
        for position, end in enumerate(ordered, start=1)
    )
