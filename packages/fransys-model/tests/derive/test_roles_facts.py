"""Tests: the role readers refine a kind's table row by the facets the one site may read."""

from decimal import Decimal

import pytest
from current_plant import device, rate
from plant import Plant
from roles_plants import every_kind_member, function_of, roles_plant
from test_breaking_check import _battery, _fn

from fransys_model.checks.ratings_breaking import check_breaking
from fransys_model.derive import (
    conductor_ends,
    conductor_role,
    function_role,
    item_role,
    link_role,
    net_class_role,
    port_role,
)
from fransys_model.derive.facts.current.bounds import LimitRole, _limits_of
from fransys_model.derive.facts.stated_ratings import fitted_link_rating
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import BreakingPoint, Rating, RatingFacet
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    LinkKind,
    LinkRest,
    NetClass,
    PortRole,
)
from fransys_model.vocab.roles import CONDUCTOR_ROLES
from fransys_model.vocab.tables import conductors, internal_links, nets, ports
from fransys_model.vocab.templates import FunctionTemplate

MODEL, IDS = roles_plant()


def test_the_worked_example_a_contact_is_read_from_the_role_not_the_kind() -> None:
    """NO, NC and CO functions are contacts; the coil is not."""
    for name in ("no", "nc", "co"):
        assert function_role(MODEL, IDS[name]).contact
    assert not function_role(MODEL, IDS["coil"]).contact
    assert function_role(MODEL, IDS["coil"]).operator


def test_a_plc_channel_function_is_a_channel_because_of_its_facet() -> None:
    """A generic function whose template has a `PlcChannelFacet` is a channel."""
    assert function_of(MODEL, "channel_by_facet").kind is FunctionKind.GENERIC
    assert function_role(MODEL, IDS["channel_by_facet"]).channel
    assert not function_role(MODEL, IDS["generic"]).channel


def test_a_protection_with_a_breaking_rating_protects() -> None:
    """The planted protection has a breaking rating."""
    assert function_role(MODEL, IDS["protection"]).protects


def test_a_connector_is_a_pin_group() -> None:
    """A connector function is `pin_group`, a terminal is not."""
    assert function_role(MODEL, IDS["connector"]).pin_group
    assert not function_role(MODEL, IDS["terminal_1"]).pin_group


def test_item_roles_of_the_strip_the_bar_and_the_cable() -> None:
    """The strip, bar and cable items read their kind's flags."""
    assert item_role(MODEL, IDS["item:strip"]).strip
    assert item_role(MODEL, IDS["item:bar"]).bar_holder
    assert item_role(MODEL, IDS["item:cable"]).cable
    assert not item_role(MODEL, IDS["item:generic"]).strip


def test_a_terminals_two_ports_are_internal_and_external() -> None:
    """The one reader of `Port.role` gives the stored role."""
    held = [p.id for p in ports(MODEL).values() if p.function == IDS["terminal_1"]]
    assert {port_role(MODEL, p) for p in held} == {PortRole.INTERNAL, PortRole.EXTERNAL}


def test_every_function_kind_gets_a_role_without_a_raise() -> None:
    """All fifteen kinds occur in the plant and each has a role."""
    seen = set()
    for name in IDS:
        if name.startswith(("item:", "port:", "net_", "conductor_")):
            continue
        function_role(MODEL, IDS[name])
        seen.add(function_of(MODEL, name).kind)
    assert seen == set(every_kind_member(FunctionKind))


def test_conductor_and_net_class_roles_follow_their_kind() -> None:
    """One role per planted conductor and net."""
    for c in conductors(MODEL).values():
        assert conductor_role(MODEL, c.id) is not None
        assert (c.kind is ConductorKind.JUMPER) is conductor_role(MODEL, c.id).bridge
    for n in nets(MODEL).values():
        assert (n.net_class is NetClass.PE) is net_class_role(MODEL, n.id).earth


