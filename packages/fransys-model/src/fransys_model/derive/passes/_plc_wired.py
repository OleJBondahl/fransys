"""`allocate_plc`: a wired request takes its wired channel (model-0083, model-0211).

The wiring walk is `vocab.plc_wiring`, the one `check_plc_wiring` reads. This module only decides,
from what it reports, which request binds to which channel by wiring and whether an
unservable request is really open at the boundary of a standalone unit.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.membership import boundary, standalone
from fransys_model.vocab.plc_wiring import (
    direct_neighbours,
    owner_of_port,
    ports_by_function,
    wired_functions,
)
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port, Unit
    from fransys_model.vocab.enums import SignalType
    from fransys_model.vocab.facets.plc import PlcRequestFacet


def unit_of(model: Model, function: Function) -> Id[Unit] | None:
    """The unit that owns `function`: its item's `Item.unit` (`None` is the top level)."""
    return items(model)[function.item].unit


@dataclasses.dataclass(frozen=True, slots=True)
class WiredPick:
    """What wiring decided: requests bound to a channel, and requests left ambiguous.

    `ambiguous` maps a request function to the channels, in serving order, that tie for it.
    """

    bound: dict[Id[Function], Id[Function]]
    ambiguous: dict[Id[Function], tuple[Id[Function], ...]]


def narrow(
    request: PlcRequestFacet,
    eligible: Collection[Id[Function]],
    signal_of: Mapping[Id[Function], SignalType],
    adjacent: Collection[Id[Function]],
) -> list[Id[Function]]:
    """The channels left of `eligible` after W2 (the asked kind) and W3 (a direct conductor).

    W2 keeps the channels of the request's signal; with none, all stay (the binding then raises
    `PLC_BINDING_SIGNAL_MISMATCH`). W3 keeps the channels one conductor from the request, if any.
    """
    kept = [c for c in eligible if signal_of.get(c) is request.signal] or list(eligible)
    return [c for c in kept if c in adjacent] or kept


@dataclasses.dataclass(frozen=True, slots=True)
class _Wiring:
    """The lookups one run reads: the net walk, the serving order and the direct conductors."""

    model: Model
    by_function: Mapping[Id[Function], list[Id[Port]]]
    channel_owner: Mapping[Id[Port], Id[Function]]
    request_owner: Mapping[Id[Port], Id[Function]]
    ranked: Mapping[Id[Function], tuple[int, SignalType]]
    neighbours: Mapping[Id[Function], frozenset[Id[Function]]]

    def eligible(
        self, subject: Id[Function], claimed: Collection[Id[Function]]
    ) -> list[Id[Function]]:
        """W1: the free channels on `subject`'s net whose own net holds no other request."""
        own = self.by_function.get(subject, ())
        reached = wired_functions(self.model, own, self.channel_owner) - {subject}
        return [
            channel
            for channel in reached
            if channel not in claimed
            and wired_functions(self.model, self.by_function.get(channel, ()), self.request_owner)
            - {channel}
            == {subject}
        ]

    def left(
        self, request: PlcRequestFacet, claimed: Collection[Id[Function]]
    ) -> list[Id[Function]]:
        """The channels left for `request` after W1 to W3, in serving order."""
        signal_of = {channel: signal for channel, (_, signal) in self.ranked.items()}
        adjacent = self.neighbours.get(request.subject, ())
        found = narrow(request, self.eligible(request.subject, claimed), signal_of, adjacent)
        return sorted(found, key=lambda channel: self.ranked[channel][0])


def wired_requests(
    model: Model,
    requests: Sequence[PlcRequestFacet],
    *,
    skip: Collection[Id[Function]],
    taken: Collection[Id[Function]],
    ranked: Mapping[Id[Function], tuple[int, SignalType]],
) -> WiredPick:
    """Which requests bind by wiring (model-0211): W1 candidates, `narrow` (W2, W3), then W4.

    `ranked` maps every channel function to its serving place and signal. One left binds; more
    than one is ambiguous and binds nothing. A channel two requests share binds nobody by wiring.
    """
    by_function = ports_by_function(model)
    owners = {request.subject for request in requests}
    wiring = _Wiring(
        model,
        by_function,
        owner_of_port(by_function, ranked),
        owner_of_port(by_function, owners),
        ranked,
        direct_neighbours(model),
    )
    claimed = set(taken)
    pick = WiredPick({}, {})
    for request in requests:
        if request.subject in skip:
            continue
        left = wiring.left(request, claimed)
        if len(left) > 1:
            pick.ambiguous[request.subject] = tuple(left)
        elif left:
            pick.bound[request.subject] = left[0]
            claimed.add(left[0])
    return pick


def reaches_open_boundary(model: Model, function: Function) -> bool:
    """Whether `function`'s net reaches a boundary port of a standalone unit on its chain.

    A standalone unit has an open outside, so a request wired out through it is served: no error.
    A boundary function wired to nothing else does not reach one; the top level has no boundary.
    """
    home = unit_of(model, function)
    if home is None:
        return False
    by_function = ports_by_function(model)
    own_ports = by_function.get(function.id, ())
    return any(
        wired_functions(model, own_ports, owner_of_port(by_function, boundary(model, unit)))
        - {function.id}
        for unit in unit_chain(model, home)
        if standalone(model, unit)
    )
