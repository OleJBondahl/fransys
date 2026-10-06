"""Decision model-0070: the closed set of wire colours and `WIRE_COLOUR_UNKNOWN`."""

from decimal import Decimal

import pytest
from scaffold import scaffold

from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze
from fransys_model.vocab import (
    ALL_VALIDATORS,
    BASE_COLOURS,
    COLOUR_GRAMMAR,
    RESERVED_COLOURS,
    split_colour,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import ConductorKind, PartCategory
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.colours import WIRE_COLOUR_UNKNOWN, check_colours

_VALID = ("BK", "BU", "GD", "SR", "TQ", "GNYE", "WHOG", "BK1", "BU12", "SH", "")
_INVALID = (
    "SHBK",  # a shield is not half of a two-colour core
    "BKSH",  # in either order
    "SH1",  # a shield has no core number
    "sh",  # lower case is not a code
    "brown",  # a name, not a code
    "bk",  # lower case is not a code
    "XX",  # not a base code
    "GNGN",  # a joined pair repeats its half
    "GNYEBK",  # three colours
    "BK0",  # a core number starts at 1
    "BK01",  # no leading zero
    "GNYE1",  # a number follows a base code, not a pair
    "BK1A",  # digits only
    "1",  # a number alone
    "BK ",  # no blanks
)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_colours.py", line=1, note="fixture")
    draft.extend((*records, *scaffold(records)), origin=origin)
    return freeze(draft)


def _wire(colour: str) -> tuple[Conductor, WireFacet]:
    conductor = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("examples", "w1"),
        a=Id(kind="port", value="1a".zfill(32)),
        b=Id(kind="port", value="1b".zfill(32)),
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    facet = WireFacet(
        id=Id(kind="facet.wire", value="1c".zfill(32)),
        key=("examples", "w1", "wire"),
        subject=conductor.id,
        colour=colour,
        gauge_mm2=Decimal("0.75"),
        length_mm=None,
        label=None,
    )
    return conductor, facet


def _product(*colours: str) -> tuple[Part, CableProductFacet]:
    """A cable part `examples/cab` and its product facet, one core per colour."""
    part = Part(
        id=Id(kind="part", value="3" * 32),
        key=("examples", "cab"),
        mpn="EXAMPLE-CAB",
        manufacturer="Example Co",
        description="Invented cable",
        category=PartCategory.CABLE,
        class_code="W",
    )
    facet = CableProductFacet(
        id=Id(kind="facet.cable_product", value="3c".zfill(32)),
        key=("examples", "cab", "product"),
        subject=part.id,
        core_colours=colours,
        gauge_mm2=Decimal("0.75"),
        shielded=False,
    )
    return part, facet


def _cable_with_cores(part: Part, count: int) -> tuple[Record, ...]:
    """A cable item of `part` and `count` cores, each with its `core` facet."""
    cable = Item(
        id=Id(kind="item", value="4" * 32),
        key=("examples", "w4"),
        part=part.id,
        parent=None,
        position=None,
        tag="W4",
        description="Invented",
        installed=True,
    )
    records: list[Record] = [cable]
    for index in range(1, count + 1):
        core = Conductor(
            id=Id(kind="conductor", value=f"4{index}".zfill(32)),
            key=("examples", "w4", f"core-{index}"),
            a=Id(kind="port", value=f"4a{index}".zfill(32)),
            b=Id(kind="port", value=f"4b{index}".zfill(32)),
            kind=ConductorKind.CORE,
            carrier=cable.id,
        )
        facet = CoreFacet(
            id=Id(kind="facet.core", value=f"4c{index}".zfill(32)),
            key=("examples", "w4", f"core-{index}", "core"),
            subject=core.id,
            index=index,
        )
        records.extend((core, facet))
    return tuple(records)


def test_the_base_codes_are_the_fourteen_of_the_standard() -> None:
    assert dict(BASE_COLOURS) == {
        "BK": "black",
        "BN": "brown",
        "RD": "red",
        "OG": "orange",
        "YE": "yellow",
        "GN": "green",
        "BU": "blue",
        "VT": "violet",
        "GY": "grey",
        "WH": "white",
        "PK": "pink",
        "GD": "gold",
        "SR": "silver",
        "TQ": "turquoise",
    }


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("BU", ("BU", "")),
        ("GNYE", ("GNYE", "")),
        ("WHOG", ("WHOG", "")),
        ("BK1", ("BK", "1")),
        ("BU12", ("BU", "12")),
        ("SH", ("SH", "")),
        ("", ("", "")),
    ],
)
def test_split_colour_gives_the_base_codes_and_the_core_number(
    code: str, expected: tuple[str, str]
) -> None:
    assert split_colour(code) == expected


