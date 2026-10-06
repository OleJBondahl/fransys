"""WP10 tests: every facet of design/facets.md in a model that holds its subject.

The tests in `test_facets.py` build a facet on its own. Here each facet is put in a
model with a real subject, so what freeze enforces (subject kind, cardinality, values) is
tested on the real kinds, one table row per design/facets.md row.
"""

import dataclasses
from decimal import Decimal
from typing import Any

import pytest
from examples import cable_4_core_part, core_model, relay_part_bundle

from fransys_model.kernel import (
    FreezeError,
    Id,
    Origin,
    RefError,
    SchemaError,
    dumps,
    evolve,
    freeze,
    loads,
    make_id,
    merge,
)
from fransys_model.vocab import facets
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import ConductorKind, Gender, SignalType
from fransys_model.vocab.facets import (
    AssignedDesignationFacet,
    AssignedUnitTagFacet,
    BoundaryValuesFacet,
    CableFacet,
    CableProductFacet,
    ConnectorFacet,
    CoreFacet,
    FootprintFacet,
    OperatingFacet,
    PartRatingFacet,
    PcbFacet,
    PlcBindingFacet,
    PlcChannelFacet,
    PlcRequestFacet,
    RatingFacet,
    ReservedDesignationFacet,
    ScalingFacet,
    SupplyFacet,
    TerminalFacet,
    WireFacet,
)
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.templates import FunctionTemplate, Part
from fransys_model.vocab.units import Boundary

_ORIGIN = Origin(file="test_facet_model.py", line=1, note="fixture")
_BUNDLE = relay_part_bundle()
_HOUSING = make_id(Item, ("plant", "housing"))
_BOARD = make_id(Item, ("plant", "board"))
_HOUSING_J1 = make_id(Function, ("plant", "housing", "j1"))
_BOARD_J1 = make_id(Function, ("plant", "board", "j1"))
_W1 = make_id(Conductor, ("plant", "w1"))
_W2 = make_id(Conductor, ("plant", "w2"))
_COIL_TEMPLATE = make_id(FunctionTemplate, ("examples", "relay", "fn", "coil"))
_NO_1_TEMPLATE = make_id(FunctionTemplate, ("examples", "relay", "fn", "no_1"))
_CABLE_PART = cable_4_core_part()
_UNIT_RELEASE = UnitRelease(
    id=make_id(UnitRelease, ("unit_release", "io_board", "1", "1")),
    key=("unit_release", "io_board", "1", "1"),
    name="io_board",
    version=1,
    revision=1,
    interface="1",
)
_UNIT = Unit(
    id=make_id(Unit, ("plant", "io_board")),
    key=("plant", "io_board"),
    release=_UNIT_RELEASE.id,
    parent=None,
)
_UNIT_2 = Unit(
    id=make_id(Unit, ("plant", "io_board_2")),
    key=("plant", "io_board_2"),
    release=_UNIT_RELEASE.id,
    parent=None,
)
_UNIT_RELEASE_2 = UnitRelease(
    id=make_id(UnitRelease, ("unit_release", "other_board", "1", "1")),
    key=("unit_release", "other_board", "1", "1"),
    name="other_board",
    version=1,
    revision=1,
    interface="1",
)
_BOUNDARY_A = Boundary(
    id=make_id(Boundary, ("plant", "io_board", "housing_j1")),
    key=("plant", "io_board", "housing_j1"),
    unit=_UNIT.id,
    function=_HOUSING_J1,
)
_BOUNDARY_B = Boundary(
    id=make_id(Boundary, ("plant", "io_board", "board_j1")),
    key=("plant", "io_board", "board_j1"),
    unit=_UNIT.id,
    function=_BOARD_J1,
)

