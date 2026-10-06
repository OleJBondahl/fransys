"""Which function of another box a function is wired to point to point (model-0130).

Layout reads it to stand a box over the pin group it feeds (CONVENTIONS-V06 V1).
"""

import dataclasses
lazy from collections.abc import Collection

from fransys_model.derive.indexes import build_indexes
from fransys_model.vocab.closure import physical_nets
from fransys_model.vocab.tables import functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Port


@dataclasses.dataclass(frozen=True, slots=True)
class BoxPair:
    """One function and the one function of another item it is wired to, pin to pin.

    Attributes:
        function: The function the pairing is read for.
        partner: The function of another item that every port of `function` reaches.
        port_pairs: `(port of function, port of partner)`, in the order of `function`'s ports.
    """

    function: Id[Function]
    partner: Id[Function]
    port_pairs: tuple[tuple[Id[Port], Id[Port]], ...]


def _far_ports(
    nets: dict[Id[Port], tuple[Id[Port], ...]], own: tuple[Id[Port], ...]
) -> list[Id[Port]] | None:
    """The other end of each of `own`'s two-port nets, or `None` when one is not a two-port net."""
    ends = [nets.get(port, ()) for port in own]
    if not own or any(len(net) != 2 for net in ends):  # noqa: PLR2004 -- "two-port net" is the rule
        return None
    return [next(p for p in net if p != port) for port, net in zip(own, ends, strict=True)]


def _item_of(model: Model, function: Id[Function]) -> Id[Item]:
    """The item that owns `function`."""
    return functions(model)[function].item


def _ports_of(
    model: Model, function: Id[Function], drawn: Collection[Id[Port]] | None
) -> tuple[Id[Port], ...]:
    """`function`'s ports, or only those in `drawn` when it is given."""
    every = build_indexes(model).ports_by_function.get(function, ())
    return every if drawn is None else tuple(port for port in every if port in drawn)


def _pair_of(
    model: Model,
    nets: dict[Id[Port], tuple[Id[Port], ...]],
    function: Id[Function],
    drawn: Collection[Id[Port]] | None,
) -> BoxPair | None:
    """The pairing of `function`, or `None`: one partner, one to one, no port left over."""
    own = _ports_of(model, function, drawn)
    far = _far_ports(nets, own)
    if far is None:
        return None
    partners = {ports(model)[port].function for port in far}
    if len(partners) != 1 or len(set(far)) != len(far):
        return None
    (partner,) = partners
    same_size = len(_ports_of(model, partner, drawn)) == len(own)
    if not same_size or _item_of(model, partner) == _item_of(model, function):
        return None
    return BoxPair(function, partner, tuple(zip(own, far, strict=True)))


def box_pairs(
    model: Model, drawn: Collection[Id[Port]] | None = None
) -> dict[Id[Function], BoxPair]:
    """Each function wired point to point to one function of another item, and the port pairs.

    Every port of the function has a two-port net to a port of that one function, one to one, and
    that function has no other port. Two partners, a split group, a third member or a net of
    three ports leave the function out. The relation is symmetric; which box is fed is layout's
    reading of the box sides. With `drawn`, only the ports in it count on either
    side: a port the profile leaves off the page is no member of its function.
    """
    nets = {port: net.ports for net in physical_nets(model) for port in net.ports}
    pairs = {f: _pair_of(model, nets, f, drawn) for f in build_indexes(model).ports_by_function}
    return {function: pair for function, pair in pairs.items() if pair is not None}
