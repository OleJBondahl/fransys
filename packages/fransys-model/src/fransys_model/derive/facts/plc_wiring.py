"""The one PLC wiring walk: which functions share a physical net (decisions model-0068, 0083).

`check_plc_wiring` (the check) and `derive.passes.plc_allocation` (PW1, PW2 and PW4 of the
PLC-WIRED spec) both ask the same question: which functions of a given set share a physical net
with a function's ports. It is answered here, over `vocab.closure.net_of`, and nowhere else.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.closure import net_of
from fransys_model.derive.facts.rail_reach import ports_by_function
from fransys_model.derive.facts.roles import plc_channel_facets
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import conductors, facets_of, functions, ports
lazy from fransys_model.vocab.enums import SignalType

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port


def owner_of_port(
    by_function: Mapping[Id[Function], list[Id[Port]]], owners: Collection[Id[Function]]
) -> dict[Id[Port], Id[Function]]:
    """Each port of a function in `owners`, mapped to that function."""
    return {port: function for function in owners for port in by_function.get(function, ())}


def wired_functions(
    model: Model, own_ports: Collection[Id[Port]], owner_of: Mapping[Id[Port], Id[Function]]
) -> frozenset[Id[Function]]:
    """The functions of `owner_of` that share a physical net with any of `own_ports`.

    A function that owns some of `own_ports` itself is included when a port of it (or another
    of its ports) is on the same net; callers subtract the function they ask about.
    """
    found: set[Id[Function]] = set()
    for port in own_ports:
        net = net_of(model, port)
        if net is not None:
            found.update(owner_of[p] for p in net.ports if p in owner_of)
    return frozenset(found)


def direct_neighbours(model: Model) -> dict[Id[Function], frozenset[Id[Function]]]:
    """Each function mapped to the functions one conductor joins it to (model-0211).

    A net also passes terminals, links and mates; this is the single conductor only.
    """
    all_ports = ports(model)
    found: dict[Id[Function], set[Id[Function]]] = {}
    for conductor in conductors(model).values():
        a, b = all_ports[conductor.a].function, all_ports[conductor.b].function
        found.setdefault(a, set()).add(b)
        found.setdefault(b, set()).add(a)
    return {function: frozenset(others) for function, others in found.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def plc_requests(model: Model) -> frozendict[Id[Function], PlcRequestFacet]:
    """Each function that asks for a PLC signal, mapped to its `plc_request` facet."""
    return frozendict({f.subject: f for f in facets_of(model, PlcRequestFacet).values()})


def request_functions(model: Model) -> frozenset[Id[Function]]:
    """The functions that carry a `plc_request`."""
    return frozenset(plc_requests(model))


def channel_functions(model: Model) -> frozenset[Id[Function]]:
    """The functions whose template is a declared PLC channel."""
    channels = plc_channel_facets(model)
    return frozenset(f.id for f in functions(model).values() if f.template in channels)


@digest_cached(DIGEST_CACHE_SIZE)
def _owners(
    model: Model,
) -> tuple[
    dict[Id[Function], list[Id[Port]]], dict[Id[Port], Id[Function]], dict[Id[Port], Id[Function]]
]:
    """Ports by function, and the port owners among the requests and among the channels."""
    by_function = ports_by_function(model)
    return (
        by_function,
        owner_of_port(by_function, request_functions(model)),
        owner_of_port(by_function, channel_functions(model)),
    )


def binding_wiring(
    model: Model, binding: PlcBindingFacet
) -> tuple[frozenset[Id[Function]], frozenset[Id[Function]]]:
    """The channels wired to the bound request, then the requests wired to the bound channel.

    Each side leaves out the bound function itself; the check compares it with the binding.
    """
    by_function, device_of, channel_of = _owners(model)
    request, channel = binding.subject, binding.channel
    request_side = wired_functions(model, by_function.get(request, ()), channel_of) - {request}
    channel_side = wired_functions(model, by_function.get(channel, ()), device_of) - {channel}
    return request_side, channel_side


def channel_takes(channel_facts: PlcChannelFacet, signal: SignalType) -> bool:
    """Whether a channel with these facts takes a request or path of `signal` (PLC-10).

    The one eligibility for a PLC channel: `allocate_plc` and the author's module pick both ask it.
    Example: a `di` channel takes `SignalType.DI` and nothing else.
    """
    return channel_facts.signal is signal
