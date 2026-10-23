"""Validators: PLC bindings match the requested signal and the wiring (facets.md).

The file holds both PLC checks: `check_plc` (signal type) and `check_plc_wiring` (decision
model-0068, the wiring is the truth).
"""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.plc_wiring import binding_wiring, plc_requests, request_functions
from fransys_model.derive.facts.roles import function_channel
from fransys_model.kernel import Finding, Severity, natural_join
from fransys_model.vocab.facets.plc import PlcBindingFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import facets_of

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function

PLC_BINDING_SIGNAL_MISMATCH: Final[str] = "PLC_BINDING_SIGNAL_MISMATCH"
PLC_BINDING_WIRING_MISMATCH: Final[str] = "PLC_BINDING_WIRING_MISMATCH"


def check_plc(model: Model) -> tuple[Finding, ...]:
    """Check every `plc_binding`'s channel has the signal type its `plc_request` asked for.

    `PLC_BINDING_SIGNAL_MISMATCH` (`ERROR`): channel's `plc_channel` signal differs or is absent.
    Subjects: binding, request function, channel function; sorted by `(code, subjects, message)`.
    """
    requests = plc_requests(model)
    found: list[Finding] = []
    for binding in facets_of(model, PlcBindingFacet).values():
        request = requests.get(binding.subject)
        if request is None:
            continue
        channel = function_channel(model, binding.channel)
        if channel is not None and channel.signal is request.signal:
            continue
        offered, other = (
            ("is not declared a channel", "a declared channel")
            if channel is None
            else (f"is {channel.signal.value}", channel.signal.value)
        )
        message = (
            f"{ref(binding.subject)} asks for {request.signal.value} "
            f"but its channel {ref(binding.channel)} {offered}: rewire it to a "
            f"{request.signal.value} channel, or ask for {other}"
        )
        subjects = (binding.id, binding.subject, binding.channel)
        found.append(finding(PLC_BINDING_SIGNAL_MISMATCH, Severity.ERROR, subjects, message))
    return ordered(found)


def check_plc_wiring(model: Model) -> tuple[Finding, ...]:
    """Check every `plc_binding` agrees with what is wired to its request and channel.

    `PLC_BINDING_WIRING_MISMATCH` (`ERROR`): request or channel wired to others than the bound one.
    Subjects: binding, request, channel; sorted by `(code, subjects, message)`.
    """
    requests = request_functions(model)
    found = [
        item
        for binding in facets_of(model, PlcBindingFacet).values()
        if binding.subject in requests
        for item in _binding_findings(model, binding)
    ]
    return ordered(found)


def _binding_findings(model: Model, binding: PlcBindingFacet) -> list[Finding]:
    """The 0 to 2 findings of one binding whose function carries a `plc_request`."""
    request, channel = binding.subject, binding.channel
    request_side, channel_side = binding_wiring(model, binding)
    subjects = (binding.id, request, channel)
    messages: list[str] = []
    if request_side and channel not in request_side:
        messages.append(
            f"{ref(request)} is wired to channel {_refs(request_side)} "
            f"but bound to channel {ref(channel)}"
        )
    if channel_side and request not in channel_side:
        messages.append(
            f"channel {ref(channel)} is wired to {_refs(channel_side)} "
            f"but bound to request {ref(request)}"
        )
    return [finding(PLC_BINDING_WIRING_MISMATCH, Severity.ERROR, subjects, m) for m in messages]


def _refs(wired: Collection[Id[Function]]) -> str:
    """The references to several functions, sorted and joined with `, `."""
    return natural_join(ref(function) for function in wired)
