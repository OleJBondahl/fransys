"""The generic-box picks of the symbol kit: a boxed function alone, or an item box (el-0006).

The split of an item's boxed functions into one box is `derive.item_box_views`; nothing here
re-derives it. A boxed function is one no authored choice or symbol rule names.
"""

from typing import TYPE_CHECKING

from electrical_symbols import GENERIC_BOX_KEY
from fransys_model.derive import (
    BoxCandidate,
    box_port_text,
    function_ports,
    item_box_views,
    port_name,
)
from fransys_model.kernel import render_id

from .placement_kit import Pick

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from collections.abc import Set as AbstractSet

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

__all__ = ["box_picks", "named_picks"]


def _candidate(model: Model, function: Function, channels: AbstractSet[Id[Function]]) -> BoxCandidate:
    """`band` decides only a view's kind, which a pick does not read."""
    return BoxCandidate(
        function=function.id,
        item=function.item,
        key=(function.name, render_id(function.id)),
        band="",
        plc_channel=function.id in channels,
        pin=False,
        boxed=True,
        ports=function_ports(model, function.id),
        symbol="",
        symbol_ports=(),
    )


def box_picks(
    model: Model,
    boxed: Iterable[Function],
    channels: AbstractSet[Id[Function]],
    wired: AbstractSet[Id[Port]],
) -> dict[Id[Function], Pick]:
    """One generic-box pick per item box (on its lead) and per lone boxed function.

    An item box's ports are named `<function>.<port>`; a lone function's, by its port names. A
    PLC channel is in `channels`; `wired` (`derive.connected_ports`) decides a lone channel.
    """
    candidates = [_candidate(model, f, channels) for f in boxed]
    name_of = {f.function: f.key[0] for f in candidates}
    found: dict[Id[Function], Pick] = {}
    views = item_box_views(model, candidates, wired)
    for view in (v for v in views if not v.lone):
        names = {p: box_port_text(name_of[f], port_name(model, p)) for f in view.members for p in function_ports(model, f)}
        rest = tuple(f for f in view.members if f != view.lead)
        found[view.lead] = Pick(GENERIC_BOX_KEY, 1, frozendict(names), rest)
    grouped = {f for view in views if not view.lone for f in view.members}
    for candidate in candidates:
        if candidate.function not in grouped:
            names = {p: port_name(model, p) for p in candidate.ports}
            found[candidate.function] = Pick(GENERIC_BOX_KEY, 1, frozendict(names))
    return found


def named_picks(
    model: Model, table: Mapping[Id[Function], Function], kit: dict[Id[Function], Pick], wired: AbstractSet[Id[Port]]
) -> dict[Id[Function], Pick]:
    """`kit` with each item whose functions all name one symbol on distinct ports drawn as one view on its lead (stages D5, the PSU)."""
    candidates = [
        BoxCandidate(
            function=f,
            item=table[f].item,
            key=(table[f].name, render_id(f)),
            band="",
            plc_channel=False,
            pin=False,
            boxed=False,
            ports=function_ports(model, f),
            symbol=pick.key,
            symbol_ports=tuple(pick.ports[p] for p in function_ports(model, f)),
        )
        for f, pick in kit.items()
        if pick.poles == 1 and not pick.members
    ]
    merged = dict(kit)
    for view in (v for v in item_box_views(model, candidates, wired) if v.named):
        picks = [kit[f] for f in view.members]
        for f in view.members:
            del merged[f]
        merged[view.lead] = Pick(
            picks[0].key, 1, frozendict({p: s for pick in picks for p, s in pick.ports.items()}), tuple(f for f in view.members if f != view.lead)
        )
    return merged
