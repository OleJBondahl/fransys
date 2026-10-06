"""CONTACT-STATES CS2 tests: `derive.changeover_throws`, the throws of a changeover contact.

A throw is a part fact (`PortTemplate.role` `COMMON`/`BREAK`/`MAKE`); no test here reads a pin
name, and the same structure under three naming schemes gives the same result shape.
"""

import dataclasses
from typing import TYPE_CHECKING

import pytest
from contact_builders import (
    _ITEM_KEY,
    _NUMBERED,
    _PART_KEY,
    _bundle,
    _function,
    _link,
    _model,
    _port,
)

from fransys_model.derive import Throws, changeover_throws, link_state
from fransys_model.kernel import Id, Origin, make_id
from fransys_model.vocab.enums import FunctionKind, LinkKind, PartCategory, PortRole
from fransys_model.vocab.instantiate import PartBundle
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

if TYPE_CHECKING:
    from fransys_model.vocab.core import Port


def _pole(
    number: int, names: tuple[str, str, str], item_key: tuple[str, ...] = _ITEM_KEY
) -> Throws:
    """The `Throws` the pole of function `co_<number>` with ports `names` must give."""
    common, brk, make = (_port(number, name, item_key) for name in names)
    return Throws(common=common, breaks=(brk,), makes=(make,))


@pytest.mark.parametrize("names", [_NUMBERED, ("COM", "NC", "NO"), ("I", "II", "III")])
def test_a_one_pole_changeover_gives_its_common_break_and_make(
    origin: Origin, names: tuple[str, str, str]
) -> None:
    """Roles, not pin names, decide: numbered, lettered and roman pins give the same shape."""
    model = _model(_bundle((names,)), origin)
    assert changeover_throws(model, _function(1)) == (_pole(1, names),)


def test_links_written_from_the_throw_to_the_common_give_the_same_result(origin: Origin) -> None:
    """A link is undirected: `a`=throw, `b`=common reads as `a`=common, `b`=throw."""
    model = _model(_bundle(reverse=True), origin)
    assert changeover_throws(model, _function(1)) == (_pole(1, _NUMBERED),)


def test_two_changeovers_of_one_part_each_get_their_own_throws(origin: Origin) -> None:
    """Poles 1 and 2 of one part never take each other's ports."""
    poles = (_NUMBERED, ("21", "22", "24"))
    model = _model(_bundle(poles), origin)
    assert changeover_throws(model, _function(1)) == (_pole(1, poles[0]),)
    assert changeover_throws(model, _function(2)) == (_pole(2, poles[1]),)


def test_two_items_of_one_part_each_get_their_own_throws(origin: Origin) -> None:
    """The same function template on two items resolves to each item's own ports."""
    other = ("cs2", "k2")
    model = _model(_bundle(), origin, _ITEM_KEY, other)
    assert changeover_throws(model, _function(1)) == (_pole(1, _NUMBERED),)
    assert changeover_throws(model, _function(1, other)) == (_pole(1, _NUMBERED, other),)


def test_a_changeover_of_only_generic_ports_gives_nothing(origin: Origin) -> None:
    """A Python-authored changeover with no roles has no throws, and does not raise."""
    generic = (PortRole.GENERIC, PortRole.GENERIC, PortRole.GENERIC)
    model = _model(_bundle(roles=generic), origin)
    assert changeover_throws(model, _function(1)) == ()


def test_a_function_that_is_not_a_changeover_gives_nothing(origin: Origin) -> None:
    """A `CONTACT_NO` function with the same roles and switched links has no throws."""
    model = _model(_bundle(kind=FunctionKind.CONTACT_NO), origin)
    assert changeover_throws(model, _function(1)) == ()


def test_a_function_that_is_not_in_the_model_gives_nothing(origin: Origin) -> None:
    """An id that names no function is the empty result, not an error."""
    model = _model(_bundle(), origin)
    assert changeover_throws(model, _function(1, ("cs2", "absent"))) == ()


def test_a_conductive_link_is_not_a_throw(origin: Origin) -> None:
    """Only `switched` links make a throw: the same roles joined `conductive` give nothing."""
    model = _model(_bundle(link_kind=LinkKind.CONDUCTIVE), origin)
    assert changeover_throws(model, _function(1)) == ()


