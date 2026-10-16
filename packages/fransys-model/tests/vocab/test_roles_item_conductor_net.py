"""Tests: the item, conductor and net-class role tables are complete and match their branches."""

from fransys_model import derive
from fransys_model.vocab import enums
from fransys_model.vocab.enums import ConductorKind, ItemKind, NetClass
from fransys_model.vocab.roles import CONDUCTOR_ROLES, ITEM_ROLES, NET_CLASS_ROLES


def test_every_member_of_the_three_enums_has_a_row() -> None:
    """`ItemKind`, `ConductorKind` and `NetClass` are each fully keyed."""
    assert set(ITEM_ROLES) == set(ItemKind)
    assert set(CONDUCTOR_ROLES) == set(ConductorKind)
    assert set(NET_CLASS_ROLES) == set(NetClass)


def test_a_jumper_rail_busbar_and_mount_is_a_link_never_a_wire() -> None:
    """G-POT-20: these join nets and carry no wire; a wire and a core carry and join nothing."""
    for kind in (
        ConductorKind.JUMPER,
        ConductorKind.RAIL,
        ConductorKind.BUSBAR,
        ConductorKind.MOUNT,
    ):
        assert CONDUCTOR_ROLES[kind].joins_net
        assert not CONDUCTOR_ROLES[kind].carries
    for kind in (ConductorKind.WIRE, ConductorKind.CORE):
        assert CONDUCTOR_ROLES[kind].carries
        assert not CONDUCTOR_ROLES[kind].joins_net


def test_a_lead_is_a_link_that_lands_a_line_by_its_docstring() -> None:
    """enums.py 157-165 names LEAD a link; `contact_lines` lands it, `overview_conns` does not."""
    lead = CONDUCTOR_ROLES[ConductorKind.LEAD]
    assert lead.joins_net
    assert lead.lead
    assert lead.lands
    assert not lead.carries


def test_only_the_jumper_bridges_and_only_a_jumper_or_rail_is_a_rail_link() -> None:
    """The two sets `wiring.py:74` and `power.py:126` read."""
    assert {k for k, r in CONDUCTOR_ROLES.items() if r.bridge} == {ConductorKind.JUMPER}
    rails = {ConductorKind.JUMPER, ConductorKind.RAIL}
    assert {k for k, r in CONDUCTOR_ROLES.items() if r.rail_link} == rails


def test_earth_is_the_pe_class_alone() -> None:
    """Only `PE` is earth."""
    assert {k for k, r in NET_CLASS_ROLES.items() if r.earth} == {NetClass.PE}


def test_item_kind_is_one_enum_in_vocab_and_derive() -> None:
    """The move kept one definition and the value."""
    assert derive.ItemKind is enums.ItemKind
    assert ItemKind.BAR.value == "bar"
    assert ITEM_ROLES[ItemKind.BAR].bar_holder


def test_pe_is_earth_and_not_power() -> None:
    """PE is protective, not a supply conductor (designer ruling 2026-10-16)."""
    assert NET_CLASS_ROLES[NetClass.PE].earth
    assert not NET_CLASS_ROLES[NetClass.PE].power
