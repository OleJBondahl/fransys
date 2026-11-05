"""`geometry.symbols`.

These run against the real symbol library: the adapter is the one place it is used.
"""

import dataclasses

import pytest

from electrical_symbols import MARKER_SLOT, MARKER_TURNED
from fransys_layout.geometry import (
    Facing,
    Orientation,
    SlotSide,
    UnknownSymbolError,
    symbol_geometry,
)


def test_unknown_symbol_raises_and_names_the_key() -> None:
    """An unknown key raises; no placeholder geometry is returned."""
    with pytest.raises(UnknownSymbolError) as excinfo:
        symbol_geometry("no-such-symbol")
    assert excinfo.value.key == "no-such-symbol"


def _leaves(obj: object) -> list[object]:
    if isinstance(obj, tuple):
        return [leaf for item in obj for leaf in _leaves(item)]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return [leaf for f in dataclasses.fields(obj) for leaf in _leaves(getattr(obj, f.name))]
    return [obj]


@pytest.mark.rule("PAGE-FRAME")
def test_the_turned_marker_reads_and_its_corner_slot_turns_with_it_but_keeps_its_box_size() -> None:
    """R1592: the turned marker's slot is a corner (SE at R0) that turns with the symbol; its box is never rotated."""
    turn = {
        Orientation.R0: SlotSide.SE,
        Orientation.R90: SlotSide.SW,
        Orientation.R180: SlotSide.NW,
        Orientation.R270: SlotSide.NE,
        Orientation.MR0: SlotSide.SW,
        Orientation.MR90: SlotSide.NW,
        Orientation.MR180: SlotSide.NE,
        Orientation.MR270: SlotSide.SE,
    }
    for orientation in Orientation:
        (slot,) = symbol_geometry(MARKER_TURNED, orientation=orientation).slots
        assert (slot.slot, slot.side) == (MARKER_SLOT, turn[orientation])
        assert (slot.box.width, slot.box.height) == (8, 14)


def test_a_slot_on_a_side_keeps_its_facing_name() -> None:
    sides = {s.side for s in symbol_geometry("coil").slots} - {SlotSide.C}
    assert sides
    assert {side.name for side in sides} <= {facing.name for facing in Facing}