# design/facets.md, one row per facet: (class, class of its subject, one per subject?, its own
# fields).
_CASES: dict[str, tuple[Any, type, bool, dict[str, Any]]] = {
    "terminal": (TerminalFacet, Item, True, {"group": "L1", "index": 1}),
    "plc_channel": (
        PlcChannelFacet,
        FunctionTemplate,
        True,
        {"signal": SignalType.DI, "channel": 3},
    ),
    "plc_request": (
        PlcRequestFacet,
        Function,
        True,
        {"signal": SignalType.AI_CURRENT, "signal_name": "Pos", "priority": 1},
    ),
    "plc_binding": (PlcBindingFacet, Function, True, {"channel": _BOARD_J1}),
    "assigned_designation": (AssignedDesignationFacet, Item, True, {"text": "K1"}),
    "scaling": (
        ScalingFacet,
        Function,
        True,
        {
            "unit": "m",
            "raw_min": 4,
            "raw_max": 20,
            "eng_min": Decimal(0),
            "eng_max": Decimal(5),
        },
    ),
    "cable_product": (
        CableProductFacet,
        Part,
        True,
        {
            "core_colours": ("brown", "black", "grey", "blue"),
            "gauge_mm2": Decimal("1.5"),
            "shielded": False,
        },
    ),
    "cable": (CableFacet, Item, True, {"length_mm": 15000}),
    "core": (CoreFacet, Conductor, True, {"index": 1}),
    "wire": (
        WireFacet,
        Conductor,
        True,
        {"colour": "blue", "gauge_mm2": Decimal("0.75"), "length_mm": 250, "label": "W1"},
    ),
    "connector": (
        ConnectorFacet,
        FunctionTemplate,
        True,
        {"style": "JST-XH", "pincount": 4, "gender": Gender.FEMALE, "marking": "X1"},
    ),
    "supply": (
        SupplyFacet,
        Part,
        False,
        {"supplier": "Example Distributor", "supplier_part_number": "EX-1", "note": ""},
    ),
    "pcb": (PcbFacet, Part, True, {"revision": "B"}),
    "footprint": (
        FootprintFacet,
        Part,
        True,
        {"library": "Resistor_SMD", "name": "R_0603_1608Metric"},
    ),
    "rating": (
        RatingFacet,
        FunctionTemplate,
        True,
        {"rating": Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))},
    ),
    "part_rating": (
        PartRatingFacet,
        Part,
        True,
        {"rating": Rating(voltage_dc_v=Decimal(30), current_dc_a=Decimal(2))},
    ),
    "operating": (
        OperatingFacet,
        FunctionTemplate,
        True,
        {"operating": Operating(nominal_voltage_v=Decimal(24), capacity_ah=Decimal("7.2"))},
    ),
    "boundary_values": (
        BoundaryValuesFacet,
        Boundary,
        True,
        {
            "rating": Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5")),
            "operating": Operating(nominal_voltage_v=Decimal(24)),
        },
    ),
    "assigned_unit_tag": (AssignedUnitTagFacet, Unit, True, {"text": "U1"}),
    "reserved_designation": (
        ReservedDesignationFacet,
        UnitRelease,
        False,
        {"scope": None, "code": "K", "text": "K2"},
    ),
}

# Two records of each subject class the model holds, for a facet kind on two subjects.
_SUBJECTS: dict[type, tuple[Id[Any], Id[Any]]] = {
    Item: (_HOUSING, _BOARD),
    Function: (_HOUSING_J1, _BOARD_J1),
    FunctionTemplate: (_COIL_TEMPLATE, _NO_1_TEMPLATE),
    Part: (_BUNDLE.part.id, _CABLE_PART.id),
    Conductor: (_W1, _W2),
    Boundary: (_BOUNDARY_A.id, _BOUNDARY_B.id),
    UnitRelease: (_UNIT_RELEASE.id, _UNIT_RELEASE_2.id),
    Unit: (_UNIT.id, _UNIT_2.id),
}
_NAMES = list(_CASES)


