"""The ends of a harness's or a cable's line, numbered once (model-0175)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.membership import is_harness
from fransys_model.vocab.tables import conductors, functions, items, ports
from fransys_model.vocab.tables import mates as mates_table
lazy from fransys_model.vocab.core import Function, Item, Port

from .designation import connector_designation, port_designation
from .harness import harness_cables, top_level_cables
from .lookups import cable_end_owner, item_of_port, require
from .natural_order import natural_key
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


def _other_side(model: Model, plug: Id[Function]) -> Id[Function] | None:
    for record in mates_table(model).values():
        if plug in (record.a, record.b):
            return record.b if record.a == plug else record.a
    return None


def _cables_of(model: Model, subject: Id[Item]) -> tuple[HarnessCable, ...]:
    require(items(model).get(subject), "item", subject)
    if is_harness(model, subject):
        return harness_cables(model, subject)
    found = tuple(cable for cable in top_level_cables(model) if cable.cable == subject)
    if not found:
        message = f"{subject}: neither a harness nor a cable"
        raise SchemaError(message, kind="item", record_id=subject)
    return found


def _wire_ends(model: Model, subject: Id[Item]) -> list[_End]:
    """One end per port a single wire of harness `subject` lands on (HL1, model-0175 amended)."""
    found = []
    for conductor in conductors(model).values():
        if harness_of_wire(model, conductor.id) == subject:
            for port in (conductor.a, conductor.b):
                function = ports(model)[port].function
                kind = functions(model)[function].kind
                connector = function if kind is FunctionKind.CONNECTOR else None
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


def _plug(model: Model, end: _End, parents: set[Id[Item]]) -> Id[Function] | None:
    """The end's connector function when its item is a direct child of a harness or cable."""
    return end.connector if items(model)[end.item].parent in parents else None


def _sort_key(model: Model, end: _End, plug: Id[Function] | None) -> tuple[object, ...]:
    if plug is not None:
        return (0, natural_key(connector_designation(model, plug)), end.item)
    return (1, natural_key(port_designation(model, end.ports[0])), end.item)


def harness_line_ends(model: Model, subject: Id[Item]) -> tuple[HarnessLineEnd, ...]:
    """The ends of `subject`'s line: a harness's cables and wires, or one cable on no harness.

    The one home of branch numbering: HL3's text function reads `-W13.n` from `branch` and never
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
    plugs = {end.item: _plug(model, end, parents) for end in ends}
    ordered = sorted(ends, key=lambda end: _sort_key(model, end, plugs[end.item]))
    return tuple(
        HarnessLineEnd(
            harness=subject,
            branch=position,
            plug=(plug := plugs[end.item]),
            ports=() if plug else end.ports,
            mates=_other_side(model, plug) if plug else None,
        )
        for position, end in enumerate(ordered, start=1)
    )
