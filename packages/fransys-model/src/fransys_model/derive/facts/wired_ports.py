"""Which ports carry any connection, and the two-port functions wired at one end only."""

from fransys_model.derive.facts.joins import joined_ports
from fransys_model.derive.facts.mates import mate_pairs
from fransys_model.derive.facts.net_facts import declared_nets_of
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.unit_index import boundary_owners
from fransys_model.derive.facts.units import standalone
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.facets.cable import OpenCoreFacet
from fransys_model.vocab.tables import HasTables, conductors, facets_of, functions, ports, unused_ports
lazy from fransys_model.vocab.core import Function, Port

_TWO_PORTS = 2


@digest_cached(DIGEST_CACHE_SIZE)
def mated_ports(model: Model) -> frozenset[Id[Port]]:
    """Every port that sits on a mate: a mate pairs the ports of equal name."""
    return frozenset(port for _, a, b in mate_pairs(model) for port in (a, b))


@digest_cached(DIGEST_CACHE_SIZE)
def wired_ports(model: HasTables) -> frozenset[Id[Port]]:
    """Every port a conductor ends on, a header join joins, or an open core lands at."""
    ends = {end for c in conductors(model).values() for end in (c.a, c.b)}
    ends |= joined_ports(model)
    ends |= {f.at for f in facets_of(model, OpenCoreFacet).values() if f.at is not None}
    return frozenset(ends)


@digest_cached(DIGEST_CACHE_SIZE)
def half_connected(model: Model) -> tuple[tuple[Function, Port], ...]:
    """Each through function of two ports used at one, with its open port, in port order.

    A port declared unused counts as used; so does a port of a boundary function whose unit is built alone (R1782).
    """
    owners = boundary_owners(model)
    used = wired_ports(model) | mated_ports(model) | {record.port for record in unused_ports(model).values()}
    found = []
    for function_id, held in build_indexes(model).ports_by_function.items():
        if len(held) != _TWO_PORTS or not function_role(model, function_id).through:
            continue
        alone = function_id in owners and all(standalone(model, unit) for unit in owners[function_id])
        taken = [alone or port in used or bool(declared_nets_of(model, port)) for port in held]
        if taken.count(True) == 1:
            found.append((functions(model)[function_id], ports(model)[held[taken.index(False)]]))
    return tuple(found)