def _model(*facets: Any):
    """The core model plus a second part, a second conductor and a unit with two boundaries."""
    draft = merge(core_model())
    extra = Conductor(
        id=_W2,
        key=("plant", "w2"),
        a=make_id(Port, ("plant", "housing", "j1", "1")),
        b=make_id(Port, ("plant", "k1", "coil", "a2")),
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    draft.extend(
        (
            _CABLE_PART,
            extra,
            _UNIT_RELEASE,
            _UNIT_RELEASE_2,
            _UNIT,
            _UNIT_2,
            _BOUNDARY_A,
            _BOUNDARY_B,
            *facets,
        ),
        origin=_ORIGIN,
    )
    return freeze(draft)


def _facet(name: str, /, subject: Id[Any] | None = None, tag: str = "a", **changes: Any) -> Any:
    cls, subject_type, _unique, fields = _CASES[name]
    key = ("facets", name, tag)
    return cls(
        id=make_id(cls, key),
        key=key,
        subject=_SUBJECTS[subject_type][0] if subject is None else subject,
        **{**fields, **changes},
    )


def _wrong_subject(subject_type: type) -> Id[Any]:
    """An id that exists in the model under a kind other than `subject_type`'s."""
    return _BUNDLE.part.id if subject_type is Item else _HOUSING


def test_the_facets_are_the_twenty_of_the_design_table() -> None:
    """facets.md lists these kinds; each one is in the `facet` namespace and none is missing."""
    assert set(_CASES) == {
        "assigned_designation",
        "assigned_unit_tag",
        "boundary_values",
        "rating",
        "part_rating",
        "operating",
        "terminal",
        "plc_channel",
        "plc_request",
        "plc_binding",
        "scaling",
        "cable_product",
        "cable",
        "core",
        "wire",
        "connector",
        "supply",
        "pcb",
        "footprint",
        "reserved_designation",
    }
    for name, (cls, _subject, _unique, _fields) in _CASES.items():
        assert make_id(cls, ("k",)).kind == f"facet.{name}"
    assert {cls.__name__ for cls, *_ in _CASES.values()} == set(facets.__all__)


@pytest.mark.parametrize("name", _NAMES)
def test_a_facet_carries_exactly_the_fields_of_its_design_row(name: str) -> None:
    """`id`, `key`, `subject` and `ext` on every facet, and the row's own fields, nothing else."""
    cls, _subject, _unique, fields = _CASES[name]
    declared = {field.name for field in dataclasses.fields(cls)}
    assert declared == {"id", "key", "subject", "ext", *fields}


@pytest.mark.parametrize("name", _NAMES)
def test_a_facet_freezes_onto_a_subject_that_exists_and_is_read_back(name: str) -> None:
    """The row's own subject kind is accepted and `facets_of` finds the facet."""
    cls = _CASES[name][0]
    facet = _facet(name)
    model = _model(facet)
    assert facets_of(model, cls) == {facet.id: facet}


@pytest.mark.parametrize("name", _NAMES)
def test_a_facet_refuses_a_subject_of_another_kind(name: str) -> None:
    """The subject exists, but as another kind: a `RefError` on the field `subject`."""
    wrong = _wrong_subject(_CASES[name][1])
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(name, wrong))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert (error.field, error.target) == ("subject", wrong)


@pytest.mark.parametrize("name", _NAMES)
def test_a_facet_refuses_a_subject_that_does_not_exist(name: str) -> None:
    """A subject with no record is a `RefError` too."""
    missing = make_id(_CASES[name][1], ("nowhere",))
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(name, missing))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert error.field == "subject"


@pytest.mark.parametrize("name", _NAMES)
def test_a_second_facet_of_one_kind_on_one_subject_is_refused_except_for_supply(name: str) -> None:
    """One per subject (facets.md) is a schema rule: `freeze` raises, naming the later record."""
    cls, _subject, unique, _fields = _CASES[name]
    first, second = _facet(name, tag="a"), _facet(name, tag="b")
    if not unique:
        assert len(facets_of(_model(first, second), cls)) == 2
        return
    with pytest.raises(FreezeError) as excinfo:
        _model(first, second)
    (error,) = excinfo.value.errors
    assert isinstance(error, SchemaError)
    assert error.record_id == max(first.id, second.id)
    assert "per subject" in str(error)


@pytest.mark.parametrize("name", _NAMES)
def test_one_facet_kind_may_sit_on_two_subjects(name: str) -> None:
    """Cardinality is per subject: two subjects, two facets of one kind."""
    cls, subject_type, _unique, _fields = _CASES[name]
    one, other = _SUBJECTS[subject_type]
    facets = (_facet(name, one, "a"), _facet(name, other, "b"))
    assert len(facets_of(_model(*facets), cls)) == 2


def test_different_facet_kinds_share_a_subject() -> None:
    """A terminal that is also a cable item, a template that is a channel and a connector."""
    pairs = [
        ("terminal", "cable", _HOUSING),
        ("plc_channel", "connector", _COIL_TEMPLATE),
        ("wire", "core", _W1),
        ("plc_request", "scaling", _HOUSING_J1),
        ("scaling", "plc_binding", _HOUSING_J1),
        ("pcb", "footprint", _BUNDLE.part.id),
        ("pcb", "supply", _BUNDLE.part.id),
    ]
    for first, second, subject in pairs:
        model = _model(_facet(first, subject), _facet(second, subject))
        assert len(facets_of(model, _CASES[first][0])) == 1
        assert len(facets_of(model, _CASES[second][0])) == 1


def test_a_plc_binding_names_a_function_as_its_channel() -> None:
    """`channel` is an `Id[Function]`: an item is refused, with the field named."""
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet("plc_binding", channel=_HOUSING))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert (error.field, error.target) == ("channel", _HOUSING)


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        ("scaling", {"eng_max": 5.0}),
        ("wire", {"gauge_mm2": 0.75}),
        ("cable_product", {"gauge_mm2": 1.5}),
        ("cable_product", {"core_colours": ["brown"]}),
        ("terminal", {"index": 1.0}),
        ("plc_channel", {"signal": "di"}),
        ("connector", {"gender": "female"}),
    ],
    ids=[
        "scaling-float",
        "wire-float",
        "product-float",
        "colours-list",
        "index-float",
        "signal-str",
        "gender-str",
    ],
)
def test_a_facet_value_outside_its_declared_type_is_refused_at_freeze(
    name: str, changes: dict[str, Any]
) -> None:
    """A float for a `Decimal`, a list for a tuple, a string for an enum: the field is named."""
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(name, **changes))
    (error,) = excinfo.value.errors
    (field,) = changes
    assert f"{_CASES[name][0].__name__}.{field}" in str(error)