def test_a_link_rest_is_the_declared_one_else_the_functions() -> None:
    """Every link has a role; the pole and switched flags follow the kind."""
    for link in internal_links(MODEL).values():
        role = link_role(MODEL, link.id)
        assert role.switched is (link.kind is LinkKind.SWITCHED)
        if link.rest is not None:
            assert role.rest is link.rest
        assert role.rest in (None, *LinkRest)


def test_the_wire_flag_is_the_wire_kind_alone() -> None:
    """Oracle: `ConductorRole.wire` equals `kind is WIRE` for every `ConductorKind`."""
    for kind in every_kind_member(ConductorKind):
        assert CONDUCTOR_ROLES[kind].wire is (kind is ConductorKind.WIRE)


def _rated(key: str, kind: FunctionKind, *, breaking: bool) -> tuple[Plant, Id[Function]]:
    """A 400 A device `key` of `kind`, its template stating a breaking point when `breaking`."""
    plant = Plant()
    device(plant, key, amps="400", kind=kind, link=LinkKind.CONDUCTIVE)
    if breaking:
        point = BreakingPoint(voltage_v=Decimal(250), current_a=Decimal(10000))
        template = make_id(FunctionTemplate, (key, "f"))
        facet = RatingFacet(
            id=make_id(RatingFacet, (key,)),
            key=(key,),
            subject=template,
            rating=Rating(breaking_ac=(point,)),
        )
        plant.add(facet)
    return plant, Plant.function_id(key, "f")


def _fit_link(plant: Plant, holder: str) -> None:
    """Fit a 10 A fuse link in item `holder`."""
    part = rate(plant, "L", "10")
    plant.item("L", part=part, parent=make_id(Item, (holder,)))


def test_a_fitted_link_is_read_for_a_function_that_protects_not_for_one_that_does_not() -> None:
    """R1: `fitted_link_rating` follows `protects`; a plain load with a link has none."""
    plant, fn = _rated("F", FunctionKind.PROTECTION, breaking=False)
    _fit_link(plant, "F")
    assert fitted_link_rating(plant.model(), fn) is not None
    plant, fn = _rated("F", FunctionKind.LOAD, breaking=False)
    _fit_link(plant, "F")
    assert fitted_link_rating(plant.model(), fn) is None


def test_a_protection_rating_is_a_current_limit_only_for_a_function_that_protects() -> None:
    """B2: the rating bounds the current when `protects`; a load's rating bounds nothing."""
    plant, fn = _rated("F", FunctionKind.PROTECTION, breaking=False)
    assert {b.role for b in _limits_of(plant.model(), fn)} == {LimitRole.PROTECTION}
    plant, fn = _rated("G", FunctionKind.LOAD, breaking=False)
    assert _limits_of(plant.model(), fn) == []


def test_the_breaking_check_reads_a_function_that_protects() -> None:
    """Y3: the main fuse, a function that protects, is checked against the prospective fault."""
    model = _battery(draws=(("2.5",), ("0.8", "0.8", "0.8"))).model()
    assert {f.subjects for f in check_breaking(model)} == {(_fn("FM"),)}


def test_a_protections_conductive_link_is_a_pole_a_loads_is_not() -> None:
    """`link_role` takes the pole from `protects`: only the protection's conductive link."""
    for kind, pole in ((FunctionKind.PROTECTION, True), (FunctionKind.LOAD, False)):
        plant, _ = _rated("F", kind, breaking=False)
        model = plant.model()
        (link,) = internal_links(model).values()
        assert link.kind is LinkKind.CONDUCTIVE
        assert link_role(model, link.id).pole is pole


def test_conductor_ends_are_the_authored_a_then_b_and_an_unknown_conductor_raises() -> None:
    """Each planted conductor gives `(a, b)` in that order (model-0340)."""
    assert conductors(MODEL)
    for c in conductors(MODEL).values():
        assert conductor_ends(MODEL, c.id) == (c.a, c.b)
        assert c.a != c.b
    with pytest.raises(KeyError):
        conductor_ends(MODEL, next(iter(ports(MODEL))))  # ty: ignore[invalid-argument-type] -- a port id, no conductor
