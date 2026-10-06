"""Zero in the rating tables: an operating value may be 0, a rating value may not (parts-0006)."""

import itertools
from decimal import Decimal

import fransys_parts
import pytest

from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import OperatingFacet, facets_of

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


def _root(tmp_path, text):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(text)
    return root


def _lint(tmp_path, text):
    return fransys_parts.lint(_root(tmp_path, text))


_BUILD = {
    "rating": lambda body: _HEAD + f"\n[rating]\n{body}" + _FUNCTION,
    "function.rating": lambda body: _HEAD + _FUNCTION + f"\n[function.rating]\n{body}",
    "function.operating": lambda body: _HEAD + _FUNCTION + f"\n[function.operating]\n{body}",
}


def _refusal(tmp_path, table, body):
    (found,) = _lint(tmp_path, _BUILD[table](body))
    assert found.code == "RATING_VALUE_INVALID"
    assert found.severity is Severity.ERROR
    assert table in found.message
    return found


@pytest.mark.parametrize("zero", ["0", "0.0"])
def test_zero_operating_value_lints_clean(tmp_path, zero):
    assert _lint(tmp_path, _BUILD["function.operating"](f'min_voltage_v = "{zero}"\n')) == ()


def test_zero_operating_value_loads_as_decimal_zero(tmp_path):
    text = _BUILD["function.operating"]('min_voltage_v = "0"\nmax_voltage_v = "30"\n')
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    (facet,) = facets_of(model, OperatingFacet).values()
    assert facet.operating.min_voltage_v == Decimal(0)
    assert facet.operating.max_voltage_v == Decimal(30)


@pytest.mark.parametrize("negative", ["-1", "-0.5", "-0"])
def test_negative_operating_value_is_refused(tmp_path, negative):
    found = _refusal(tmp_path, "function.operating", f'min_voltage_v = "{negative}"\n')
    assert "0 or more" in found.message


@pytest.mark.parametrize("table", ["rating", "function.rating"])
@pytest.mark.parametrize("zero", ["0", "0.0"])
def test_zero_rating_value_is_refused(tmp_path, table, zero):
    found = _refusal(tmp_path, table, f'voltage_ac_v = "{zero}"\n')
    assert "positive number" in found.message


def test_rating_value_invalid_names_its_own_header_line(tmp_path):
    text = _BUILD["rating"]('voltage_ac_v = "0"\n')
    header_line = next(
        i for i, line in enumerate(text.splitlines(), start=1) if line.strip() == "[rating]"
    )
    assert header_line != 1
    found = _refusal(tmp_path, "rating", 'voltage_ac_v = "0"\n')
    assert found.message.startswith(f"parts/p.toml:{header_line}:")
