"""The rating tables of a part file: load, lint refusals and the demo round trip (parts-0004)."""

from decimal import Decimal
from pathlib import Path

import fransys_parts
import pytest
from part_roots import part_root

from fransys_model.derive import function_templates
from fransys_model.elecdef import Connection, Current, Quantity, Unit
from fransys_model.kernel import Severity, freeze, make_id
from fransys_model.vocab import (
    BlockFacet,
    FunctionTemplate,
    OperatingFacet,
    Part,
    PartRatingFacet,
    RatingFacet,
    facets_of,
    parts,
)

DEMO = next(p for p in Path(__file__).resolve().parents if (p / "examples").is_dir()) / "examples" / "demo-parts" / "demo_parts"

_HEAD = """schema = 2

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


def _function_with(tables):
    return _HEAD + _FUNCTION + tables


def _lint(tmp_path, text):
    return fransys_parts.lint(part_root(tmp_path, text))


def _codes(tmp_path, text):
    return {f.code for f in _lint(tmp_path, text)}


def _line_of(text, header):
    return next(i for i, line in enumerate(text.splitlines(), start=1) if line == header)


# ---- loading ----------------------------------------------------------------------------------


def test_function_rating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _function_with('\n[function.rating]\nvoltage = [{ nom = "690 V", at = ["AC"] }]\ncurrent = [{ nom = "0.5 A", at = ["AC"] }]\n')
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    (facet,) = facets_of(model, RatingFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.key == (*_FUNCTION_KEY, "rating")
    (voltage,), (current,) = facet.rating.voltage, facet.rating.current
    assert voltage.nom == Quantity(Decimal(690), Unit.V)
    assert voltage.at.get(Current) is Current.AC
    assert current.nom == Quantity(Decimal("0.5"), Unit.A)
    assert facet.rating.power_loss is None
    origin = model.origins[facet.id]
    assert (origin.file, origin.line) == ("parts/p.toml", _line_of(text, "[function.rating]"))


def test_function_operating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _function_with('\n[function.operating]\nvoltage = [{ nom = "24 V", min = "18 V", at = ["DC"] }]\ncapacity = "7.2 Ah"\n')
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    (facet,) = facets_of(model, OperatingFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.key == (*_FUNCTION_KEY, "operating")
    (voltage,) = facet.operating.voltage
    assert (voltage.nom, voltage.min, voltage.max) == (Quantity(Decimal(24), Unit.V), Quantity(Decimal(18), Unit.V), None)
    assert facet.operating.capacity == Quantity(Decimal("7.2"), Unit.AH)
    assert facet.operating.nominal_current is None
    origin = model.origins[facet.id]
    assert origin.line == _line_of(text, "[function.operating]")


def test_part_rating_loads_with_subject_key_values_and_origin(tmp_path):
    text = _HEAD + '\n[rating]\nvoltage = [{ nom = "48 V", at = ["DC"] }]\n' + _FUNCTION
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    (facet,) = facets_of(model, PartRatingFacet).values()
    assert facet.subject == make_id(Part, _PART_KEY)
    assert facet.key == (*_PART_KEY, "rating")
    (voltage,) = facet.rating.voltage
    assert (voltage.nom, voltage.at.get(Current)) == (Quantity(Decimal(48), Unit.V), Current.DC)
    assert model.origins[facet.id].line == _line_of(text, "[rating]")


def test_second_function_rating_gets_its_own_header_line(tmp_path):
    second = _FUNCTION.replace('"f1"', '"f2"').replace('name = "1"', 'name = "2"')
    text = _function_with('\n[function.rating]\nvoltage = [{ nom = "1 V", at = ["AC"] }]\n') + second
    text += '\n[function.rating]\nvoltage = [{ nom = "2 V", at = ["AC"] }]\n'
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    lines = {f.rating.voltage[0].nom.value: model.origins[f.id].line for f in facets_of(model, RatingFacet).values() if f.rating.voltage[0].nom}
    header_lines = [i for i, x in enumerate(text.splitlines(), start=1) if x == "[function.rating]"]
    assert lines == {1: header_lines[0], 2: header_lines[1]}


def test_a_library_without_rating_tables_has_no_rating_records(tmp_path):
    model = freeze(fransys_parts.load_path(part_root(tmp_path, _HEAD + _FUNCTION)))
    assert not model.tables.get("facet.rating")
    assert not model.tables.get("facet.part_rating")
    assert not model.tables.get("facet.operating")


def test_demo_library_round_trips_the_three_tables():
    model = freeze(fransys_parts.load_path(DEMO))
    contactor_main = make_id(FunctionTemplate, ("part", "Demo", "DEMO-CTR-3P-24", "function", "main"))
    (rating,) = [f for f in facets_of(model, RatingFacet).values() if f.subject == contactor_main]
    assert rating.rating.voltage[0].nom == Quantity(Decimal(690), Unit.V)
    assert rating.rating.current[0].nom == Quantity(Decimal(25), Unit.A)

    cable = make_id(Part, ("part", "Demo", "DEMO-CBL-4G1.5"))
    (part_rating,) = [f for f in facets_of(model, PartRatingFacet).values() if f.subject == cable]
    assert part_rating.rating.voltage[0].nom == Quantity(Decimal(500), Unit.V)

    lamp = make_id(FunctionTemplate, ("part", "Demo", "DEMO-LAMP-24", "function", "lamp"))
    (operating,) = [f for f in facets_of(model, OperatingFacet).values() if f.subject == lamp]
    assert operating.operating.voltage[0].nom == Quantity(Decimal(24), Unit.V)


# ---- lint: clean and unchanged behaviour -------------------------------------------------------


def test_valid_tables_lint_clean(tmp_path):
    tables = '\n[function.rating]\nvoltage = [{ nom = "250 V", at = ["AC"] }]\n'
    tables += 'current = [{ nom = "0.5 A", at = ["AC"] }]\n'
    tables += '\n[function.operating]\nvoltage = [{ nom = "24 V", at = ["DC"] }]\n'
    assert _lint(tmp_path, _function_with(tables)) == ()
    assert _lint(tmp_path, _HEAD + '\n[rating]\nvoltage = [{ nom = "500 V", at = ["AC"] }]\n' + _FUNCTION) == ()


def test_top_level_rating_is_not_an_unknown_table(tmp_path):
    assert "TABLE_UNKNOWN" not in _codes(tmp_path, _HEAD + '\n[rating]\nvoltage = [{ nom = "5 V", at = ["AC"] }]\n')


def test_function_sub_tables_do_not_make_the_function_entry_unknown(tmp_path):
    tables = '\n[function.rating]\nvoltage = [{ nom = "5 V", at = ["AC"] }]\n'
    tables += '[function.operating]\nvoltage = [{ nom = "5 V", at = ["DC"] }]\n'
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


def _body(value):
    """A one-field body whose single value is the raw TOML text `value`."""
    return f'voltage = [{{ nom = {value}, at = ["AC"] }}]\n'


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
        "-5 V",
        "abc",
        "",
        "24",
        "NaN V",
        "Infinity V",
        " 230 V",
        "230 V ",
        "1_000 V",
        "2.5e2 V",
        "+5 V",
        ".5 V",
        "5. V",
        "5 furlong",
        "5  V",
    ],
)
def test_bad_value_is_refused(tmp_path, table, bad):
    found = _one(tmp_path, table, _body(f'"{bad}"'), "RATING_VALUE_INVALID")
    assert "is not a quantity" in found.message


@pytest.mark.parametrize("table", ["rating", "function.rating"])
def test_zero_is_refused_in_a_rating(tmp_path, table):
    found = _one(tmp_path, table, _body('"0 V"'), "RATING_VALUE_INVALID")
    assert "above zero" in found.message


@pytest.mark.parametrize("good", ["250", "0.5", "24", "0.001", "1000000"])
def test_good_value_is_accepted(tmp_path, good):
    text = _function_with(f'\n[function.rating]\ncurrent = [{{ nom = "{good} A", at = ["DC"] }}]\n')
    assert _lint(tmp_path, text) == ()


@pytest.mark.parametrize(
    "body",
    ['nominal_current = "5 V"\n', 'capacity = "5 A"\n', 'voltage = [{ nom = "5 A" }]\n', 'fault_current = [{ max = "5 V", at = ["DC"] }]\n'],
)
def test_an_operating_field_takes_its_unit_kind(tmp_path, body):
    found = _one(tmp_path, "function.operating", body, "RATING_VALUE_INVALID")
    assert "takes a" in found.message


@pytest.mark.parametrize("table", list(_TABLES))
def test_unknown_field_is_refused(tmp_path, table):
    found = _one(tmp_path, table, 'watts = "5"\n', "FIELD_UNKNOWN")
    assert "'watts'" in found.message


def test_operating_field_is_unknown_in_a_rating_table(tmp_path):
    text = _function_with('\n[function.rating]\nnominal_voltage = "24 V"\n')
    assert "FIELD_UNKNOWN" in _codes(tmp_path, text)


@pytest.mark.parametrize("table", list(_TABLES))
def test_bare_float_is_forbidden_and_not_double_reported(tmp_path, table):
    build, _ = _TABLES[table]
    findings = _lint(tmp_path, build(_body("24.5")))
    assert [f.code for f in findings] == ["FLOAT_FORBIDDEN"]


@pytest.mark.parametrize("table", list(_TABLES))
def test_bare_int_is_a_field_type_error_and_not_double_reported(tmp_path, table):
    build, _ = _TABLES[table]
    findings = _lint(tmp_path, build("voltage = 24\n"))
    assert [f.code for f in findings] == ["FIELD_TYPE"]


_INLINE_FUNCTION = """
[[function]]
name = "f1"
kind = "generic"
{inline}
ports = [{{ name = "1", role = "generic" }}]
"""


def test_inline_rating_table_is_reported_at_the_functions_header_line(tmp_path):
    text = _HEAD + _INLINE_FUNCTION.format(inline='rating = { voltage = [{ nom = "0 V", at = ["AC"] }] }')
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
    text = _HEAD.replace("schema = 2\n", "schema = 2\nrating = 5\n") + _FUNCTION
    codes = _codes(tmp_path, text)
    assert "FIELD_TYPE" in codes
    assert "RATING_TABLE_EMPTY" not in codes


# ---- [connection]: the conductors a terminal point takes (R1268) -------------------------------------------------


def test_part_connection_loads_as_the_elecdef_connection_of_the_one_template(tmp_path):
    text = _function_with("\n[connection]\nconductors_per_clamp = 2\n")
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    (facet,) = facets_of(model, BlockFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.block == Connection(conductors_per_clamp=2)
    assert model.origins[facet.id].line == _line_of(text, "[connection]")


def test_demo_twin_terminal_states_two_conductors_and_the_plain_one_states_none():
    model = freeze(fransys_parts.load_path(DEMO))
    templates, mpn = function_templates(model), {p.id: p.mpn for p in parts(model).values()}
    states = {mpn[templates[f.subject].part]: f.block for f in facets_of(model, BlockFacet).values() if isinstance(f.block, Connection)}
    twin = Connection(conductors_per_clamp=2)
    assert states == {"DEMO-TB-2.5-TWIN": twin, "DEMO-TB-FUSE-2.5-TWIN": twin, "DEMO-OVERLOAD-A2": twin}


@pytest.mark.parametrize("table", ["conductors_per_clamp = 0", "conductors_per_clamp = 1.5", 'conductors_per_clamp = "2"', "conductors = 2", ""])
def test_part_connection_refuses_a_bad_table(tmp_path, table):
    findings = _lint(tmp_path, _function_with(f"\n[connection]\n{table}\n"))
    assert any(f.severity is Severity.ERROR for f in findings)
