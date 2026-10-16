"""Tests: the role readers refine a kind's table row by the facets the one site may read."""

from roles_plants import every_kind_member, function_of, roles_plant

from fransys_model.derive import (
    conductor_role,
    function_role,
    item_role,
    link_role,
    net_class_role,
    port_role,
)
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    LinkKind,
    LinkRest,
    NetClass,
    PortRole,
)
from fransys_model.vocab.tables import conductors, internal_links, nets, ports

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
