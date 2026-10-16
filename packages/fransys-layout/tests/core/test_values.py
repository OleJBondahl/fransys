"""The values contract (P1.1, C3): frozen plain data, a versioned JSON form, closed vocabularies."""

import ast
import dataclasses
import pathlib
import re
import typing
from typing import Any

import pytest

from fransys_layout.core import jsonform, outputs, values
from fransys_layout.core.keys import natural_key
from fransys_layout.core.outputs import CoreLayout
from fransys_layout.core.values import Block, Cell, End, Options, PlacementProblem

from . import values_fixtures
from .values_fixtures import all_values, layout, problem

CLASSES = [
    c
    for m in (values, outputs)
    for c in vars(m).values()
    if isinstance(c, type) and dataclasses.is_dataclass(c) and c.__module__ == m.__name__
]
DROPPED_OPTIONS = [
    "flow_axis",
    "two_edge_split",
    "tie_key",
    "widen_passes",
    "seed",
    "move_budget",
    "stand_height",
    "w_stub",
    "w_copy",
    "w_star",
    "w_x",
    "w_b",
    "w_d",
]


def plain_of(value: object) -> dict[str, Any]:
    return jsonform.to_plain(value)


def _walk(value: object):
    """Every dataclass instance inside value, value first."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        yield value
        for f in dataclasses.fields(value):
            yield from _walk(getattr(value, f.name))
    elif isinstance(value, tuple | frozenset):
        for v in value:
            yield from _walk(v)


def _fields_with_defaults():
    return {
        (c.__name__, f.name)
        for c in CLASSES
        if c is not Options
        for f in dataclasses.fields(c)
        if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
    }


def _set_once(*roots: object) -> set[tuple[str, str]]:
    """The (class, field) pairs with a default that some instance in roots sets to another value."""
    out = set()
    for root in roots:
        for obj in _walk(root):
            for f in dataclasses.fields(obj):
                default = (
                    f.default
                    if f.default is not dataclasses.MISSING
                    else (
                        f.default_factory() if f.default_factory is not dataclasses.MISSING else f
                    )
                )
                if default is not f and getattr(obj, f.name) != default:
                    out.add((type(obj).__name__, f.name))
    return out


@pytest.mark.parametrize("cls", CLASSES, ids=lambda c: c.__name__)
def test_every_value_is_frozen_with_slots(cls):
    assert cls.__dataclass_params__.frozen
    assert "__slots__" in cls.__dict__


def test_assigning_to_a_value_raises():
    pin = problem().symbols[0].pins[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        pin.dx = 1  # ty: ignore[invalid-assignment] - the assignment is the thing under test


def test_the_hand_built_values_set_every_optional_field_once():
    holders = [v for v in all_values() if not isinstance(v, str)]
    unset = _fields_with_defaults() - _set_once(*holders)
    assert unset == set()


def test_the_optional_field_check_can_fail():
    bare = values.Pin("1", "N", 0, 0, 0)
    assert ("Pin", "stand") in _fields_with_defaults() - _set_once(bare)


@pytest.mark.parametrize("make", [problem, layout], ids=["problem", "layout"])
def test_to_plain_then_from_plain_is_identity(make):
    value = make()
    plain = plain_of(value)
    assert jsonform.from_plain(type(value), plain) == value


@pytest.mark.parametrize("value", all_values(), ids=lambda v: type(v).__name__)
def test_every_value_has_a_json_form_that_reads_back(value):
    plain = plain_of(value)
    assert jsonform.from_plain(type(value), plain) == value


@pytest.mark.parametrize("make", [problem, layout], ids=["problem", "layout"])
def test_the_json_form_carries_its_format(make):
    assert plain_of(make())["format"] == 1


def test_nested_values_carry_no_format():
    plain = plain_of(problem())
    assert "format" not in plain["symbols"][0]


@pytest.mark.parametrize("make", [problem, layout], ids=["problem", "layout"])
@pytest.mark.parametrize("bad", [2, "1", None])
def test_from_plain_refuses_another_format_and_names_it(make, bad):
    plain = plain_of(make()) | {"format": bad}
    with pytest.raises(ValueError, match=re.escape(f"format {bad!r}")):
        jsonform.from_plain(type(make()), plain)


def test_from_plain_refuses_a_missing_format():
    plain = plain_of(problem())
    del plain["format"]
    with pytest.raises(ValueError, match="format None"):
        jsonform.from_plain(PlacementProblem, plain)


def _put(data: Any, path: list, value: object) -> None:
    for step in path[:-1]:
        data = data[step]
    data[path[-1]] = value


VOCAB = [
    (problem, ["symbols", 0, "pins", 0, "side"], "Pin.side"),
    (problem, ["symbols", 0, "pins", 0, "stand"], "Pin.stand"),
    (problem, ["symbols", 0, "orientations", 0], "Sym.orientations"),
    (problem, ["nets", 0, "rail", "power"], "Rail.power"),
    (layout, ["routes", "pages", 0, "wires", 0, "kind"], "Wire.kind"),
    (layout, ["annotations", "markers", 0, "kind"], "Marker.kind"),
    (layout, ["references", 0, "kind"], "Ref.kind"),
    (layout, ["findings", 0, "code"], "Finding.code"),
    (layout, ["placement", "pages", 0, "placed", 0, "orient"], "Placed.orient"),
]


@pytest.mark.parametrize(("make", "path", "field"), VOCAB, ids=[v[2] for v in VOCAB])
def test_a_vocabulary_rejects_an_unknown_string_naming_the_field(make, path, field):
    plain = plain_of(make())
    _put(plain, path, "NOPE")
    with pytest.raises(ValueError, match=rf"{field}: 'NOPE' is not one of"):
        jsonform.from_plain(type(make()), plain)


def test_the_stage_values_reject_an_unknown_string_naming_the_field():
    block = typing.cast("values.BlockList", all_values()[3]).blocks[0]
    cases = [
        (Cell, Cell("K1", "R0", None, None), "orient", "Cell.orient"),
        (End, End("open"), "kind", "End.kind"),
        (Block, block, "kind", "Block.kind"),
    ]
    for cls, value, key, field in cases:
        plain = plain_of(value)
        plain[key] = "NOPE"
        with pytest.raises(ValueError, match=rf"{field}: 'NOPE' is not one of"):
            jsonform.from_plain(cls, plain)


def test_the_new_finding_codes_are_in_the_vocabulary():
    codes = typing.get_args(values.FindingCode)
    for code in ("FILL_UNDER_MIN", "WIDER_THAN_PAGE", "LANE_TURNED"):
        assert code in codes


def test_natural_key_orders_digits_as_numbers():
    assert sorted(["H10", "H2", "H1"], key=natural_key) == ["H1", "H2", "H10"]


def test_options_defaults_follow_the_design_with_e4():
    o = Options()
    assert o.box_pins == "spread"
    assert o.justify is True


@pytest.mark.parametrize("name", DROPPED_OPTIONS)
def test_the_unread_options_are_gone(name):
    assert name not in {f.name for f in dataclasses.fields(Options)}


def test_c3_contract_shape():
    names = {c.__name__: {f.name for f in dataclasses.fields(c)} for c in CLASSES}
    assert {"label", "table"} <= names["Sym"]
    assert not {"text", "text_w", "table_rows"} & names["Sym"]
    assert "failed" in names["Routes"]
    assert "row" in names["RefEnd"]
    assert {"stand", "fan"} <= names["End"]
    assert "ref" not in names["End"]
    assert "tracks" in names["Gap"]
    assert "reserved" not in names["Gap"]
    assert "pin_class" not in names["Pin"]
    assert "PinClass" not in names
    assert "crossed" not in names["Bundle"]
    assert "crossed" in names["Fan"]
    assert not {"shape", "narrow"} & names["Column"]
    assert isinstance(CoreLayout, type)


def test_a_value_with_no_json_form_is_refused():
    with pytest.raises(TypeError, match="no JSON form for dict"):
        jsonform.to_plain({"a": 1})


def test_a_wrong_scalar_type_is_refused_and_an_int_reads_as_a_float():
    plain = plain_of(Options())
    plain["min_fill"] = 1
    assert jsonform.from_plain(Options, plain).min_fill == 1.0
    plain["wire_min"] = "8"
    with pytest.raises(TypeError, match="expected"):
        jsonform.from_plain(Options, plain)


def test_the_scene_values_reject_an_unknown_string_naming_the_field():
    from .values_fixtures import scene_value

    for path, field in [
        (["boxes", 0, "pins", 0, "side"], "ScenePin.side"),
        (["markers", 0, "kind"], "SceneMarker.kind"),
    ]:
        plain = plain_of(scene_value())
        _put(plain, path, "NOPE")
        with pytest.raises(ValueError, match=rf"{field}: 'NOPE' is not one of"):
            jsonform.from_plain(outputs.Scene, plain)


def test_the_marker_names_the_pin_it_stands_at():
    assert layout().annotations.markers[0].end == values.PinRef("K1", "1")


def test_the_options_carry_geometry_for_the_placement_strings_and_no_colours():
    o = Options()
    assert o.open_stub == 0
    assert o.box_columns is True
    assert o.cells == (8, 6)
    assert o.wire_label_sides == ("N", "S")
    assert o.marker == values.Size(24, 8)
    assert "colours" not in {f.name for f in dataclasses.fields(Options)}


def test_the_new_size_fields_default_to_none_or_empty():
    assert values.Net("N", ()).label is None
    assert values.Facts().row_tags == ()
    names = {c.__name__: {f.name for f in dataclasses.fields(c)} for c in CLASSES}
    assert "page_titles" not in names["Hints"]
    assert "groups" in names["PagePlan"]
    assert "title" not in names["PagePlan"]


def test_a_label_has_no_text_and_a_table_has_cells_not_rows():
    names = {c.__name__: {f.name for f in dataclasses.fields(c)} for c in CLASSES}
    assert "text" not in names["Label"]
    assert "cells" in names["Table"]
    assert "rows" not in names["Table"]


def test_a_marker_has_no_text_and_no_colour():
    names = {c.__name__: {f.name for f in dataclasses.fields(c)} for c in CLASSES}
    assert not {"text", "colour"} & names["Marker"]
    assert "cell" in names["Marker"]


def test_annotations_hold_wire_labels():
    assert outputs.Annotations().wire_labels == ()
    assert layout().annotations.wire_labels[0].net == "N1"


def test_no_core_value_carries_a_string_to_print():
    banned = {"text", "colour", "title", "page_titles"}
    for cls in CLASSES:
        if cls is values.Finding:
            continue
        assert not banned & {f.name for f in dataclasses.fields(cls)}, cls.__name__


def test_no_stage_ties_by_a_designation():
    """Attribute half; the behaviour half is test_stage_ties.py."""
    core = pathlib.Path(values.__file__).parent
    for path in core.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr in {"text", "text_w", "colour"}:
                msg = f"{path.name}:{node.lineno} reads .{node.attr}"
                raise AssertionError(msg)


@pytest.mark.parametrize("orient", typing.get_args(values.Orientation))
def test_every_orientation_has_a_json_form_that_reads_back(orient):
    box = dataclasses.replace(values_fixtures.scene_value().boxes[0], orient=orient)
    assert jsonform.from_plain(type(box), plain_of(box)) == box
