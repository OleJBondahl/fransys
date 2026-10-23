"""The items drawn as one generic box: which functions form it, its kind and its port names."""

lazy from collections.abc import Sequence
lazy from collections.abc import Set as AbstractSet

from fransys_model.derive.order_box_ports import box_port_ranks
from fransys_model.derive.rows_item_boxes import BoxCandidate, BoxPort, ItemBoxView
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import ports as ports_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port

__all__ = ["box_port_text", "item_box_views"]

_PAIR = 2  # the least a box holds: a pair of functions


def box_port_text(function: str, port: str) -> str:
    """An item view's box port name, `<function>.<port>`: the one place that text is built."""
    return f"{function}.{port}"


def item_box_views(
    model: Model, candidates: Sequence[BoxCandidate], wired: AbstractSet[Id[Port]]
) -> tuple[ItemBoxView, ...]:
    """One row per item of `candidates` drawn as an item box, in candidate order.

    An item's boxed functions form its box when two or more; the rest stand `apart`. A box is
    drawn when every member is boxed or all name one symbol with distinct symbol ports. A lone
    unwired PLC channel is its own generic box (`lone`). `wired` is the engine's wired port set.
    """
    by_item: dict[Id[Item], list[BoxCandidate]] = {}
    for candidate in candidates:
        by_item.setdefault(candidate.item, []).append(candidate)
    rows = (_view(model, item, group, wired) for item, group in by_item.items())
    return tuple(row for row in rows if row is not None)


def _split(whole: list[BoxCandidate]) -> tuple[list[BoxCandidate], list[BoxCandidate]]:
    """The boxed functions (two or more) and the rest; fewer than two boxed leave all together."""
    boxed = [c for c in whole if c.boxed]
    if len(boxed) < _PAIR:
        return list(whole), []
    return boxed, [c for c in whole if not c.boxed]


def _named(group: list[BoxCandidate]) -> bool:
    """Whether every member names one symbol, none is a pin view and the symbol ports differ."""
    if len({c.symbol for c in group}) != 1 or not all(c.symbol for c in group):
        return False
    if any(c.pin for c in group):
        return False
    mapped = [name for c in group for name in c.symbol_ports]
    return len(mapped) == len(set(mapped))


def _kind(group: list[BoxCandidate], wired: AbstractSet[Id[Port]]) -> str:
    """The kind the wired members share unless it is a PLC channel, else "item"."""
    on_wire = [c for c in group if any(p in wired for p in c.ports)]
    shared = len({c.band for c in on_wire}) == 1 and not on_wire[0].plc_channel
    return on_wire[0].band if shared else "item"


def _box_ports(model: Model, group: list[BoxCandidate]) -> tuple[BoxPort, ...]:
    """The ports of the members with their printed box names and ranks."""
    rank = box_port_ranks(model, tuple(group))
    names, table = functions_table(model), ports_table(model)
    return tuple(
        BoxPort(
            function=c.function,
            port=p,
            name=box_port_text(names[c.function].name, table[p].name),
            rank=rank[p],
        )
        for c in group
        for p in c.ports
    )


def _view(
    model: Model, item: Id[Item], whole: list[BoxCandidate], wired: AbstractSet[Id[Port]]
) -> ItemBoxView | None:
    """The item's row, or `None` when its functions stay as they are."""
    group, apart = _split(whole)
    first = group[0]
    if len(group) == 1 and first.plc_channel and first.ports[0] not in wired:
        return ItemBoxView(
            item=item,
            members=(first.function,),
            apart=(),
            lead=first.function,
            kind="item",
            named=False,
            lone=True,
            ports=(),
        )
    defaulted, named = all(c.boxed for c in group), _named(group)
    pair = len(group) == 1 and first.plc_channel and len(first.ports) > 1
    if (len(group) < _PAIR and not pair) or not (defaulted or named):
        return None
    lowest = min(c.key for c in group)
    lead = next(c for c in group if c.key == lowest)
    return ItemBoxView(
        item=item,
        members=tuple(c.function for c in group),
        apart=tuple(c.function for c in apart),
        lead=lead.function,
        kind=_kind(group, wired),
        named=named and not defaulted,
        lone=False,
        ports=_box_ports(model, group),
    )