@pytest.mark.parametrize(
    "roles",
    [
        (PortRole.COMMON, PortRole.COMMON, PortRole.COMMON),
        (PortRole.COMMON, PortRole.GENERIC, PortRole.GENERIC),
        (PortRole.BREAK, PortRole.MAKE, PortRole.GENERIC),
    ],
    ids=["common-to-common", "common-to-generic", "throw-to-throw"],
)
def test_a_link_that_does_not_join_a_common_to_a_throw_gives_no_throws(
    origin: Origin, roles: tuple[PortRole, PortRole, PortRole]
) -> None:
    """Two commons, a common and a `GENERIC` port, or two throws: no link joins a pole."""
    model = _model(_bundle(roles=roles), origin)
    assert changeover_throws(model, _function(1)) == ()


def test_a_common_with_only_a_break_has_no_makes(origin: Origin) -> None:
    """A pole with one throw kind keeps the other tuple empty: a link to `GENERIC` adds none."""
    roles = (PortRole.COMMON, PortRole.BREAK, PortRole.GENERIC)
    model = _model(_bundle(roles=roles), origin)
    assert changeover_throws(model, _function(1)) == (
        Throws(common=_port(1, "11"), breaks=(_port(1, "12"),), makes=()),
    )


def test_a_common_with_only_a_make_has_no_breaks(origin: Origin) -> None:
    """The symmetric case: a link to `GENERIC` adds no break either."""
    roles = (PortRole.COMMON, PortRole.MAKE, PortRole.GENERIC)
    model = _model(_bundle(roles=roles), origin)
    assert changeover_throws(model, _function(1)) == (
        Throws(common=_port(1, "11"), breaks=(), makes=(_port(1, "12"),)),
    )


def test_a_link_end_naming_no_port_template_gives_both_not_a_crash(origin: Origin) -> None:
    """`link_state`'s promise for "a link end that names no port template": `"both"`, no raise.

    `freeze` refuses a dangling reference outright, so the missing template is dropped from an
    already-frozen model instead, the way `test_plc_allocation_model`'s determinism test
    reorders tables after freezing.
    """
    model = _model(_bundle(), origin)
    missing = make_id(PortTemplate, (*_PART_KEY, "fn", "co_1", "port", "12"))
    kind = missing.kind
    trimmed = dataclasses.replace(
        model,
        tables=frozendict(
            {
                **model.tables,
                kind: frozendict({i: r for i, r in model.tables[kind].items() if i != missing}),
            }
        ),
    )
    assert link_state(trimmed, _function(1), _link(1, "12")) == "both"


def test_several_commons_breaks_and_makes_come_back_sorted_by_id(origin: Origin) -> None:
    """One function, three commons, each joined to five breaks and five makes: every tuple sorted.

    The templates, and the links, are built in descending port-id order, so the order the model
    was written in is never the sorted one.
    """
    commons, breaks, makes = (
        ("X", "Y", "Z"),
        tuple(f"B{n}" for n in range(5)),
        tuple(f"M{n}" for n in range(5)),
    )
    roles = (
        dict.fromkeys(commons, PortRole.COMMON)
        | dict.fromkeys(breaks, PortRole.BREAK)
        | dict.fromkeys(makes, PortRole.MAKE)
    )
    names = sorted(roles, key=lambda name: _port(1, name), reverse=True)
    part = Part(
        id=make_id(Part, _PART_KEY),
        key=_PART_KEY,
        mpn="CS2-RELAY-2",
        manufacturer="Example Co",
        description="Invented two-way changeover relay for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    function_key = (*_PART_KEY, "fn", "co_1")
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, function_key),
        key=function_key,
        part=part.id,
        name="co_1",
        kind=FunctionKind.CONTACT_CO,
    )
    templates = {
        name: PortTemplate(
            id=make_id(PortTemplate, (*function_key, "port", name)),
            key=(*function_key, "port", name),
            function=function.id,
            name=name,
            role=roles[name],
        )
        for name in names
    }
    links = tuple(
        InternalLink(
            id=make_id(InternalLink, (*function_key, "link", common, throw)),
            key=(*function_key, "link", common, throw),
            a=templates[common].id,
            b=templates[throw].id,
            kind=LinkKind.SWITCHED,
        )
        for common in names
        if roles[common] is PortRole.COMMON
        for throw in names
        if roles[throw] is not PortRole.COMMON
    )
    bundle = PartBundle(
        part=part,
        function_templates=(function,),
        port_templates=tuple(templates.values()),
        internal_links=links,
    )
    model = _model(bundle, origin)

    def ids(*kind_names: str) -> tuple[Id[Port], ...]:
        return tuple(sorted(_port(1, name) for name in kind_names))

    assert changeover_throws(model, _function(1)) == tuple(
        Throws(common=common, breaks=ids(*breaks), makes=ids(*makes)) for common in ids(*commons)
    )
