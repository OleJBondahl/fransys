"""The three current fields in a part file (decision model-0088, parts-0004, parts-0006).

`min_breaking_current_a` sits in `[rating]` and `[function.rating]` (positive only);
`max_current_ac_a` and `max_current_dc_a` sit in `[function.operating]` (zero allowed, no
negative). No key is wired by hand: `RATING_FIELDS` and `OPERATING_FIELDS` are built from the
model's `Rating` and `Operating`, so these tests are the proof that they are accepted and that
the one value rule applies to them.
"""

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

_BUILD = {
    "rating": lambda body: _HEAD + f"\n[rating]\n{body}" + _FUNCTION,
    "function.rating": lambda body: _HEAD + _FUNCTION + f"\n[function.rating]\n{body}",
    "function.operating": lambda body: _HEAD + _FUNCTION + f"\n[function.operating]\n{body}",
}


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


def test_min_breaking_current_loads_from_the_function_rating(tmp_path):
    model = _model(tmp_path, _BUILD["function.rating"]('min_breaking_current_a = "4000"\n'))
    (facet,) = facets_of(model, RatingFacet).values()
    assert facet.subject == make_id(FunctionTemplate, _FUNCTION_KEY)
    assert facet.rating.min_breaking_current_a == Decimal(4000)
    assert isinstance(facet.rating.min_breaking_current_a, Decimal)
    assert facet.rating.current_dc_a is None


def test_min_breaking_current_loads_from_the_part_rating(tmp_path):
    model = _model(tmp_path, _BUILD["rating"]('min_breaking_current_a = "0.5"\n'))
    (facet,) = facets_of(model, PartRatingFacet).values()
    assert facet.subject == make_id(Part, _PART_KEY)
    assert facet.rating.min_breaking_current_a == Decimal("0.5")


def test_max_currents_load_from_the_function_operating(tmp_path):
    body = 'max_current_ac_a = "63"\nmax_current_dc_a = "186"\n'
    model = _model(tmp_path, _BUILD["function.operating"](body))
    (facet,) = facets_of(model, OperatingFacet).values()
    assert facet.operating.max_current_ac_a == Decimal(63)
    assert facet.operating.max_current_dc_a == Decimal(186)
    assert isinstance(facet.operating.max_current_dc_a, Decimal)
    assert facet.operating.nominal_voltage_v is None


@pytest.mark.parametrize("field", ["max_current_ac_a", "max_current_dc_a"])
@pytest.mark.parametrize("zero", ["0", "0.0"])
def test_a_zero_max_current_lints_clean_and_loads_as_zero(tmp_path, field, zero):
    text = _BUILD["function.operating"](f'{field} = "{zero}"\n')
    assert _lint(tmp_path, text) == ()
    (facet,) = facets_of(_model(tmp_path, text), OperatingFacet).values()
    assert getattr(facet.operating, field) == Decimal(0)


@pytest.mark.parametrize("field", ["max_current_ac_a", "max_current_dc_a"])
@pytest.mark.parametrize("negative", ["-1", "-0.5", "-0"])
def test_a_negative_max_current_is_refused(tmp_path, field, negative):
    (found,) = _lint(tmp_path, _BUILD["function.operating"](f'{field} = "{negative}"\n'))
    assert found.code == "RATING_VALUE_INVALID"
    assert found.severity is Severity.ERROR
    assert f"function.operating.{field}" in found.message
    assert "0 or more" in found.message


@pytest.mark.parametrize("table", ["rating", "function.rating"])
@pytest.mark.parametrize("bad", ["0", "0.0", "-1", "abc"])
def test_a_zero_or_bad_min_breaking_current_is_refused(tmp_path, table, bad):
    (found,) = _lint(tmp_path, _BUILD[table](f'min_breaking_current_a = "{bad}"\n'))
    assert found.code == "RATING_VALUE_INVALID"
    assert found.severity is Severity.ERROR
    assert f"{table}.min_breaking_current_a" in found.message


@pytest.mark.parametrize("table", ["rating", "function.rating"])
def test_a_positive_min_breaking_current_lints_clean(tmp_path, table):
    assert _lint(tmp_path, _BUILD[table]('min_breaking_current_a = "4000"\n')) == ()


def test_each_new_key_is_unknown_in_the_other_kind_of_table(tmp_path):
    """`min_breaking_current_a` is a rating field only; the two max currents operating only."""
    wrong = (
        ("function.operating", 'min_breaking_current_a = "5"\n'),
        ("function.rating", 'max_current_dc_a = "5"\n'),
        ("rating", 'max_current_ac_a = "5"\n'),
    )
    for table, body in wrong:
        (found,) = _lint(tmp_path, _BUILD[table](body))
        assert found.code == "FIELD_UNKNOWN"


def test_demo_fuse_and_string_load_the_new_values():
    model = freeze(fransys_parts.load_path(DEMO))
    fuse = make_id(FunctionTemplate, ("part", "Demo", "DEMO-FUSE-ABAT", "function", "element"))
    (rating,) = [f for f in facets_of(model, RatingFacet).values() if f.subject == fuse]
    assert rating.rating.voltage_dc_v == Decimal(1500)
    assert rating.rating.current_dc_a == Decimal(400)
    assert rating.rating.min_breaking_current_a == Decimal(4000)

    string = make_id(FunctionTemplate, ("part", "Demo", "DEMO-STRING-864V", "function", "string"))
    (operating,) = [f for f in facets_of(model, OperatingFacet).values() if f.subject == string]
    assert operating.operating.nominal_voltage_v == Decimal(864)
    assert operating.operating.max_voltage_v == Decimal("985.5")
    assert operating.operating.max_current_dc_a == Decimal(186)
    assert operating.operating.max_current_ac_a is None
