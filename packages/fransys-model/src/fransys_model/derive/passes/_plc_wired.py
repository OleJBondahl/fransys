"""`allocate_plc`: a wired request takes its wired channel (model-0083, model-0211).

The wiring walk is `derive.facts.plc_wiring`, the one `check_plc_wiring` reads. This module
only decides, from what it reports, which request binds to which channel by wiring and whether an
unservable request is really open at the boundary of a standalone unit.
"""

import dataclasses
from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.derive.facts.plc_wiring import (
    channel_takes,
    direct_neighbours,
    owner_of_port,
    wired_functions,
)
from fransys_model.derive.facts.rail_reach import ports_by_function
from fransys_model.derive.facts.units import boundary, standalone
from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port, Unit
    from fransys_model.vocab.facets.plc import PlcChannelFacet, PlcRequestFacet


def unit_of(model: Model, function: Function) -> Id[Unit] | None:
    """The unit that owns `function`: its item's `Item.unit` (`None` is the top level)."""
    return items(model)[function.item].unit


@dataclasses.dataclass(frozen=True, slots=True)
class WiredPick:
    """What wiring decided: requests bound to a channel, left ambiguous, or contested.

    `ambiguous` maps a request function to the channels, in serving order, that tie for it.
    `contested` maps a channel to the kind-matched requests, in request order, that all picked it.
    """

    bound: dict[Id[Function], Id[Function]]
    ambiguous: dict[Id[Function], tuple[Id[Function], ...]]
    contested: dict[Id[Function], tuple[Id[Function], ...]]

    @property
    def unbound(self) -> set[Id[Function]]:
        """The requests that bind nothing and skip the free queue: ambiguous and contested."""
        return {*self.ambiguous, *(r for group in self.contested.values() for r in group)}


def narrow(
    request: PlcRequestFacet,
    eligible: Collection[Id[Function]],
    facts_of: Mapping[Id[Function], PlcChannelFacet],
    adjacent: Collection[Id[Function]],
) -> list[Id[Function]]:
    """The channels left of `eligible` after W2 (the asked kind) and W3 (a direct conductor).

    W2 keeps the channels of the request's signal; with none, all stay (the binding then raises
    `PLC_BINDING_SIGNAL_MISMATCH`). W3 keeps the channels one conductor from the request, if any.
    """
    kept = [c for c in eligible if channel_takes(facts_of[c], request.signal)] or list(eligible)
    return [c for c in kept if c in adjacent] or kept


@dataclasses.dataclass(frozen=True, slots=True)
class _Wiring:
    """The lookups one run reads: the net walk, the serving order and the direct conductors."""

    model: Model
    by_function: Mapping[Id[Function], list[Id[Port]]]
    channel_owner: Mapping[Id[Port], Id[Function]]
    request_owner: Mapping[Id[Port], Id[Function]]
    ranked: Mapping[Id[Function], tuple[int, PlcChannelFacet]]
    neighbours: Mapping[Id[Function], frozenset[Id[Function]]]

    def eligible(
        self, request: PlcRequestFacet, claimed: Collection[Id[Function]]
    ) -> list[Id[Function]]:
        """W1 (model-0211, amended): W1a keeps channels whose net holds no other request.

        With none, W1b keeps the channels whose net holds the subject, whatever else it carries.
        """
        subject = request.subject
        own = self.by_function.get(subject, ())
        reached = wired_functions(self.model, own, self.channel_owner) - {subject}
        free = [channel for channel in reached if channel not in claimed]
        alone = [
            channel
            for channel in free
            if not wired_functions(
                self.model, self.by_function.get(channel, ()), self.request_owner
            )
            - {channel, subject}
        ]
        return alone or free

    def left(
        self, request: PlcRequestFacet, claimed: Collection[Id[Function]]
    ) -> list[Id[Function]]:
        """The channels left for `request` after W1 to W3, in serving order."""
        facts_of = {channel: facts for channel, (_, facts) in self.ranked.items()}
        adjacent = self.neighbours.get(request.subject, ())
        found = narrow(request, self.eligible(request, claimed), facts_of, adjacent)
        return sorted(found, key=lambda channel: self.ranked[channel][0])


def uncontested(
    picked: Mapping[Id[Function], Id[Function]],
    ranked: Mapping[Id[Function], tuple[int, PlcChannelFacet]],
    requests: Sequence[PlcRequestFacet],
) -> tuple[dict[Id[Function], Id[Function]], dict[Id[Function], tuple[Id[Function], ...]]]:
    """W5 (model-0211): the uncontested picks, and each channel picked by 2+ matched requests.

    A pick of the wrong kind (W2 found none) yields to a kind-matched pick of that channel.
    """
    kind = {request.subject: request.signal for request in requests}
    matched = {s for s, c in picked.items() if channel_takes(ranked[c][1], kind[s])}
    held = {picked[subject] for subject in matched}
    pool = {s: c for s, c in picked.items() if s in matched or c not in held}
    counts = Counter(pool.values())
    bound = {subject: channel for subject, channel in pool.items() if counts[channel] == 1}
    contested: dict[Id[Function], list[Id[Function]]] = {}
    for request in requests:
        if request.subject in matched and counts[picked[request.subject]] > 1:
            contested.setdefault(picked[request.subject], []).append(request.subject)
    return bound, {channel: tuple(group) for channel, group in contested.items()}


def wired_requests(
    model: Model,
    requests: Sequence[PlcRequestFacet],
    *,
    skip: Collection[Id[Function]],
    taken: Collection[Id[Function]],
    ranked: Mapping[Id[Function], tuple[int, PlcChannelFacet]],
) -> WiredPick:
    """Which requests bind by wiring (model-0211): W1 candidates, `narrow` (W2, W3), then W4.

    `ranked` maps each channel to its place and facts; one candidate binds, several bind none.
    W5: two kind-matched picks of one channel bind neither (contested); wrong-kind picks yield.
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
    picked: dict[Id[Function], Id[Function]] = {}
    ambiguous: dict[Id[Function], tuple[Id[Function], ...]] = {}
    for request in requests:
        if request.subject in skip:
            continue
        left = wiring.left(request, set(taken))
        if len(left) > 1:
            ambiguous[request.subject] = tuple(left)
        elif left:
            picked[request.subject] = left[0]
    bound, contested = uncontested(picked, ranked, requests)
    return WiredPick(bound, ambiguous, contested)


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
