"""Validators: PLC bindings match the requested signal and the wiring (facets.md, ROADMAP WP13).

The file holds both PLC checks: `check_plc` (signal type) and `check_plc_wiring` (decision
model-0068, the wiring is the truth).
"""

import dataclasses
from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.plc_wiring import owner_of_port, ports_by_function, wired_functions
from fransys_model.vocab.tables import facets_of, functions

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port

PLC_BINDING_SIGNAL_MISMATCH: Final[str] = "PLC_BINDING_SIGNAL_MISMATCH"
PLC_BINDING_WIRING_MISMATCH: Final[str] = "PLC_BINDING_WIRING_MISMATCH"


def check_plc(model: Model) -> tuple[Finding, ...]:
    """Check every `plc_binding`'s channel has the signal type its `plc_request` asked for.

    `PLC_BINDING_SIGNAL_MISMATCH` (`ERROR`): channel's `plc_channel` signal differs or is absent.
    Subjects: binding, request function, channel function; sorted by `(code, subjects, message)`.
    """
    requests = {facet.subject: facet for facet in facets_of(model, PlcRequestFacet).values()}
    channels = {facet.subject: facet for facet in facets_of(model, PlcChannelFacet).values()}
    all_functions = functions(model)
    found: list[Finding] = []
    for binding in facets_of(model, PlcBindingFacet).values():
        request = requests.get(binding.subject)
        if request is None:
            continue
        target = all_functions[binding.channel]
        channel = None if target.template is None else channels.get(target.template)
        if channel is not None and channel.signal is request.signal:
            continue
        asked = all_functions[binding.subject]
        offered = "is not declared a channel" if channel is None else f"is {channel.signal.value}"
        found.append(
            Finding(
                code=PLC_BINDING_SIGNAL_MISMATCH,
                severity=Severity.ERROR,
                subjects=(binding.id, binding.subject, binding.channel),
                message=(
                    f"{'/'.join(asked.key)} asks for {request.signal.value} "
                    f"but its channel {'/'.join(target.key)} {offered}"
                ),
            )
        )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))


def check_plc_wiring(model: Model) -> tuple[Finding, ...]:
    """Check every `plc_binding` agrees with what is wired to its request and channel.

    `PLC_BINDING_WIRING_MISMATCH` (`ERROR`): request or channel wired to others than the bound one.
    Subjects: binding, request, channel; sorted by `(code, subjects, message)`.
    """
    request_functions = {facet.subject for facet in facets_of(model, PlcRequestFacet).values()}
    channel_templates = {facet.subject for facet in facets_of(model, PlcChannelFacet).values()}
    all_functions = functions(model)
    channel_functions = {f.id for f in all_functions.values() if f.template in channel_templates}
    by_function = ports_by_function(model)
    wiring = _Wiring(
        model=model,
        all_functions=all_functions,
        by_function=by_function,
        device_of=owner_of_port(by_function, request_functions),
        channel_of=owner_of_port(by_function, channel_functions),
    )
    found = [
        finding
        for binding in facets_of(model, PlcBindingFacet).values()
        if binding.subject in request_functions
        for finding in _binding_findings(wiring, binding)
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))


@dataclasses.dataclass(frozen=True, slots=True)
class _Wiring:
    """The lookups `check_plc_wiring` reads: functions, ports by function, port owners."""

    model: Model
    all_functions: Mapping[Id[Function], Function]
    by_function: Mapping[Id[Function], list[Id[Port]]]
    device_of: Mapping[Id[Port], Id[Function]]
    channel_of: Mapping[Id[Port], Id[Function]]


def _binding_findings(wiring: _Wiring, binding: PlcBindingFacet) -> list[Finding]:
    """The 0 to 2 findings of one binding whose function carries a `plc_request`."""
    request, channel = binding.subject, binding.channel
    subjects = (binding.id, request, channel)
    found: list[Finding] = []
    on_request = wiring.by_function.get(request, ())
    request_side = wired_functions(wiring.model, on_request, wiring.channel_of) - {request}
    if request_side and channel not in request_side:
        found.append(
            _mismatch(
                subjects,
                f"{_key(wiring, request)} is wired to channel {_keys(wiring, request_side)} "
                f"but bound to channel {_key(wiring, channel)}",
            )
        )
    on_channel = wiring.by_function.get(channel, ())
    channel_side = wired_functions(wiring.model, on_channel, wiring.device_of) - {channel}
    if channel_side and request not in channel_side:
        found.append(
            _mismatch(
                subjects,
                f"channel {_key(wiring, channel)} is wired to {_keys(wiring, channel_side)} "
                f"but bound to request {_key(wiring, request)}",
            )
        )
    return found


def _key(wiring: _Wiring, function: Id[Function]) -> str:
    """The function's key joined with `/`, the name a message prints."""
    return "/".join(wiring.all_functions[function].key)


def _keys(wiring: _Wiring, wired: Collection[Id[Function]]) -> str:
    """The keys of several functions, sorted and joined with `, `."""
    return ", ".join(sorted(_key(wiring, function) for function in wired))


def _mismatch(subjects: tuple[Id[Any], ...], message: str) -> Finding:
    """A `PLC_BINDING_WIRING_MISMATCH` `ERROR` on `subjects`."""
    return Finding(
        code=PLC_BINDING_WIRING_MISMATCH,
        severity=Severity.ERROR,
        subjects=subjects,
        message=message,
    )
