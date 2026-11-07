"""Channels that carry their own settings leave the allocation pool; a request wired to one is `PLC_CHANNEL_HAS_SETTINGS` (R1842)."""

from typing import TYPE_CHECKING, Final, cast

from fransys_model.derive.facts.plc_wiring import channel_functions, plc_settings, wired_functions
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.order import functions_in_order
from fransys_model.vocab.codes import finding
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import facets_of, functions
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.facets.plc import PlcRequestFacet

PLC_CHANNEL_HAS_SETTINGS: Final[str] = "PLC_CHANNEL_HAS_SETTINGS"


def own_settings(model: Model) -> frozenset[Id[Function]]:
    """The channel functions that carry a name, routing, `configured=False` or a scaling of their own."""
    scaled = {facet.subject for facet in facets_of(model, ScalingFacet).values()}
    return frozenset(channel for channel in channel_functions(model) if channel in plc_settings(model) or channel in scaled)


def own_clashes(model: Model, requests: Collection[PlcRequestFacet], own: Collection[Id[Function]]) -> dict[Id[Function], tuple[Id[Function], ...]]:
    """Each request function wired to channels of `own`, mapped to them."""
    by_function = build_indexes(model).ports_by_function
    owner_of = {port: channel for channel in own for port in by_function.get(channel, ())}
    found = {request.subject: wired_functions(model, by_function.get(request.subject, ()), owner_of) for request in requests}
    return {subject: tuple(cast("tuple[Id[Function], ...]", functions_in_order(model, channels))) for subject, channels in found.items() if channels}


def own_findings(model: Model, clashes: Mapping[Id[Function], tuple[Id[Function], ...]]) -> list[Finding]:
    """One `ERROR` per request wired to a channel with its own settings, naming both."""
    all_functions = functions(model)
    return [
        finding(
            PLC_CHANNEL_HAS_SETTINGS,
            (request, *channels),
            f"{ref(all_functions[request])} is wired to channel {', '.join(ref(c) for c in channels)} of a module, which carries its own "
            "settings (a name, routing, a scale or configured=False): wire the device to a channel without settings, or drop the channel's",
        )
        for request, channels in clashes.items()
    ]