def test_every_facet_survives_canonical_form() -> None:
    """`loads(dumps(m)) == m`, with the `Decimal`s, enums and tuples of the facets intact."""
    facets = [_facet(name) for name in _NAMES]
    facets.append(_facet("supply", tag="b", supplier="Other Distributor"))
    model = _model(*facets)
    again = loads(dumps(model))
    assert again == model
    assert again.digests == model.digests
    (wire,) = facets_of(again, WireFacet).values()
    assert wire.gauge_mm2 == Decimal("0.75")
    (product,) = facets_of(again, CableProductFacet).values()
    assert product.core_colours == ("brown", "black", "grey", "blue")
    (channel,) = facets_of(again, PlcChannelFacet).values()
    assert channel.signal is SignalType.DI


def test_changing_a_facet_changes_the_facet_digest_and_no_other_namespace() -> None:
    """Facets live in their own namespace: a scaling edit does not touch `core`."""
    model = _model(_facet("scaling"))
    (scaling,) = facets_of(model, ScalingFacet).values()
    changed = dataclasses.replace(scaling, eng_max=Decimal(6))
    origin = Origin(file="test_facet_model.py", line=2, note="edit")
    edited = evolve(model, put=(changed,), remove=(scaling.id,), origin=origin)
    assert edited.digests["facet"] != model.digests["facet"]
    assert edited.digests["core"] == model.digests["core"]
    assert edited.digest != model.digest


@pytest.mark.parametrize(
    ("name", "field"),
    [("cable", "length_mm"), ("wire", "length_mm"), ("wire", "label"), ("connector", "gender")],
    ids=["cable-length", "wire-length", "wire-label", "connector-gender"],
)
def test_an_optional_facet_field_may_be_none_and_survives_canonical_form(
    name: str, field: str
) -> None:
    """A cable not yet measured, a wire with no label: `None` is a value, not a missing one."""
    cls = _CASES[name][0]
    changes: dict[str, Any] = {field: None}
    model = _model(_facet(name, **changes))
    (facet,) = facets_of(loads(dumps(model)), cls).values()
    assert getattr(facet, field) is None


def test_a_connector_facet_built_with_no_gender_has_none() -> None:
    """Decision model-0080: `gender` defaults to `None`, not to `Gender.NEUTRAL`."""
    fields = {k: v for k, v in _CASES["connector"][3].items() if k != "gender"}
    key = ("facets", "connector", "a")
    facet = ConnectorFacet(
        id=make_id(ConnectorFacet, key), key=key, subject=_NO_1_TEMPLATE, **fields
    )
    assert facet.gender is None


_OPTIONAL = {
    ("boundary_values", "rating"),
    ("boundary_values", "operating"),
    ("cable", "length_mm"),
    ("wire", "length_mm"),
    ("wire", "label"),
    ("connector", "marking"),
    ("connector", "gender"),
    ("reserved_designation", "scope"),
    ("reserved_designation", "code"),
}


@pytest.mark.parametrize(
    ("name", "field"),
    [
        (name, field)
        for name, (_cls, _subject, _unique, fields) in _CASES.items()
        for field in fields
        if (name, field) not in _OPTIONAL
    ],
)
def test_a_required_facet_field_refuses_none(name: str, field: str) -> None:
    """Only the `_OPTIONAL` fields may be `None`: two lengths, a wire label, a connector's
    marking and gender (decision model-0080).

    A boundary-values facet may leave either of its two values `None`, never both.
    """
    changes: dict[str, Any] = {field: None}
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(name, **changes))
    (error,) = excinfo.value.errors
    assert f"{_CASES[name][0].__name__}.{field}" in str(error)


@pytest.mark.parametrize("name", _NAMES)
def test_the_subject_of_a_facet_refuses_none(name: str) -> None:
    """A facet describes something: `subject` is never optional."""
    cls, _subject_type, _unique, fields = _CASES[name]
    key = ("facets", name, "a")
    with pytest.raises(FreezeError) as excinfo:
        _model(cls(id=make_id(cls, key), key=key, subject=None, **fields))
    assert f"{cls.__name__}.subject" in str(excinfo.value.errors[0])
