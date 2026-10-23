"""`power_symbol_key`: the one home of the power-kind-to-symbol-key table (es-0080)."""

import pytest

from electrical_symbols import LIBRARY, SymdefError, power_symbol_key

KEYS = {"supply": "power-supply", "ground": "ground", "pe": "protective-earth"}


@pytest.mark.parametrize(("kind", "key"), KEYS.items())
def test_each_kind_has_its_key(kind, key):
    assert power_symbol_key(kind) == key


@pytest.mark.parametrize("key", KEYS.values())
def test_each_key_is_a_library_symbol(key):
    assert LIBRARY.get(key) is not None


def test_an_unknown_kind_raises_naming_it():
    with pytest.raises(SymdefError, match="'none'"):
        power_symbol_key("none")
