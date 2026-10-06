"""`layout.symbol_choice.template` precedence: function > template > part > kind.

Model decision 0030 adds the `template` selector; `reading.symbol_choices` resolves it
into function-level stage entries (`stages/types.py` is frozen, design/stages.md 6.1). These tests
build a tiny two-relay model directly, without `layout_cabinet`'s bigger cabinet fixture,
because only symbol resolution is under test here, not connectivity or placement.
"""

from typing import Any

import pytest

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import reading
from fransys_layout.geometry import HintError
from fransys_layout.stages import resolve
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Draft, Id, Origin, freeze, make_id
from fransys_model.layout import SymbolChoice
from fransys_model.vocab import (
    FunctionKind,
    FunctionTemplate,
    InternalLink,
    LinkKind,
    Part,
    PartBundle,
    PartCategory,
    PortRole,
    PortTemplate,
    instantiate,
)

_ORIGIN = Origin(file="tests/engines/test_symbol_choice_template.py", line=1, note="fixture")


def _relay_bundle() -> PartBundle:
    """A relay part: `coil` (A1/A2) and `no_1` (13/14, switched)."""
    part = Part(
        id=make_id(Part, ("relay",)),
        key=("relay",),
        mpn="EX-RELAY-1NO",
        manufacturer="Example Co",
        description="Invented relay",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
        library=None,
    )
    coil = FunctionTemplate(
        id=make_id(FunctionTemplate, ("relay", "coil")),
        key=("relay", "coil"),
        part=part.id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    contact = FunctionTemplate(
        id=make_id(FunctionTemplate, ("relay", "no_1")),
        key=("relay", "no_1"),
        part=part.id,
        name="no_1",
        kind=FunctionKind.CONTACT_NO,
    )
    ports = (
        PortTemplate(
            id=make_id(PortTemplate, ("relay", "coil", "A1")),
            key=("relay", "coil", "A1"),
            function=coil.id,
            name="A1",
            role=PortRole.GENERIC,
        ),
        PortTemplate(
            id=make_id(PortTemplate, ("relay", "coil", "A2")),
            key=("relay", "coil", "A2"),
            function=coil.id,
            name="A2",
            role=PortRole.GENERIC,
        ),
        PortTemplate(
            id=make_id(PortTemplate, ("relay", "no_1", "13")),
            key=("relay", "no_1", "13"),
            function=contact.id,
            name="13",
            role=PortRole.GENERIC,
        ),
        PortTemplate(
            id=make_id(PortTemplate, ("relay", "no_1", "14")),
            key=("relay", "no_1", "14"),
            function=contact.id,
            name="14",
            role=PortRole.GENERIC,
        ),
    )
    link = InternalLink(
        id=make_id(InternalLink, ("relay", "no_1", "link")),
        key=("relay", "no_1", "link"),
        a=make_id(PortTemplate, ("relay", "no_1", "13")),
        b=make_id(PortTemplate, ("relay", "no_1", "14")),
        kind=LinkKind.SWITCHED,
    )
    return PartBundle(
        part=part, function_templates=(coil, contact), port_templates=ports, internal_links=(link,)
    )


def _model(*extra):
    """Two relays (`k1`, `k2`) stamped from one bundle, plus any authored `extra` records."""
    bundle = _relay_bundle()
    draft = Draft()
    draft.extend(
        (bundle.part, *bundle.function_templates, *bundle.port_templates, *bundle.internal_links),
        origin=_ORIGIN,
    )
    for key in (("k1",), ("k2",)):
        draft.extend(instantiate(bundle, key, tag=key[0].upper()), origin=_ORIGIN)
    draft.extend(extra, origin=_ORIGIN)
    return freeze(draft), bundle


def _coil_functions(model) -> dict[str, Id[Any]]:
    """`{"k1": <coil function id>, "k2": <coil function id>}`."""
    return {f.key[0]: f.id for f in model.tables["function"].values() if f.key[-1] == "coil"}


_COIL_TEMPLATE = make_id(FunctionTemplate, ("relay", "coil"))


def _template_choice(*, symbol: str, key: str = "coil-choice") -> SymbolChoice:
    return SymbolChoice(
        id=make_id(SymbolChoice, ("choice", key)),
        key=("choice", key),
        function=None,
        template=_COIL_TEMPLATE,
        part=None,
        kind=None,
        symbol=symbol,
        port_map=frozendict({"A1": "in", "A2": "out"}),
    )


def test_a_template_choice_applies_to_every_instance_of_that_template() -> None:
    """Both relays' `coil` functions resolve to the template choice's symbol."""
    model, _bundle = _model(_template_choice(symbol="operating-device"))
    entries = reading.symbol_choices(model)
    coils = _coil_functions(model)
    resolved = {e.function: e.symbol for e in entries}
    assert resolved[coils["k1"]] == "operating-device"
    assert resolved[coils["k2"]] == "operating-device"


def test_an_explicit_function_choice_beats_the_template_choice() -> None:
    """`k1`'s coil has its own choice; only `k2`'s coil is synthesised from the template."""
    bare, _bundle = _model()
    coils = _coil_functions(bare)
    model, _bundle = _model(
        _template_choice(symbol="operating-device"),
        SymbolChoice(
            id=make_id(SymbolChoice, ("choice", "k1-coil")),
            key=("choice", "k1-coil"),
            function=coils["k1"],
            template=None,
            part=None,
            kind=None,
            symbol="special-operating-device",
        ),
    )
    entries = reading.symbol_choices(model)
    coils = _coil_functions(model)
    resolved = {e.function: e.symbol for e in entries}
    assert resolved[coils["k1"]] == "special-operating-device"
    assert resolved[coils["k2"]] == "operating-device"


def test_a_template_choice_beats_the_default_kind_rule() -> None:
    """`resolve` draws the coil with the template's symbol, not `DEFAULT_RULES`'s."""
    model, _bundle = _model(_template_choice(symbol="operating-device"))
    indexes = build_indexes(model)
    functions = reading.drawn_functions(model, indexes)
    choices = reading.symbol_choices(model)
    drawn, findings = resolve(functions, rules=DEFAULT_RULES, choices=choices)
    coils = _coil_functions(model)
    by_function = {d.function: d for d in drawn}
    assert by_function[coils["k1"]].geometry.key == "operating-device"
    assert findings == ()


def test_two_template_choices_for_one_template_raise() -> None:
    """Two `layout.symbol_choice` records naming the same template are ambiguous."""
    model, _bundle = _model(
        _template_choice(symbol="operating-device", key="a"),
        _template_choice(symbol="other-device", key="b"),
    )
    indexes = build_indexes(model)
    functions = reading.drawn_functions(model, indexes)
    choices = reading.symbol_choices(model)
    with pytest.raises(HintError):
        resolve(functions, rules=DEFAULT_RULES, choices=choices)


def test_symbol_choices_result_is_independent_of_authoring_order() -> None:
    """The same records, added in reverse, resolve to the same stage tuple."""
    bundle = _relay_bundle()
    choice = _template_choice(symbol="operating-device")
    forward, _bundle = _model(choice)
    draft = Draft()
    draft.extend(
        (bundle.part, *bundle.function_templates, *bundle.port_templates, *bundle.internal_links),
        origin=_ORIGIN,
    )
    for key in (("k2",), ("k1",)):
        draft.extend(instantiate(bundle, key, tag=key[0].upper()), origin=_ORIGIN)
    draft.extend((choice,), origin=_ORIGIN)
    backward = freeze(draft)
    assert reading.symbol_choices(forward) == reading.symbol_choices(backward)
