"""PW1, PW2 and PW4 of `allocate_plc`: a wired request takes its wired channel (model-0083).

The wiring walk is `vocab.plc_wiring`, the one `check_plc_wiring` reads. This module only decides,
from what it reports, which request binds to which channel by wiring (PW1, PW2) and whether an
unservable request is really open at the boundary of a standalone unit (PW4).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.membership import boundary, standalone
from fransys_model.vocab.plc_wiring import owner_of_port, ports_by_function, wired_functions
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Unit
    from fransys_model.vocab.facets.plc import PlcRequestFacet


def unit_of(model: Model, function: Function) -> Id[Unit] | None:
    """The unit that owns `function`: its item's `Item.unit` (`None` is the top level)."""
    return items(model)[function.item].unit


def wired_requests(
    model: Model,
    requests: Sequence[PlcRequestFacet],
    *,
    skip: Collection[Id[Function]],
    taken: Collection[Id[Function]],
    rank: Mapping[Id[Function], int],
) -> dict[Id[Function], Id[Function]]:
    """Which requests bind by wiring: a request function mapped to its channel function.

    A request takes the first free channel, in serving order, whose net holds no other request.
    A channel two requests share binds nobody by wiring; an unreached request stays unbound.
    """
    by_function = ports_by_function(model)
    channel_owner = owner_of_port(by_function, rank)
    request_owner = owner_of_port(by_function, {request.subject for request in requests})
    claimed = set(taken)
    bound: dict[Id[Function], Id[Function]] = {}
    for request in requests:
        subject = request.subject
        if subject in skip:
            continue
        reached = wired_functions(model, by_function.get(subject, ()), channel_owner) - {subject}
        eligible = [
            channel
            for channel in reached
            if channel not in claimed
            and wired_functions(model, by_function.get(channel, ()), request_owner) - {channel}
            == {subject}
        ]
        if eligible:
            bound[subject] = min(eligible, key=rank.__getitem__)
            claimed.add(bound[subject])
    return bound


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
