"""Bundles: nets that connect the poles of one multi-pole device travel as one trunk.

A pole end is a port at the line (0) or load (1) end of one declared pole link of a function with two or more
poles (model-0397); the source end is one every member net meets. Nets that meet one function end,
with pairwise distinct pole indices at the trunk's source, are one bundle; a net is keyed by
`physical.ports[0]`. A crossed net is in the bundle and its end carries the permutation. The line side
and the load side of a device are two trunks. A cable or a harness line (`line_conductors`) is one more bundle, a lane per conductor in core order;
where a net is in both, the line bundle wins (G07-BUNDLES).
"""

from collections import defaultdict
lazy from collections.abc import Collection

from fransys_model.derive.facts.closure import drawn_net_of, drawn_physical_nets
from fransys_model.derive.facts.roles import function_role
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, UnionFind, digest_cached
from fransys_model.vocab import Function, Port, PortTemplate
from fransys_model.vocab.facets.cable import CoreFacet
from fransys_model.vocab.markings import poles_by_role
from fransys_model.vocab.tables import conductors, facets_of, internal_links, port_templates, ports

from .line_fact import line_conductors
from .order import cores_in_lane_order
from .order_kit import source_end
from .rows_bundles import Bundle, BundleNet

__all__ = ["Bundle", "BundleNet", "bundle_of", "bundles"]

_MULTI = 2  # poles a function needs to bundle its nets
_End = tuple[Id[Function], int]  # a function and its end: 0 line, 1 load
_PoleEnd = tuple[_End, int]  # an end and the pole index there


def _function_ends(model: Model, function: Id[Function], own: dict[Id[PortTemplate], Port]) -> dict[Id[Port], _PoleEnd]:
    """Each port of `function` by end of a declared pole link; empty for one pole or a port that sits on two poles."""
    templates = {t: port_templates(model)[t] for t in own}
    links = (link for link in internal_links(model).values() if link.a in templates and link.b in templates)
    found = poles_by_role(function_role(model, function), links, templates)
    ends = {own[template.id].id: ((function, end), index) for index, pole in enumerate(found) for end, template in enumerate(pole.ends)}
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
    for physical in drawn_physical_nets(model):
        at: dict[_End, int] = {}
        for end, index in (pole_ends[p] for p in physical.ports if p in pole_ends):
            if at.setdefault(end, index) != index:
                at = {}
                break
        if at:
            nets[physical.ports[0]] = at
            (wired.update(at) if len(physical.ports) > 1 else lone.add(physical.ports[0]))
    return {n: at for n, at in nets.items() if n not in lone or not wired.intersection(at)}


def _bundle(model: Model, members: list[Id[Port]], nets: dict[Id[Port], dict[_End, int]]) -> Bundle | None:
    """The bundle of one trunk, poles taken at its source end; `None` for a trunk with no end all meet or a ragged one."""
    common = set.intersection(*(set(nets[net]) for net in members))
    if len(members) < _MULTI or not common:
        return None
    pole = {net: nets[net][source_end(model, common)] for net in members}
    if len(set(pole.values())) < len(members):
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
    found = (_bundle(model, members, nets) for members in joined.groups().values())
    return tuple(sorted((*(b for b in found if b is not None), *_line_bundles(model)), key=lambda bundle: bundle.id))


def _line_bundles(model: Model) -> list[Bundle]:
    """One bundle per cable or harness line: its wired conductors' nets in core order, if all distinct.

    A net is in one trunk: a line that shares a net with an earlier line (a common return) stays wires.
    """
    index = {facet.subject: facet.index for facet in facets_of(model, CoreFacet).values()}
    found: list[Bundle] = []
    taken: set[Id[Port]] = set()
    for ids in line_conductors(model).values():
        keys = [net.ports[0] for c in cores_in_lane_order(index, ids) if (net := drawn_net_of(model, conductors(model)[c].a)) is not None]
        if len(set(keys)) == len(keys) >= _MULTI and taken.isdisjoint(keys):
            taken.update(keys)
            found.append(Bundle(id=keys[0], nets=tuple(BundleNet(net=k, pole=i) for i, k in enumerate(keys)), form="line"))
    return found


@digest_cached(DIGEST_CACHE_SIZE)
def _member(model: Model) -> frozendict[Id[Port], tuple[tuple[Id[Port], int, str], ...]]:
    """Each bundled net's key with its `(bundle id, pole index, form)` in every bundle, line bundles first."""
    found: defaultdict[Id[Port], list[tuple[Id[Port], int, str]]] = defaultdict(list)
    made = _bundles(model)
    for bundle in (*(b for b in made if b.form != "pole"), *(b for b in made if b.form == "pole")):
        for lane in bundle.nets:
            found[lane.net].append((bundle.id, lane.pole, bundle.form))
    return frozendict({net: tuple(rows) for net, rows in found.items()})


def bundles(model: Model) -> tuple[Bundle, ...]:
    """The bundles of `model`, sorted by id; each lists its nets in pole order."""
    return _bundles(model)


def bundle_of(model: Model, port: Id[Port], forms: Collection[str] = ("pole",)) -> tuple[Id[Port], int, str] | None:
    """The `(bundle id, pole index, form)` of the physical net of `port` in a bundle of one of `forms`.

    A line bundle outranks a pole one where a net is in both. `None` when the net is in
    no bundle of those forms.
    """
    physical = drawn_net_of(model, port)
    rows = () if physical is None else _member(model).get(physical.ports[0], ())
    return next((row for row in rows if row[2] in forms), None)
