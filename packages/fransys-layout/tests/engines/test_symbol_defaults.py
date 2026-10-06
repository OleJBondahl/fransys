"""`default_symbol`: one table of symbol by function kind and rest state or protection type
(decision layout-0105). A switch's rest is read from `link_state`, never from the function kind.
"""

import pytest
from fransys_parts._rest import _SYMBOL_REST

from fransys_layout.engines.schematic.read.reading import drawn_functions
from fransys_layout.engines.schematic.symbol_defaults import default_symbol
from fransys_model.derive import link_state
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import (
    FunctionKind,
    LinkKind,
    LinkRest,
    PartCategory,
    PortRole,
    ProtectionType,
)
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

_ORIGIN = Origin(file="tests/engines/test_symbol_defaults.py", line=1, note="invented switch")
_PART = ("sd", "switch")
_ITEM = ("sd", "s1")
_FN = (*_PART, "fn", "sw")


def _switch(
    kind: FunctionKind, rest: LinkRest | None, protection: ProtectionType | None = None
) -> tuple[Model, Id[Function], Id[InternalLink]]:
    """A one-pole function of `kind`; its link is switched with `rest`, or conductive without."""
    part = Part(
        id=make_id(Part, _PART), key=_PART, mpn="SD-1", manufacturer="Example Co",
        description="Invented switch", category=PartCategory.ELECTROMECHANICAL, class_code="S",
    )  # fmt: skip
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, _FN), key=_FN, part=part.id, name="sw", kind=kind,
        protection_type=protection,
    )  # fmt: skip
    ports = [
        PortTemplate(
            id=make_id(PortTemplate, (*_FN, "port", n)),
            key=(*_FN, "port", n), function=function.id, name=n, role=PortRole.INTERNAL,
        )
        for n in ("A", "B")
    ]  # fmt: skip
    link = InternalLink(
        id=make_id(InternalLink, (*_FN, "link")), key=(*_FN, "link"),
        a=ports[0].id, b=ports[1].id, rest=rest,
        kind=LinkKind.CONDUCTIVE if rest is None else LinkKind.SWITCHED,
    )  # fmt: skip
    bundle = PartBundle(
        part=part, function_templates=(function,), port_templates=tuple(ports),
        internal_links=(link,),
    )  # fmt: skip
    draft = Draft()
    for record in (part, function, *ports, link, *instantiate(bundle, _ITEM)):
        draft.add(record, origin=_ORIGIN)
    return freeze(draft), make_id(Function, (*_ITEM, "fn", "sw")), link.id


@pytest.mark.parametrize("kind", [FunctionKind.SWITCH, FunctionKind.GENERIC])
@pytest.mark.parametrize(
    ("declared", "state", "symbol"),
    [
        (LinkRest.OPEN, "operated", "make-contact"),
        (LinkRest.CLOSED, "rest", "break-contact"),
    ],
    ids=["rest-open", "rest-closed"],
)
def test_the_rest_read_from_link_state_picks_make_or_break(
    kind: FunctionKind, declared: LinkRest, state: str, symbol: str
) -> None:
    """The kind is the same in both rows: only the declared rest, through `link_state`, differs."""
    model, function, link = _switch(kind, declared)
    rest = link_state(model, function, link)
    assert rest == state
    assert default_symbol(kind.value, rest, None) == symbol


@pytest.mark.parametrize("rest", ["rest", "operated"])
def test_the_symbols_agree_with_the_parts_lint_table(rest: str) -> None:
    """`_rest.py` maps symbol to open/closed at rest; `link_state` "rest" is closed at rest."""
    symbol = default_symbol("switch", rest, None)
    assert symbol is not None
    assert _SYMBOL_REST[symbol] == {"rest": "closed", "operated": "open"}[rest]


@pytest.mark.parametrize(
    ("protection_type", "symbol"),
    [
        (None, "circuit-breaker"),
        ("fuse", "fuse"),
        ("mcb", "circuit-breaker"),
        ("motor_breaker", "circuit-breaker"),
        ("overload", "thermal-overload"),
        ("rcd", "rcd"),
    ],
)
def test_a_protection_draws_by_its_type(protection_type: str | None, symbol: str) -> None:
    """No type keeps today's circuit-breaker; `rest` is ignored for a protection."""
    assert default_symbol("protection", "rest", protection_type) == symbol


@pytest.mark.parametrize(
    ("kind", "rest", "protection_type"),
    [
        ("switch", "both", None),
        ("switch", None, None),
        ("protection", None, "unknown"),
        ("coil", "rest", "fuse"),
        ("contact_no", "operated", None),
    ],
)
def test_no_row_gives_none(kind: str, rest: str | None, protection_type: str | None) -> None:
    """A rest of "both", an unknown type, another kind: the caller falls to ."""
    assert default_symbol(kind, rest, protection_type) is None


def test_a_switch_ignores_the_protection_type() -> None:
    """Each fact is read only for the kind that uses it."""
    assert default_symbol("switch", "rest", "fuse") == "break-contact"


@pytest.mark.parametrize(
    ("declared", "state"), [(LinkRest.OPEN, "operated"), (LinkRest.CLOSED, "rest")]
)
def test_the_spec_reads_rest_through_link_state_not_the_kind(
    declared: LinkRest, state: str
) -> None:
    """A `switch` kind says nothing of its rest: the spec holds what `link_state` answers."""
    model, function, link = _switch(FunctionKind.SWITCH, declared)
    (spec,) = drawn_functions(model, build_indexes(model))
    assert spec.function == function
    assert spec.rest == link_state(model, function, link) == state
    assert spec.protection_type is None


def test_the_spec_reads_a_protections_type_and_no_rest() -> None:
    """A protection's conductive link has no switched link, so no rest; its type is its value."""
    model, _, _ = _switch(FunctionKind.PROTECTION, None, ProtectionType.FUSE)
    (spec,) = drawn_functions(model, build_indexes(model))
    assert (spec.rest, spec.protection_type) == (None, "fuse")
