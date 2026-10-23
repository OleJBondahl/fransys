"""`natural()`: the one home of a symbol's natural size, keepout and step (SYMDEF-SLOTS SS6)."""

import sys

import pytest
from symdef import UnknownSymbolError, body_box, keepout_box, stretch, table

from electrical_symbols import G_PER_MODULE, LIBRARY, Natural, natural

STRETCHABLE = [
    "cable-head",
    "diagram-box",
    "diagram-box-by-others",
    "card",
    "unit-outline",
    "harness-frame",
    "group-frame",
]
ROWS = {"pin-cell": "y", "pin-cell-wide": "y", "cable-column": "x", "contact-row": "y"}
SS5 = [
    *ROWS,
    "cable-head",
    "contact-head",
    "diagram-box",
    "diagram-box-by-others",
    "card",
    "reference-marker",
    "wire-label-frame",
    "unit-outline",
    "harness-frame",
    "group-frame",
    "junction-dot",
]


def g(modules):
    return round(modules * G_PER_MODULE)


@pytest.mark.parametrize("key", SS5)
def test_body_equals_the_body_box_extent_in_grid_units(key):
    box = body_box(LIBRARY.get(key))
    assert natural(key).body == (g(box.max.x - box.min.x), g(box.max.y - box.min.y))


@pytest.mark.parametrize("key", SS5)
def test_keepout_margins_rebuild_the_keepout_box(key):
    keep = keepout_box(LIBRARY.get(key))
    body = body_box(LIBRARY.get(key))
    left, top, right, bottom = natural(key).keepout
    assert min(left, top, right, bottom) >= 0
    assert (g(body.min.x) - left, g(body.min.y) - top) == (g(keep.min.x), g(keep.min.y))
    assert (g(body.max.x) + right, g(body.max.y) + bottom) == (g(keep.max.x), g(keep.max.y))


def test_keepout_leaves_out_a_slot_beyond_the_body():
    """plc-channel's tag box stands 6 M wide beside its body: symdef 0.22 keeps it out (D101)."""
    assert natural("plc-channel").keepout[0] == 0


@pytest.mark.parametrize("key", STRETCHABLE)
def test_a_stretch_to_the_natural_extent_is_a_no_op(key):
    symbol = LIBRARY.get(key)
    box = body_box(symbol)
    for cut in symbol.stretch:
        extent = box.max.x - box.min.x if cut.axis == "x" else box.max.y - box.min.y
        done = stretch(symbol, cut.axis, extent)
        assert done.elements == symbol.elements
        assert done.ports == symbol.ports
        assert done.slots == symbol.slots


@pytest.mark.parametrize("key", STRETCHABLE)
def test_cuts_are_the_stretch_lines_in_grid_units(key):
    cuts = {s.axis: g(s.at) for s in LIBRARY.get(key).stretch}
    found = natural(key)
    assert (found.cut_x, found.cut_y) == (cuts.get("x"), cuts.get("y"))


@pytest.mark.parametrize(("key", "axis"), ROWS.items())
def test_a_table_is_n_steps_long(key, axis):
    found = natural(key)
    assert found.axis == axis
    built = body_box(table(LIBRARY.get(key), 4, axis))
    extent = built.max.x - built.min.x if axis == "x" else built.max.y - built.min.y
    assert g(extent) == 4 * found.step > 0


def test_a_symbol_that_is_not_a_row_has_no_step_and_no_cut():
    assert natural("make-contact") == Natural(
        natural("make-contact").body, natural("make-contact").keepout, 0, None, None, None
    )


def test_unknown_key_raises():
    with pytest.raises(UnknownSymbolError):
        natural("no-such-symbol")


def test_natural_reads_the_package_library_object():
    """`natural` and the package share one loaded bundle, not two reads of it."""
    assert sys.modules["electrical_symbols.natural"].LIBRARY is LIBRARY
