"""F8 load values and heat: each key loads, the value rules hold, `POWER_LOSS_TWICE` fires."""

import itertools
from decimal import Decimal

import fransys_parts
import pytest

from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import OperatingFacet, PartRatingFacet, RatingFacet, facets_of

_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_HEAD = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"
"""
_FUNCTION = (
    '\n[[function]]\nname = "f1"\nkind = "load"\nports = [{ name = "1", role = "generic" }]\n'
)
_roots = itertools.count()


def _root(tmp_path, text):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(text)
    return root


def _lint(tmp_path, text):
    return fransys_parts.lint(_root(tmp_path, text))


@pytest.mark.parametrize("key", ["resistance_ohm", "nominal_power_w", "nominal_current_a"])
def test_each_operating_load_value_loads_into_the_record(tmp_path, key):
    text = _HEAD + _FUNCTION + f'\n[function.operating]\nnominal_voltage_v = "24"\n{key} = "1.5"\n'
    model = freeze(fransys_parts.load_path(_root(tmp_path, text)))
    (facet,) = facets_of(model, OperatingFacet).values()
    assert getattr(facet.operating, key) == Decimal("1.5")
    assert facet.operating.nominal_voltage_v == Decimal(24)


def test_power_loss_loads_from_the_part_and_from_a_function_rating(tmp_path):
    part = _HEAD + '\n[rating]\npower_loss_w = "12"\n' + _FUNCTION
    (facet,) = facets_of(
        freeze(fransys_parts.load_path(_root(tmp_path, part))), PartRatingFacet
    ).values()
    assert facet.rating.power_loss_w == Decimal(12)
    function = _HEAD + _FUNCTION + '\n[function.rating]\npower_loss_w = "3.5"\n'
    (rated,) = facets_of(
        freeze(fransys_parts.load_path(_root(tmp_path, function))), RatingFacet
    ).values()
    assert rated.rating.power_loss_w == Decimal("3.5")


@pytest.mark.parametrize("value", ["0", "-1", "1e3", "abc"])
def test_a_rating_power_loss_must_be_a_positive_plain_decimal(tmp_path, value):
    text = _HEAD + f'\n[rating]\npower_loss_w = "{value}"\n' + _FUNCTION
    assert {f.code for f in _lint(tmp_path, text)} == {"RATING_VALUE_INVALID"}


@pytest.mark.parametrize("key", ["resistance_ohm", "nominal_power_w", "nominal_current_a"])
def test_an_operating_load_value_may_be_zero_but_not_negative(tmp_path, key):
    zero = _HEAD + _FUNCTION + f'\n[function.operating]\n{key} = "0"\n'
    assert _lint(tmp_path, zero) == ()
    negative = _HEAD + _FUNCTION + f'\n[function.operating]\n{key} = "-2"\n'
    assert {f.code for f in _lint(tmp_path, negative)} == {"RATING_VALUE_INVALID"}


def test_power_loss_twice_fires_when_the_part_and_a_function_both_state_it(tmp_path):
    both = _HEAD + '\n[rating]\npower_loss_w = "12"\n' + _FUNCTION
    both += '\n[function.rating]\npower_loss_w = "3"\n'
    (found,) = [f for f in _lint(tmp_path, both) if f.code == "POWER_LOSS_TWICE"]
    assert found.severity is Severity.ERROR


def test_power_loss_stated_once_is_clean(tmp_path):
    part_only = _HEAD + '\n[rating]\npower_loss_w = "12"\n' + _FUNCTION
    function_only = _HEAD + _FUNCTION + '\n[function.rating]\npower_loss_w = "3"\n'
    other_rating = _HEAD + '\n[rating]\npower_loss_w = "12"\n' + _FUNCTION
    other_rating += '\n[function.rating]\nvoltage_ac_v = "230"\n'
    for text in (part_only, function_only, other_rating):
        assert _lint(tmp_path, text) == ()