@pytest.mark.parametrize("code", _INVALID)
def test_split_colour_refuses_what_the_grammar_does_not_allow(code: str) -> None:
    assert split_colour(code) is None


def test_the_shield_code_is_reserved_beside_the_fourteen_not_one_of_them() -> None:
    assert dict(RESERVED_COLOURS) == {"SH": "shield"}
    assert "SH" not in BASE_COLOURS


def test_the_grammar_text_names_every_base_code_and_the_two_forms() -> None:
    for code, name in BASE_COLOURS.items():
        assert f"{code} {name}" in COLOUR_GRAMMAR
    for code, name in RESERVED_COLOURS.items():
        assert f"{code} {name}" in COLOUR_GRAMMAR
    assert "GNYE" in COLOUR_GRAMMAR
    assert "BK1" in COLOUR_GRAMMAR


def test_the_validator_is_registered() -> None:
    assert check_colours in ALL_VALIDATORS


def test_an_unknown_colour_is_found_by_the_registered_validators() -> None:
    conductor, facet = _wire("brown")
    model = _freeze((conductor, facet))
    findings = [f for check in ALL_VALIDATORS for f in check(model)]
    assert WIRE_COLOUR_UNKNOWN in {f.code for f in findings}


@pytest.mark.parametrize("colour", _INVALID)
def test_an_unknown_colour_on_a_wire_fires(colour: str) -> None:
    conductor, facet = _wire(colour)
    (finding,) = check_colours(_freeze((conductor, facet)))
    assert finding.code == WIRE_COLOUR_UNKNOWN
    assert finding.severity.name == "ERROR"
    assert finding.subjects == tuple(sorted((conductor.id, facet.id)))
    assert repr(colour) in finding.message
    assert COLOUR_GRAMMAR in finding.message
    assert "w1" in finding.message


@pytest.mark.parametrize("colour", _INVALID)
def test_one_unknown_core_colour_of_a_cable_product_fires_once(colour: str) -> None:
    part, facet = _product("BN", colour, "BU")
    (finding,) = check_colours(_freeze((part, facet)))
    assert finding.code == WIRE_COLOUR_UNKNOWN
    assert finding.severity.name == "ERROR"
    assert finding.subjects == tuple(sorted((part.id, facet.id)))
    assert repr(colour) in finding.message
    assert COLOUR_GRAMMAR in finding.message
    assert "cab" in finding.message
    assert "core colour 2 " in finding.message


def test_two_unknown_core_colours_of_a_cable_product_fire_twice() -> None:
    part, facet = _product("brown", "BU", "xx")
    findings = check_colours(_freeze((part, facet)))
    assert [f.code for f in findings] == [WIRE_COLOUR_UNKNOWN] * 2
    assert sorted("'brown'" in f.message for f in findings) == [False, True]
    assert sorted("'xx'" in f.message for f in findings) == [False, True]


def test_a_cable_product_with_only_allowed_core_colours_is_silent() -> None:
    part, facet = _product(*_VALID)
    assert check_colours(_freeze((part, facet))) == ()


def test_a_bad_core_colour_is_reported_once_however_many_cores_the_cable_has() -> None:
    part, facet = _product("BN", "brown", "BU")
    cable = _cable_with_cores(part, 3)
    (finding,) = check_colours(_freeze((part, facet, *cable)))
    assert finding.subjects == tuple(sorted((part.id, facet.id)))


@pytest.mark.parametrize("colour", _VALID)
def test_every_allowed_colour_is_silent_on_a_wire_and_in_a_product(colour: str) -> None:
    wire, wire_facet = _wire(colour)
    part, facet = _product(colour)
    assert check_colours(_freeze((wire, wire_facet, part, facet))) == ()


def test_every_base_code_is_silent_and_dropping_one_would_make_it_fire() -> None:
    """Acceptance 8's probe target: each base code on its own is a legal colour."""
    for code in (*BASE_COLOURS, *RESERVED_COLOURS):
        conductor, facet = _wire(code)
        assert check_colours(_freeze((conductor, facet))) == ()
