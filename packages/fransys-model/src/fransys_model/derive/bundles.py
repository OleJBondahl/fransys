"""Bundles: nets that connect the poles of one multi-pole device travel as one trunk.

A pole end is a port at the line (0) or load (1) end of one pole of a function with two or more
poles. Nets that meet one function end, with pairwise distinct pole indices at the trunk's source,
are one bundle; a net is keyed by `physical.ports[0]`. A crossed net is in the bundle and its end
carries the permutation. The line side and the load side of a device are two trunks.
"""

from collections import defaultdict

from fransys_model.derive.facts.closure import net_of, physical_nets
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
from fransys_model.vocab import Function, Port, PortTemplate
from fransys_model.vocab.tables import ports

from .pole_lists import poles_of
from .rows_bundles import Bundle, BundleNet

__all__ = ["Bundle", "BundleNet", "bundle_of", "bundles"]

_MULTI = 2  # poles a function needs to bundle its nets
_End = tuple[Id[Function], int]  # a function and its end: 0 line, 1 load
_PoleEnd = tuple[_End, int]  # an end and the pole index there


def _function_ends(
    model: Model, function: Id[Function], own: dict[Id[PortTemplate], Port]
) -> dict[Id[Port], _PoleEnd]:
    """Each port of `function` by pole end; empty for one pole or a port that sits on two poles."""
    found = poles_of(model, own)
    ends = {
        own[template.id].id: ((function, end), index)
        for index, pole in enumerate(found)
        for end, template in enumerate(pole.ends)
    }
    return ends if len(found) >= _MULTI and len(ends) == 2 * len(found) else {}


@digest_cached(DIGEST_CACHE_SIZE)
def _pole_ends(model: Model) -> frozendict[Id[Port], _PoleEnd]:
    """Every port that is the end of a pole of a multi-pole function."""
    own_of: defaultdict[Id[Function], dict[Id[PortTemplate], Port]] = defaultdict(dict)
    for port in ports(model).values():
        if port.template is not None:
            own_of[port.function][port.template] = port
    found: dict[Id[Port], _PoleEnd] = {}
    for function, own in own_of.items():
        found.update(_function_ends(model, function, own))
    return frozendict(found)


def _net_ends(model: Model) -> dict[Id[Port], dict[_End, int]]:
    """Each net by the pole index it takes at each function end it meets.

    A net that takes two poles of one end is shorted and out. A lone port is an unwired pole: out
    wherever its end has a wired net, kept when every pole there is unwired.
    """
    pole_ends = _pole_ends(model)
    nets: dict[Id[Port], dict[_End, int]] = {}
    lone: set[Id[Port]] = set()
    wired: set[_End] = set()
    for physical in physical_nets(model):
        at: dict[_End, int] = {}
        for end, index in (pole_ends[p] for p in physical.ports if p in pole_ends):
            if at.setdefault(end, index) != index:
                at = {}
                break
        if at:
            nets[physical.ports[0]] = at
            (wired.update(at) if len(physical.ports) > 1 else lone.add(physical.ports[0]))
    return {n: at for n, at in nets.items() if n not in lone or not wired.intersection(at)}


def _bundle(members: list[Id[Port]], nets: dict[Id[Port], dict[_End, int]]) -> Bundle | None:
    """The bundle of one trunk, poles taken at its source end; `None` for a ragged trunk."""
    source = min(end for net in members for end in nets[net])
    pole = {net: nets[net].get(source, nets[net][min(nets[net])]) for net in members}
    if len(members) < _MULTI or len(set(pole.values())) < len(members):
        return None
    ordered = sorted(members, key=lambda net: (pole[net], net))
    lanes = tuple(BundleNet(net=net, pole=pole[net]) for net in ordered)
    return Bundle(id=ordered[0], nets=lanes)


@digest_cached(DIGEST_CACHE_SIZE)
def _bundles(model: Model) -> tuple[Bundle, ...]:
    """The bundles: each group of nets at shared function ends, if its source poles differ."""
    nets = _net_ends(model)
    at_end: defaultdict[_End, list[Id[Port]]] = defaultdict(list)
    for net, ends in nets.items():
        for end in ends:
            at_end[end].append(net)
    joined = UnionFind(nets)
    for group in at_end.values():
        joined.union_all(group)
    found = (_bundle(members, nets) for members in joined.groups().values())
    return tuple(sorted((b for b in found if b is not None), key=lambda bundle: bundle.id))


@digest_cached(DIGEST_CACHE_SIZE)
def _member(model: Model) -> frozendict[Id[Port], tuple[Id[Port], int]]:
    """Each bundled net's key with its bundle id and pole index."""
    return frozendict({n.net: (b.id, n.pole) for b in _bundles(model) for n in b.nets})


def bundles(model: Model) -> tuple[Bundle, ...]:
    """The bundles of `model`, sorted by id; each lists its nets in pole order."""
    return _bundles(model)


def bundle_of(model: Model, port: Id[Port]) -> tuple[Id[Port], int] | None:
    """The `(bundle id, pole index)` of the physical net of `port`, or `None` when in no bundle."""
    physical = net_of(model, port)
    return None if physical is None else _member(model).get(physical.ports[0])
