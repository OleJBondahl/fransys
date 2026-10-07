"""Breaking points and fault current in a part file (decision parts-0015, RATINGS-3 R1, R2)."""

import itertools
from decimal import Decimal

import fransys_parts
import pytest

from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import (
    BreakingPoint,
    OperatingFacet,
    PartRatingFacet,
    RatingFacet,
    facets_of,
)

_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
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
_roots = itertools.count()
_DC = 'breaking_dc = [{ voltage_v = "1000", current_a = "15000", time_constant_ms = "15" }]\n'
_POINT = BreakingPoint(
    voltage_v=Decimal(1000), current_a=Decimal(15000), time_constant_ms=Decimal(15)
)


def _root(tmp_path, text):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(text)
    return root


def _lint(tmp_path, text):
    return fransys_parts.lint(_root(tmp_path, text))


def _model(tmp_path, text):
    return freeze(fransys_parts.load_path(_root(tmp_path, text)))


def test_a_part_rating_loads_its_breaking_point(tmp_path):
    (facet,) = facets_of(
        _model(tmp_path, _HEAD + "\n[rating]\n" + _DC + _FUNCTION), PartRatingFacet
    ).values()
    assert facet.rating.breaking_dc == (_POINT,)
    assert facet.rating.breaking_ac == ()


def test_a_function_rating_loads_ac_and_dc_points(tmp_path):
    body = 'breaking_ac = [{ voltage_v = "400", current_a = "10000" }]\n' + _DC
    (facet,) = facets_of(
        _model(tmp_path, _HEAD + _FUNCTION + "\n[function.rating]\n" + body), RatingFacet
    ).values()
    assert facet.rating.breaking_dc == (_POINT,)
    assert facet.rating.breaking_ac == (
        BreakingPoint(voltage_v=Decimal(400), current_a=Decimal(10000)),
    )


def test_an_operating_table_loads_its_fault_fields(tmp_path):
    body = 'fault_current_dc_a = "6000"\nfault_time_constant_ms = "2"\nfault_current_ac_a = "9"\n'
    (facet,) = facets_of(
        _model(tmp_path, _HEAD + _FUNCTION + "\n[function.operating]\n" + body), OperatingFacet
    ).values()
    assert facet.operating.fault_current_dc_a == Decimal(6000)
    assert facet.operating.fault_time_constant_ms == Decimal(2)
    assert facet.operating.fault_current_ac_a == Decimal(9)


_P = '{ voltage_v = "1000", current_a = "15000" }'
_BAD = {
    "empty list": "breaking_dc = []",
    "not a table": 'breaking_dc = ["15000"]',
    "voltage missing": 'breaking_dc = [{ current_a = "15000" }]',
    "current missing": 'breaking_dc = [{ voltage_v = "1000" }]',
    "unknown key": 'breaking_dc = [{ voltage_v = "1", current_a = "2", extra = "3" }]',
    "not a string": "breaking_dc = [{ voltage_v = 1000, current_a = 15 }]",
    "zero current": 'breaking_dc = [{ voltage_v = "1000", current_a = "0" }]',
    "exponent": 'breaking_dc = [{ voltage_v = "1e3", current_a = "15" }]',
    "zero time constant": (
        'breaking_dc = [{ voltage_v = "1", current_a = "2", time_constant_ms = "0" }]'
    ),
    "time constant on ac": (
        'breaking_ac = [{ voltage_v = "1", current_a = "2", time_constant_ms = "3" }]'
    ),
    "second point bad": f'breaking_dc = [{_P}, {{ voltage_v = "1" }}]',
}


@pytest.mark.parametrize("table", ["rating", "function.rating"])
@pytest.mark.parametrize("case", sorted(_BAD))
def test_a_malformed_breaking_point_is_rating_value_invalid(tmp_path, table, case):
    text = (
        _HEAD + f"\n[rating]\n{_BAD[case]}\n" + _FUNCTION
        if table == "rating"
        else _HEAD + _FUNCTION + f"\n[function.rating]\n{_BAD[case]}\n"
    )
    findings = _lint(tmp_path, text)
    assert findings
    assert {f.code for f in findings} == {"RATING_VALUE_INVALID"}
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f"{table}.breaking_" in f.message for f in findings)


def test_the_message_names_the_field_and_point_index(tmp_path):
    text = _HEAD + f'\n[rating]\nbreaking_dc = [{_P}, {{ voltage_v = "1" }}]\n' + _FUNCTION
    (found,) = _lint(tmp_path, text)
    assert "rating.breaking_dc[1] has no key 'current_a'" in found.message


def test_a_clean_point_list_lints_clean(tmp_path):
    assert _lint(tmp_path, _HEAD + "\n[rating]\n" + _DC + _FUNCTION) == ()


def test_breaking_points_under_operating_are_an_unknown_field_only(tmp_path):
    # An empty list would be RATING_VALUE_INVALID under a rating; here it is unknown only.
    text = _HEAD + _FUNCTION + "\n[function.operating]\nbreaking_dc = []\n"
    assert {f.code for f in _lint(tmp_path, text)} == {"FIELD_UNKNOWN"}


def test_a_float_in_a_point_is_float_forbidden_only(tmp_path):
    text = _HEAD + '\n[rating]\nbreaking_dc = [{ voltage_v = "1", current_a = 1.5 }]\n' + _FUNCTION
    assert {f.code for f in _lint(tmp_path, text)} == {"FLOAT_FORBIDDEN"}
