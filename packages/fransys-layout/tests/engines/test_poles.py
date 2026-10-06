"""`FunctionSpec.poles` and `pole_pairs` of shapes the shared cabinet lacks (layout-0026)."""

from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages import PolePair
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Function,
    FunctionKind,
    FunctionTemplate,
    InternalLink,
    Item,
    LinkKind,
    Part,
    PartBundle,
    PartCategory,
    PartLibrary,
    Port,
    PortRole,
    PortTemplate,
    instantiate,
)

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec

_ORIGIN = Origin(file="tests/engines/test_poles.py", line=1, note="pole tests")

type Link = tuple[str, str, str, str]


def _specs(
    functions: dict[str, tuple[str, ...]],
    links: tuple[Link, ...],
    *,
    kind: FunctionKind = FunctionKind.GENERIC,
    link_kinds: tuple[LinkKind, ...] = (),
) -> dict[str, FunctionSpec]:
    """One device `K1` of one part: functions by name with their pins, and switched links.

    A link is `(function a, pin a, function b, pin b)`. Returns the specs by function name.
    D5: a device of two or more functions that all default to a generic symbol is read as one
    box, with no spec per function. A `kind` that has a default symbol keeps the functions apart.
    """
    library = PartLibrary(
        id=make_id(PartLibrary, ("part_library", "invented")),
        key=("part_library", "invented"),
        name="invented",
        version="1.0.0",
    )
    part = Part(
        id=make_id(Part, ("device",)),
        key=("device",),
        mpn="EX-DEVICE",
        manufacturer="Example Co",
        description="Invented device",
        category=PartCategory.GENERIC,
        class_code="K",
        library=library.id,
    )
    templates = {
        name: FunctionTemplate(
            id=make_id(FunctionTemplate, ("device", name)),
            key=("device", name),
            part=part.id,
            name=name,
            kind=kind,
        )
        for name in functions
    }
    pins = {
        (name, pin): PortTemplate(
            id=make_id(PortTemplate, ("device", name, pin)),
            key=("device", name, pin),
            function=templates[name].id,
            name=pin,
            role=PortRole.GENERIC,
        )
        for name, names in functions.items()
        for pin in names
    }
    internal_links = tuple(
        InternalLink(
            id=make_id(InternalLink, ("device", "link", str(number))),
            key=("device", "link", str(number)),
            a=pins[fa, pa].id,
            b=pins[fb, pb].id,
            kind=link_kinds[number - 1] if number <= len(link_kinds) else LinkKind.SWITCHED,
        )
        for number, (fa, pa, fb, pb) in enumerate(links, start=1)
    )
    bundle = PartBundle(
        part=part,
        function_templates=tuple(templates.values()),
        port_templates=tuple(pins.values()),
        internal_links=internal_links,
    )
    stamped = instantiate(
        bundle,
        ("k1",),
        tag="K1",
        parent=None,
        description=part.description,
        installed=True,
    )
    draft = Draft()
    draft.extend(
        (library, part, *templates.values(), *pins.values(), *internal_links, *stamped),
        origin=_ORIGIN,
    )
    return {spec.key[-1]: spec for spec in read_inputs(freeze(draft)).functions}


def test_a_change_over_is_one_pole_and_has_no_pole_pair() -> None:
    """Links `11-14` and `12-14` share `14`: one component of three ports, so one pole."""
    spec = _specs({"co": ("11", "12", "14")}, (("co", "11", "co", "14"), ("co", "12", "co", "14")))[
        "co"
    ]
    assert spec.poles == 1
    assert spec.pole_pairs == ()


def test_a_function_with_no_internal_link_has_one_pole_and_no_pair() -> None:
    """No link joins its ports: one pole, nothing to pair."""
    spec = _specs({"coil": ("A1", "A2")}, ())["coil"]
    assert spec.poles == 1
    assert spec.pole_pairs == ()


def test_a_three_port_component_takes_a_pole_index_but_gives_no_pair() -> None:
    """A change-over `1,2,3` beside a plain pair `4-5`: two poles, and the pair is index 1."""
    spec = _specs(
        {"mix": ("1", "2", "3", "4", "5")},
        (("mix", "1", "mix", "3"), ("mix", "2", "mix", "3"), ("mix", "4", "mix", "5")),
    )["mix"]
    assert spec.poles == 2
    assert spec.pole_pairs == (PolePair(index=1, first="4", second="5"),)


def test_a_function_whose_template_has_no_port_template_has_one_pole_and_no_pair() -> None:
    """A template with no pins gives a function with no links to read: one pole."""
    spec = _specs({"bare": ()}, ())["bare"]
    assert spec.poles == 1
    assert spec.pole_pairs == ()


def test_a_function_with_no_template_has_one_pole_and_no_pair() -> None:
    """A half-finished design: an item with no part and a function stamped from no template."""
    item = Item(
        id=make_id(Item, ("loose",)),
        key=("loose",),
        part=None,
        parent=None,
        position=None,
        tag="X9",
        description="Invented loose item",
    )
    function = Function(
        id=make_id(Function, ("loose", "fn", "f")),
        key=("loose", "fn", "f"),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port = Port(
        id=make_id(Port, ("loose", "fn", "f", "port", "1")),
        key=("loose", "fn", "f", "port", "1"),
        function=function.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    draft = Draft()
    draft.extend((item, function, port), origin=_ORIGIN)
    (spec,) = read_inputs(freeze(draft)).functions
    assert spec.function == function.id
    assert spec.poles == 1
    assert spec.pole_pairs == ()


def test_a_link_between_two_function_templates_adds_no_pole_to_either() -> None:
    """Only a link between two port templates of one function template counts.

    Both functions are switches (a contact with no conductor is not drawn), so each keeps its
    own spec (D5's box takes only functions that all default to a generic symbol).
    """
    specs = _specs(
        {"main": ("1", "2"), "aux": ("13", "14")},
        (("main", "1", "aux", "13"), ("main", "1", "main", "2")),
        kind=FunctionKind.SWITCH,
    )
    assert specs["main"].poles == 1
    assert specs["main"].pole_pairs == (PolePair(index=0, first="1", second="2"),)
    assert specs["aux"].poles == 1
    assert specs["aux"].pole_pairs == ()


def test_poles_follow_marking_order_by_value_not_text() -> None:
    """Declared `13-14` first and `10-9` second: pole 0 is 9/10, pole 1 is 13/14 (layout-0106)."""
    spec = _specs({"p": ("13", "14", "10", "9")}, (("p", "13", "p", "14"), ("p", "10", "p", "9")))[
        "p"
    ]
    assert spec.pole_pairs == (
        PolePair(index=0, first="9", second="10"),
        PolePair(index=1, first="13", second="14"),
    )


def test_a_protective_link_is_a_pole_and_a_conductive_link_beside_poles_is_not() -> None:
    """Switched `1-2` and protective `3-4` are poles; a generic one's conductive `5-6` is not."""
    spec = _specs(
        {"g": ("1", "2", "3", "4", "5", "6")},
        (("g", "1", "g", "2"), ("g", "3", "g", "4"), ("g", "5", "g", "6")),
        link_kinds=(LinkKind.SWITCHED, LinkKind.PROTECTIVE, LinkKind.CONDUCTIVE),
    )["g"]
    assert spec.poles == 2
    assert spec.pole_pairs == (
        PolePair(index=0, first="1", second="2"),
        PolePair(index=1, first="3", second="4"),
    )
