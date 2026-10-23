"""The marker table names real library symbols that hold the text slot (es-0082)."""

import pytest

from electrical_symbols import LIBRARY, MARKER_FACING, MARKER_SLOT, SymdefError, marker_symbol


@pytest.mark.parametrize("kind", ["tag", "arrow", "star", "stub", "copy"])
def test_every_kind_names_a_library_symbol_with_the_text_slot(kind: str) -> None:
    symbol = LIBRARY.symbols[marker_symbol(kind)]
    assert MARKER_SLOT in {slot.id for slot in symbol.slots}


def test_an_unknown_kind_is_refused_naming_the_fix() -> None:
    with pytest.raises(SymdefError, match="add its row"):
        marker_symbol("loop")


def test_the_four_turns_are_distinct() -> None:
    assert sorted(MARKER_FACING.values()) == ["R0", "R180", "R270", "R90"]
