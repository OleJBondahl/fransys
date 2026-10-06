"""CONTACT-STATES CS2 tests: `derive.link_state`, the state in which an internal link is closed.

`contact_no` closes operated, `contact_nc` at rest; a changeover's link closes at rest to the
`BREAK` port and operated to the `MAKE` port, by role and never by pin name.
"""

import pytest
from contact_builders import _NUMBERED, _PART_KEY, _bundle, _function, _link, _model

from fransys_model.derive import link_state
from fransys_model.kernel import Origin, make_id
from fransys_model.vocab.enums import FunctionKind, LinkKind, LinkRest, PortRole
from fransys_model.vocab.templates import InternalLink


@pytest.mark.parametrize(
    ("kind", "state"),
    [(FunctionKind.CONTACT_NO, "operated"), (FunctionKind.CONTACT_NC, "rest")],
    ids=["no", "nc"],
)
def test_a_make_contact_closes_operated_and_a_break_contact_at_rest(
    origin: Origin, kind: FunctionKind, state: str
) -> None:
    """The function kind decides, whatever the roles of the ports the link joins."""
    model = _model(_bundle(kind=kind), origin)
    assert link_state(model, _function(1), _link(1, "12")) == state
    assert link_state(model, _function(1), _link(1, "14")) == state


@pytest.mark.parametrize("names", [_NUMBERED, ("COM", "NC", "NO"), ("I", "II", "III")])
@pytest.mark.parametrize("reverse", [False, True], ids=["common-first", "throw-first"])
def test_a_changeover_link_to_the_break_is_rest_and_to_the_make_is_operated(
    origin: Origin, names: tuple[str, str, str], *, reverse: bool
) -> None:
    """Roles, not pin names or the order of a link's ends, decide."""
    model = _model(_bundle((names,), reverse=reverse), origin)
    assert link_state(model, _function(1), _link(1, names[1])) == "rest"
    assert link_state(model, _function(1), _link(1, names[2])) == "operated"


def test_a_changeover_of_only_generic_ports_is_closed_in_both_states(origin: Origin) -> None:
    """No roles, no throw: both links are `both`."""
    generic = (PortRole.GENERIC, PortRole.GENERIC, PortRole.GENERIC)
    model = _model(_bundle(roles=generic), origin)
    assert link_state(model, _function(1), _link(1, "12")) == "both"
    assert link_state(model, _function(1), _link(1, "14")) == "both"


def test_a_changeover_link_that_joins_a_common_to_a_common_is_both(origin: Origin) -> None:
    """Only a common to a throw is a pole."""
    commons = (PortRole.COMMON, PortRole.COMMON, PortRole.COMMON)
    model = _model(_bundle(roles=commons), origin)
    assert link_state(model, _function(1), _link(1, "12")) == "both"


def test_a_conductive_link_is_both_whatever_the_function_kind(origin: Origin) -> None:
    """A conductive link is always closed, so it carries no condition."""
    for kind in (FunctionKind.CONTACT_NO, FunctionKind.CONTACT_NC, FunctionKind.CONTACT_CO):
        model = _model(_bundle(kind=kind, link_kind=LinkKind.CONDUCTIVE), origin)
        assert link_state(model, _function(1), _link(1, "12")) == "both"


def test_a_switched_link_on_another_function_kind_is_both(origin: Origin) -> None:
    """A `protection` function's switched link is not a contact's."""
    model = _model(_bundle(kind=FunctionKind.PROTECTION), origin)
    assert link_state(model, _function(1), _link(1, "12")) == "both"


def test_an_unknown_function_or_link_is_both(origin: Origin) -> None:
    """An id that names nothing gives `both`, not an error."""
    model = _model(_bundle(), origin)
    absent_link = make_id(InternalLink, (*_PART_KEY, "absent"))
    assert link_state(model, _function(1, ("cs2", "absent")), _link(1, "12")) == "both"
    assert link_state(model, _function(1), absent_link) == "both"


@pytest.mark.parametrize("kind", [FunctionKind.SWITCH, FunctionKind.GENERIC])
@pytest.mark.parametrize(
    ("rest", "state"), [(LinkRest.CLOSED, "rest"), (LinkRest.OPEN, "operated")], ids=["nc", "no"]
)
def test_a_declared_rest_decides_a_switch_and_a_generic_function(
    origin: Origin, kind: FunctionKind, rest: LinkRest, state: str
) -> None:
    """A rest-closed push button is closed at rest; a rest-open one closes when operated."""
    generic = (PortRole.GENERIC, PortRole.GENERIC, PortRole.GENERIC)
    model = _model(_bundle(kind=kind, roles=generic, rest=rest), origin)
    assert link_state(model, _function(1), _link(1, "12")) == state


def test_a_switch_link_with_no_rest_is_both_and_a_no_contact_with_none_is_operated(
    origin: Origin,
) -> None:
    """Only an undeclared switch link falls back to `both`; a contact kind still implies it."""
    switch = _model(_bundle(kind=FunctionKind.SWITCH), origin)
    assert link_state(switch, _function(1), _link(1, "12")) == "both"
    contact = _model(_bundle(kind=FunctionKind.CONTACT_NO), origin)
    assert link_state(contact, _function(1), _link(1, "12")) == "operated"
