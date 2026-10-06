"""PLC channel allocation pass (design/connectivity.md and design/derive.md)."""

import dataclasses
from collections import deque
from typing import TYPE_CHECKING, Final

from fransys_model.derive.lookups import position_rank, unit_chain
from fransys_model.derive.passes._plc_wired import (
    reaches_open_boundary,
    unit_of,
    wired_requests,
)
from fransys_model.kernel import Finding, Model, Severity, evolve, make_id
from fransys_model.kernel.origin import require_origin
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of, functions, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Origin
    from fransys_model.vocab.core import Function, Unit
    from fransys_model.vocab.enums import SignalType

PLC_REQUEST_UNSERVABLE: Final[str] = "PLC_REQUEST_UNSERVABLE"

type _Order = tuple[tuple[str, ...], tuple[int, int], tuple[str, ...], int, Id[Function]]


def _ranked(model: Model) -> list[tuple[Function, SignalType]]:
    """Every channel function with its signal, in the one global serving order.

    The order is rack key, `position` (`None` last), own key, `plc_channel` number, function id.
    No designation is read; `_channels` cuts it into one queue per (unit, signal).
    """
    channel_of = {facet.subject: facet for facet in facets_of(model, PlcChannelFacet).values()}
    modules = items(model)
    ranked: list[tuple[_Order, Function, SignalType]] = []
    for function in functions(model).values():
        facet = channel_of.get(function.template)
        if facet is None:
            continue
        module = modules[function.item]
        rack = () if module.parent is None else modules[module.parent].key
        order = (rack, position_rank(module), module.key, facet.channel, function.id)
        ranked.append((order, function, facet.signal))
    return [(function, signal) for _, function, signal in sorted(ranked, key=lambda r: r[0])]


def _channels(
    model: Model, ranked: list[tuple[Function, SignalType]]
) -> dict[tuple[Id[Unit] | None, SignalType], list[Function]]:
    """`ranked` cut into channel functions by (unit, signal), each list in serving order.

    A channel's unit is its module item's `Item.unit`; a unit declares a signal when a key with
    it exists here (a module in a nested unit counts for that unit only).
    """
    channels: dict[tuple[Id[Unit] | None, SignalType], list[Function]] = {}
    for function, signal in ranked:
        channels.setdefault((unit_of(model, function), signal), []).append(function)
    return channels


def _serving(
    model: Model,
    unit: Id[Unit] | None,
    signal: SignalType,
    channels: dict[tuple[Id[Unit] | None, SignalType], list[Function]],
) -> tuple[Id[Unit] | None, SignalType]:
    """The first unit of `unit`'s chain (it, its parents, the top level) that declares `signal`.

    Falls back to `unit`'s own key when none does, so the request is unservable.
    """
    links = [] if unit is None else unit_chain(model, unit)
    key = next(((link, signal) for link in (*links, None) if (link, signal) in channels), None)
    return (unit, signal) if key is None else key


def _unservable(function: Function, request: PlcRequestFacet, *, declared: bool) -> Finding:
    cause = (
        f"but its unit declares no {request.signal.value} channel"
        if not declared
        else f"but every {request.signal.value} channel of its unit is taken"
    )
    return Finding(
        code=PLC_REQUEST_UNSERVABLE,
        severity=Severity.ERROR,
        subjects=(request.id, function.id),
        message=(
            f"{'/'.join(function.key)} asks for {request.signal.value} "
            f"as {request.signal_name!r}, {cause}"
        ),
    )


def allocate_plc(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Bind every `plc_request` facet to a free channel of matching `SignalType`.

    Wiring first: a request whose ports share a physical net with channel functions binds to the
    first free one in serving order whose net holds no other request's function, in any unit. The
    rest are served by the first unit on their chain (item's unit, then each `Unit.parent`, top
    level last) that declares a channel of their signal type, from one free queue per (unit, signal
    type). Siblings never share and nothing reaches downward. If that unit's channels are all taken,
    or the chain declares none, the request gets `PLC_REQUEST_UNSERVABLE` with no fall-through.
    Requests serve by `(priority, requesting Function.key, Function.id)`, channels by `(rack
    Item.key, module position, module Item.key, plc_channel.channel, Function.id)`. A request
    already carrying a `plc_binding` is skipped. Returns the model with one `plc_binding` per
    request served and one finding per request left; a model with nothing to bind comes back as the
    same object.
    """
    bindings = facets_of(model, PlcBindingFacet)
    bound_subjects = {binding.subject for binding in bindings.values()}
    all_functions = functions(model)
    requests = sorted(
        facets_of(model, PlcRequestFacet).values(),
        key=lambda request: (request.priority, all_functions[request.subject].key, request.subject),
    )
    ranked = _ranked(model)
    existing = {binding.channel for binding in bindings.values()}
    wired = wired_requests(
        model,
        requests,
        skip=bound_subjects,
        taken=existing,
        rank={function.id: place for place, (function, _) in enumerate(ranked)},
    )
    taken = existing | set(wired.values())
    channels = _channels(model, ranked)
    free = {
        key: deque(function for function in queue if function.id not in taken)
        for key, queue in channels.items()
    }
    served: list[PlcBindingFacet] = []
    findings: list[Finding] = []
    origins: dict[Id[PlcBindingFacet], Origin] = {}
    for request in requests:
        if request.subject in bound_subjects:
            continue
        function = all_functions[request.subject]
        channel = wired.get(request.subject)
        if channel is None:
            queue = _serving(model, unit_of(model, function), request.signal, channels)
            available = free.get(queue)
            if not available:
                declared = queue in channels
                if declared or not reaches_open_boundary(model, function):
                    findings.append(_unservable(function, request, declared=declared))
                continue
            channel = available.popleft().id
        key = (*function.key, "plc_binding")
        binding = PlcBindingFacet(
            id=make_id(PlcBindingFacet, key), key=key, subject=function.id, channel=channel
        )
        served.append(binding)
        origins[binding.id] = require_origin(model.origins, request.id)
    ordered = tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    if not served:
        return model, ordered
    evolved = evolve(model, put=served, origin=origins[served[0].id])
    return dataclasses.replace(evolved, origins=frozendict({**evolved.origins, **origins})), ordered
