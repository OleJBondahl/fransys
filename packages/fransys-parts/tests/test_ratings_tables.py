"""The rating tables of a part file: load, lint refusals and the demo round trip (parts-0004)."""

import itertools
from decimal import Decimal
from pathlib import Path

import fransys_parts
import pytest

from fransys_model.kernel import Severity, freeze, make_id
from fransys_model.vocab import (
    FunctionTemplate,
    OperatingFacet,
    Part,
    PartRatingFacet,
    RatingFacet,
    facets_of,
)

DEMO = (
    next(p for p in Path(__file__).resolve().parents if (p / "examples").is_dir())
    / "examples"
    / "demo-parts"
    / "demo_parts"
)
_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_roots = itertools.count()

_HEAD = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"
"""
_FUNCTION = """
[[function]]
name = "f1"
kind = "generic"
ports = [{ name = "1", role = "generic" }]
"""
_PART_KEY = ("part", "Demo", "X-1")
_FUNCTION_KEY = (*_PART_KEY, "function", "f1")


def _root(tmp_path, text):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(text)
    return root


def _function_with(tables):
    return _HEAD + _FUNCTION + tables


def _lint(tmp_path, text):
    return fransys_parts.lint(_root(tmp_path, text))


def _codes(tmp_path, text):
    return {f.code for f in _lint(tmp_path, text)}


def _line_of(text, header):
    return next(i for i, line in enumerate(text.splitlines(), start=1) if line == header)


# ---- loading ----------------------------------------------------------------------------------


def test_function_rating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _function_with('\n[function.rating]\nvoltage_ac_v = "690"\ncurrent_ac_a = "0.5"\n')
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    (facet,) = facets_of(model, RatingFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.key == (*_FUNCTION_KEY, "rating")
    assert facet.rating.voltage_ac_v == Decimal(690)
    assert facet.rating.current_ac_a == Decimal("0.5")
    assert facet.rating.voltage_dc_v is None
    assert facet.rating.current_dc_a is None
    origin = model.origins[facet.id]
    assert (origin.file, origin.line) == ("parts/p.toml", _line_of(text, "[function.rating]"))


def test_function_operating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _function_with('\n[function.operating]\nnominal_voltage_v = "24"\ncapacity_ah = "7.2"\n')
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    (facet,) = facets_of(model, OperatingFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.key == (*_FUNCTION_KEY, "operating")
    assert facet.operating.nominal_voltage_v == Decimal(24)
    assert facet.operating.capacity_ah == Decimal("7.2")
    assert facet.operating.max_voltage_v is None
    origin = model.origins[facet.id]
    assert origin.line == _line_of(text, "[function.operating]")


def test_part_rating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _HEAD + '\n[rating]\nvoltage_dc_v = "48"\n' + _FUNCTION
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    (facet,) = facets_of(model, PartRatingFacet).values()
    assert facet.subject == make_id(Part, _PART_KEY)
    assert facet.key == (*_PART_KEY, "rating")
    assert facet.rating.voltage_dc_v == Decimal(48)
    assert facet.rating.voltage_ac_v is None
    assert model.origins[facet.id].line == _line_of(text, "[rating]")


def test_second_function_rating_gets_its_own_header_line(tmp_path):
    second = _FUNCTION.replace('"f1"', '"f2"').replace('name = "1"', 'name = "2"')
    text = _function_with('\n[function.rating]\nvoltage_ac_v = "1"\n') + second
    text += '\n[function.rating]\nvoltage_ac_v = "2"\n'
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    lines = {
        f.rating.voltage_ac_v: model.origins[f.id].line
        for f in facets_of(model, RatingFacet).values()
    }
    header_lines = [i for i, x in enumerate(text.splitlines(), start=1) if x == "[function.rating]"]
    assert lines == {Decimal(1): header_lines[0], Decimal(2): header_lines[1]}


def test_a_library_without_rating_tables_has_no_rating_records(tmp_path):
    model = freeze(fransys_parts.load_path(_root(tmp_path, _HEAD + _FUNCTION)))
    assert not model.tables.get("facet.rating")
    assert not model.tables.get("facet.part_rating")
    assert not model.tables.get("facet.operating")


def test_demo_library_round_trips_the_three_tables():
    model = freeze(fransys_parts.load_path(DEMO))
    contactor_main = make_id(
        FunctionTemplate, ("part", "Demo", "DEMO-CTR-3P-24", "function", "main")
    )
    (rating,) = [f for f in facets_of(model, RatingFacet).values() if f.subject == contactor_main]
    assert rating.rating.voltage_ac_v == Decimal(690)
    assert rating.rating.current_ac_a == Decimal(25)

    cable = make_id(Part, ("part", "Demo", "DEMO-CBL-4G1.5"))
    (part_rating,) = [f for f in facets_of(model, PartRatingFacet).values() if f.subject == cable]
    assert part_rating.rating.voltage_ac_v == Decimal(500)

    lamp = make_id(FunctionTemplate, ("part", "Demo", "DEMO-LAMP-24", "function", "lamp"))
    (operating,) = [f for f in facets_of(model, OperatingFacet).values() if f.subject == lamp]
    assert operating.operating.voltage_dc_v == Decimal(24)


# ---- lint: clean and unchanged behaviour -------------------------------------------------------


def test_valid_tables_lint_clean(tmp_path):
    tables = '\n[function.rating]\nvoltage_ac_v = "250"\ncurrent_ac_a = "0.5"\n'
    tables += '\n[function.operating]\nvoltage_dc_v = "24"\n'
    assert _lint(tmp_path, _function_with(tables)) == ()
    assert _lint(tmp_path, _HEAD + '\n[rating]\nvoltage_ac_v = "500"\n' + _FUNCTION) == ()


def test_top_level_rating_is_not_an_unknown_table(tmp_path):
    assert "TABLE_UNKNOWN" not in _codes(tmp_path, _HEAD + '\n[rating]\nvoltage_ac_v = "5"\n')


def test_function_sub_tables_do_not_make_the_function_entry_unknown(tmp_path):
    tables = '\n[function.rating]\nvoltage_ac_v = "5"\n[function.operating]\nvoltage_dc_v = "5"\n'
    assert "FIELD_UNKNOWN" not in _codes(tmp_path, _function_with(tables))


# ---- lint: refusals ----------------------------------------------------------------------------

_TABLES = {
    "rating": (lambda body: _HEAD + f"\n[rating]\n{body}" + _FUNCTION, "[rating]"),
    "function.rating": (
        lambda body: _function_with(f"\n[function.rating]\n{body}"),
        "[function.rating]",
    ),
    "function.operating": (
        lambda body: _function_with(f"\n[function.operating]\n{body}"),
        "[function.operating]",
    ),
}
_FIELD = {"rating": "voltage_ac_v", "function.rating": "voltage_ac_v"}


def _one(tmp_path, table, body, code):
    build, header = _TABLES[table]
    text = build(body)
    (found,) = [f for f in _lint(tmp_path, text) if f.code == code]
    assert found.severity is Severity.ERROR
    assert found.message.startswith(f"parts/p.toml:{_line_of(text, header)}: ")
    assert table in found.message
    return found


@pytest.mark.parametrize("table", list(_TABLES))
def test_empty_table_is_refused(tmp_path, table):
    found = _one(tmp_path, table, "", "RATING_TABLE_EMPTY")
    assert "no field" in found.message


@pytest.mark.parametrize("table", list(_TABLES))
def test_empty_table_reports_nothing_else(tmp_path, table):
    build, _ = _TABLES[table]
    assert {f.code for f in _lint(tmp_path, build(""))} == {"RATING_TABLE_EMPTY"}


@pytest.mark.parametrize("table", list(_TABLES))
@pytest.mark.parametrize(
    "bad",
    [
        "-5",
        "abc",
        "",
        "NaN",
        "Infinity",
        " 230",
        "230 ",
        "1_000",
        "2.5e2",
        "+5",
        ".5",
        "5.",
    ],
)
def test_bad_value_is_refused(tmp_path, table, bad):
    field = _FIELD.get(table, "voltage_dc_v")
    found = _one(tmp_path, table, f'{field} = "{bad}"\n', "RATING_VALUE_INVALID")
    assert field in found.message


@pytest.mark.parametrize("good", ["250", "0.5", "24", "0.001", "1000000"])
def test_good_value_is_accepted(tmp_path, good):
    text = _function_with(f'\n[function.rating]\ncurrent_dc_a = "{good}"\n')
    assert _lint(tmp_path, text) == ()


@pytest.mark.parametrize("table", list(_TABLES))
def test_unknown_field_is_refused(tmp_path, table):
    found = _one(tmp_path, table, 'watts = "5"\n', "FIELD_UNKNOWN")
    assert "'watts'" in found.message


def test_operating_field_is_unknown_in_a_rating_table(tmp_path):
    text = _function_with('\n[function.rating]\nnominal_voltage_v = "24"\n')
    assert "FIELD_UNKNOWN" in _codes(tmp_path, text)


@pytest.mark.parametrize("table", list(_TABLES))
def test_bare_float_is_forbidden_and_not_double_reported(tmp_path, table):
    field = _FIELD.get(table, "voltage_dc_v")
    build, _ = _TABLES[table]
    findings = _lint(tmp_path, build(f"{field} = 24.5\n"))
    assert [f.code for f in findings] == ["FLOAT_FORBIDDEN"]


@pytest.mark.parametrize("table", list(_TABLES))
def test_bare_int_is_a_field_type_error_and_not_double_reported(tmp_path, table):
    field = _FIELD.get(table, "voltage_dc_v")
    build, _ = _TABLES[table]
    findings = _lint(tmp_path, build(f"{field} = 24\n"))
    assert [f.code for f in findings] == ["FIELD_TYPE"]


_INLINE_FUNCTION = """
[[function]]
name = "f1"
kind = "generic"
{inline}
ports = [{{ name = "1", role = "generic" }}]
"""


def test_inline_rating_table_is_reported_at_the_functions_header_line(tmp_path):
    text = _HEAD + _INLINE_FUNCTION.format(inline='rating = { voltage_ac_v = "0" }')
    (found,) = [f for f in _lint(tmp_path, text) if f.code == "RATING_VALUE_INVALID"]
    assert found.message.startswith(f"parts/p.toml:{_line_of(text, '[[function]]')}: ")


def test_bare_int_rating_inside_a_function_is_a_field_type_error_only(tmp_path):
    text = _HEAD + _INLINE_FUNCTION.format(inline="rating = 5")
    assert [f.code for f in _lint(tmp_path, text)] == ["FIELD_TYPE"]


def test_rating_key_inside_a_supply_is_an_unknown_field(tmp_path):
    supply = '\n[[supply]]\nsupplier = "S"\nsupplier_part_number = "1"\nrating = { a = "5" }\n'
    findings = _lint(tmp_path, _HEAD + _FUNCTION + supply)
    assert [f.code for f in findings] == ["FIELD_UNKNOWN"]


def test_a_rating_that_is_not_a_table_is_a_field_type_error(tmp_path):
    text = _HEAD.replace("schema = 1\n", "schema = 1\nrating = 5\n") + _FUNCTION
    codes = _codes(tmp_path, text)
    assert "FIELD_TYPE" in codes
    assert "RATING_TABLE_EMPTY" not in codes
