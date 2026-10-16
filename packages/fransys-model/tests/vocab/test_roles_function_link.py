"""Tests: the function and link role tables are complete, frozen and reproduce today's branches."""

import dataclasses
from enum import Enum

import pytest
from plant import Plant

from fransys_model.derive.facts.energy_flow import gives_energy, takes_energy
from fransys_model.vocab.enums import Energy, FunctionKind, LinkKind, LinkRest
from fransys_model.vocab.roles import LINK_ROLES, function_role_of
from fransys_model.vocab.roles_types import FunctionRole, LinkRole, complete

_ROWS = {kind: function_role_of(kind) for kind in FunctionKind}
_CONTACTS = (FunctionKind.CONTACT_NO, FunctionKind.CONTACT_NC, FunctionKind.CONTACT_CO)


def test_every_function_kind_has_a_row() -> None:
    """Each member of `FunctionKind` is a key of the table."""
    assert all(isinstance(function_role_of(kind), FunctionRole) for kind in FunctionKind)


def test_every_link_kind_has_a_row() -> None:
    """Each member of `LinkKind` is a key of the table."""
    assert set(LINK_ROLES) == set(LinkKind)


def test_rows_are_frozen_and_slotted() -> None:
    """A row refuses an assignment and has no `__dict__`."""
    for row in (*_ROWS.values(), *LINK_ROLES.values()):
        assert not hasattr(row, "__dict__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            row.__setattr__("pole", True)


def test_contact_kinds_are_contacts_and_only_the_changeover_changes_over() -> None:
    """NO, NC, CO and SWITCH are contacts; `plain_contact` leaves `SWITCH` out."""
    for kind in _CONTACTS:
        assert function_role_of(kind).contact
        assert function_role_of(kind).plain_contact
    assert function_role_of(FunctionKind.SWITCH).contact
    assert not function_role_of(FunctionKind.SWITCH).plain_contact
    changing = {kind for kind, row in _ROWS.items() if row.changeover}
    assert changing == {FunctionKind.CONTACT_CO}


def test_a_contact_kind_implies_its_rest_state() -> None:
    """A normally open contact rests open, a normally closed one closed, the rest imply none."""
    assert function_role_of(FunctionKind.CONTACT_NO).rest is LinkRest.OPEN
    assert function_role_of(FunctionKind.CONTACT_NC).rest is LinkRest.CLOSED
    others = {k for k, row in _ROWS.items() if row.rest is not None}
    assert others == {FunctionKind.CONTACT_NO, FunctionKind.CONTACT_NC}


def test_one_role_flag_per_structural_kind() -> None:
    """Terminal, connector, channel, bar and protection each set exactly their own flag."""
    flags = {
        FunctionKind.TERMINAL: "terminal",
        FunctionKind.CONNECTOR: "pin_group",
        FunctionKind.PLC_CHANNEL: "channel",
        FunctionKind.BAR: "bar",
        FunctionKind.PROTECTION: "protects",
        FunctionKind.COIL: "operator",
    }
    for kind, flag in flags.items():
        for name in ("terminal", "pin_group", "channel", "bar", "protects", "operator"):
            assert getattr(function_role_of(kind), name) is (name == flag)


def test_energy_matches_the_energy_flow_oracle_for_every_kind() -> None:
    """`takes_energy` and `gives_energy` of a templateless function match `energy`."""
    plant = Plant()
    item = plant.item("device")
    made = {kind: plant.function(item, kind.value, kind=kind) for kind in FunctionKind}
    model = plant.model()
    for kind, row in _ROWS.items():
        assert takes_energy(model, made[kind]) is (row.energy is Energy.IN)
        assert gives_energy(model, made[kind]) is (row.energy is Energy.OUT)


def test_the_switched_link_does_not_join_the_net() -> None:
    """A switched link is a pole, switched, and outside the physical net; a protective one too."""
    assert LINK_ROLES[LinkKind.SWITCHED] == LinkRole(pole=True, switched=True, passes_rail=True)
    assert all(row.passes_rail for row in LINK_ROLES.values())
    assert LINK_ROLES[LinkKind.CONDUCTIVE].joins_net
    assert not LINK_ROLES[LinkKind.PROTECTIVE].joins_net
    assert LINK_ROLES[LinkKind.PROTECTIVE].protective


def test_a_kind_added_without_a_row_fails_at_import() -> None:
    """`complete` raises, naming the enum and the member, when a table lacks a member."""
    wider = Enum("wider", [(k.name, k.value) for k in FunctionKind] + [("NEW", "new")])
    with pytest.raises(RuntimeError, match="wider has no role row for: NEW"):
        complete({member: FunctionRole() for member in wider if member.name != "NEW"}, wider)


def test_function_role_of_returns_the_row_of_the_kind() -> None:
    """The kind-taking fact gives each kind its own row, not a neighbour's."""
    assert function_role_of(FunctionKind.PROTECTION).protects
    assert function_role_of(FunctionKind.CONTACT_NO).rest is LinkRest.OPEN
    assert function_role_of(FunctionKind.TERMINAL).terminal
    assert not function_role_of(FunctionKind.GENERIC).protects
