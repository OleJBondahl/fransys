"""PLC channel allocation pass (design/connectivity.md and design/derive.md)."""

import dataclasses
from collections import deque
from typing import TYPE_CHECKING, Final

from fransys_kernel import require_origin
from fransys_model.derive.facts.roles import plc_channel_facets
from fransys_model.derive.lookups import unit_chain
from fransys_model.derive.order import (
    ChannelTie,
    ModuleKey,
    natural_key,
    plc_channel_tie,
    plc_module_key,
    plc_rack_key,
)
from fransys_model.derive.passes._plc_ambiguous import ambiguous_findings
from fransys_model.derive.passes._plc_contested import contested_findings
from fransys_model.derive.passes._plc_wired import (
    reaches_open_boundary,
    unit_of,
    wired_requests,
)
from fransys_model.kernel import Finding, Model, Severity, evolve, make_id
from fransys_model.vocab.codes import fix_text
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import facets_of, functions, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Origin
    from fransys_model.vocab.core import Function, Unit
    from fransys_model.vocab.enums import SignalType
    from fransys_model.vocab.facets.plc import PlcChannelFacet

PLC_REQUEST_UNSERVABLE: Final[str] = "PLC_REQUEST_UNSERVABLE"

_NO_RACK: Final[ModuleKey] = ((0, 0), natural_key(""), ())

type _Order = tuple[ModuleKey, ModuleKey, ChannelTie]


def _ranked(model: Model) -> list[tuple[Function, PlcChannelFacet]]:
    """Every channel function with its facts, in the one global serving order.

    The order is `plc_rack_key`, `plc_module_key`, `plc_channel_tie`.
    No designation is read; `_channels` cuts it into one queue per (unit, signal).
    """
    channel_of = plc_channel_facets(model)
    modules = items(model)
    ranked: list[tuple[_Order, Function, PlcChannelFacet]] = []
    for function in functions(model).values():
        facet = channel_of.get(function.template)
        if facet is None:
            continue
        module = modules[function.item]
        rack = _NO_RACK if module.parent is None else plc_rack_key(modules[module.parent])
        order = (rack, plc_module_key(module), plc_channel_tie(facet.channel, function))
        ranked.append((order, function, facet))
    return [(function, facet) for _, function, facet in sorted(ranked, key=lambda r: r[0])]


def _channels(
    model: Model, ranked: list[tuple[Function, PlcChannelFacet]]
) -> dict[tuple[Id[Unit] | None, SignalType], list[Function]]:
    """`ranked` cut into channel functions by (unit, signal), each list in serving order.

    A channel's unit is its module item's `Item.unit`; a unit declares a signal when a key with
    it exists here (a module in a nested unit counts for that unit only).
    """
    channels: dict[tuple[Id[Unit] | None, SignalType], list[Function]] = {}
    for function, facet in ranked:
        channels.setdefault((unit_of(model, function), facet.signal), []).append(function)
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
            f"{ref(function)} asks for {request.signal.value} as {request.signal_name!r}, {cause}"
        ),
        fix=fix_text(PLC_REQUEST_UNSERVABLE),
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
    request served and one finding per request left (`PLC_CHANNEL_CONTESTED` once per channel wired
    to two or more kind-matched requests, which bind nothing); a model with nothing to bind comes
    back as the same object.
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
    pick = wired_requests(
        model,
        requests,
        skip=bound_subjects,
        taken=existing,
        ranked={function.id: (place, facts) for place, (function, facts) in enumerate(ranked)},
    )
    taken = existing | set(pick.bound.values()) | set(pick.contested)
    channels = _channels(model, ranked)
    free = {
        key: deque(function for function in queue if function.id not in taken)
        for key, queue in channels.items()
    }
    served: list[PlcBindingFacet] = []
    findings = [
        *ambiguous_findings(model, requests, pick.ambiguous),
        *contested_findings(model, pick.contested),
    ]
    origins: dict[Id[PlcBindingFacet], Origin] = {}
    for request in requests:
        if request.subject in bound_subjects or request.subject in pick.unbound:
            continue
        function = all_functions[request.subject]
        channel = pick.bound.get(request.subject)
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
