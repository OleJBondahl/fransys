"""Decision model-0080: a connector whose facet states no gender is drawn with `contact`.

Hand-built model: a cabinet connector `X9` on a function template with a `connector` facet,
wired to a second connector `X8` with no template. Read through `read_inputs` and resolved with
the shipped rules, the pin view of `X9` is drawn with the symbol the (connector, None, gender)
rule names.
"""

import pytest

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages import resolve
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    Function,
    FunctionKind,
    FunctionTemplate,
    Gender,
    Item,
    Part,
    PartCategory,
    Port,
    PortRole,
)
from fransys_model.vocab.facets import ConnectorFacet

_ORIGIN = Origin(file="tests/engines/test_connector_gender.py", line=1, note="model-0080 tests")


def _connector_symbol(gender: Gender | None) -> str:
    """The symbol key the pin view of connector `X9` (facet gender `gender`) is drawn with."""
    part = Part(
        id=make_id(Part, ("cp",)),
        key=("cp",),
        mpn="MPN-CP",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CONNECTOR,
        class_code="X",
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("cp", "tpl")),
        key=("cp", "tpl"),
        part=part.id,
        name="conn",
        kind=FunctionKind.CONNECTOR,
    )
    facet = ConnectorFacet(
        id=make_id(ConnectorFacet, ("cp", "tpl", "connector")),
        key=("cp", "tpl", "connector"),
        subject=template.id,
        style="header",
        pincount=1,
        gender=gender,
    )
    x9 = Item(
        id=make_id(Item, ("x9",)),
        key=("x9",),
        part=None,
        parent=None,
        position=None,
        tag="X9",
        description="",
        installed=True,
    )
    x8 = Item(
        id=make_id(Item, ("x8",)),
        key=("x8",),
        part=None,
        parent=None,
        position=None,
        tag="X8",
        description="",
        installed=True,
    )
    x9_fn = Function(
        id=make_id(Function, ("x9", "fn", "conn")),
        key=("x9", "fn", "conn"),
        item=x9.id,
        template=template.id,
        name="conn",
        kind=FunctionKind.CONNECTOR,
    )
    x8_fn = Function(
        id=make_id(Function, ("x8", "fn", "conn")),
        key=("x8", "fn", "conn"),
        item=x8.id,
        template=None,
        name="conn",
        kind=FunctionKind.CONNECTOR,
    )
    x9_p1 = Port(
        id=make_id(Port, (*x9_fn.key, "1")),
        key=(*x9_fn.key, "1"),
        function=x9_fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    x8_p1 = Port(
        id=make_id(Port, (*x8_fn.key, "1")),
        key=(*x8_fn.key, "1"),
        function=x8_fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    conductor = Conductor(
        id=make_id(Conductor, ("w",)),
        key=("w",),
        a=x9_p1.id,
        b=x8_p1.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    draft = Draft()
    draft.extend(
        (part, template, facet, x9, x8, x9_fn, x8_fn, x9_p1, x8_p1, conductor), origin=_ORIGIN
    )
    inputs = read_inputs(freeze(draft))
    drawn, _findings = resolve(inputs.functions, rules=DEFAULT_RULES, choices=inputs.choices)
    (view,) = (one for one in drawn if one.function == x9_p1.id)
    return view.geometry.key


@pytest.mark.parametrize(
    ("gender", "symbol"),
    [
        (None, "contact"),
        (Gender.FEMALE, "contact-female"),
        (Gender.MALE, "contact-male"),
        (Gender.NEUTRAL, "contact"),
    ],
    ids=["unstated", "female", "male", "neutral"],
)
def test_a_connector_pin_view_is_drawn_by_its_facets_gender_and_an_unstated_one_is_contact(
    gender: Gender | None, symbol: str
) -> None:
    assert _connector_symbol(gender) == symbol
