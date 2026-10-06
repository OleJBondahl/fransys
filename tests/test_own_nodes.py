"""`own_nodes` on the scale fixture (two cabinets, each nesting a board) and eight variations.

Each expected value is one unit's own aspect nodes as node keys (`/`-joined), per unit key
(`/`-joined; the container is `unit`). Every set was checked once against the per-unit scan that
`own_nodes` was at commit 03783d6, before model-0067 part 2 replaced it, and is written out here.
The rule is in `own_nodes`' docstring (I4 R2, F9).
"""

import sys
from pathlib import Path

import pytest

from fransys_model.derive import units
from fransys_model.derive.designation import own_nodes
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab import Unit
from fransys_model.vocab.tables import aspect_nodes
from fransys_model.vocab.tables import units as units_table

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

import own_nodes_models as models  # noqa: E402


def _own_by_unit(model):
    """Every unit's `own_nodes` as `{unit key: sorted node keys}`, keys joined by `/`."""
    nodes = aspect_nodes(model)
    return {
        "/".join(units_table(model)[unit].key): sorted(
            "/".join(nodes[n].key) for n in own_nodes(model, unit)
        )
        for unit in sorted(units(model))
    }


SCALE = {
    "unit": [
        "location/ER",
        "pump1/group/FLD",
        "pump1/io/group/BRD",
        "pump1/location/C1",
        "pump2/group/FLD",
        "pump2/io/group/BRD",
        "pump2/location/C2",
    ],
    "pump1/unit": ["pump1/group/FLD", "pump1/io/group/BRD", "pump1/location/C1"],
    "pump1/io/unit": ["pump1/io/group/BRD"],
    "pump2/unit": ["pump2/group/FLD", "pump2/io/group/BRD", "pump2/location/C2"],
    "pump2/io/unit": ["pump2/io/group/BRD"],
}


def test_the_scale_fixture():
    assert _own_by_unit(models.scale_model()) == SCALE


def test_an_item_in_no_unit_at_er_leaves_er_owned_by_no_unit():
    without_er = {**SCALE, "unit": [k for k in SCALE["unit"] if k != "location/ER"]}
    assert _own_by_unit(models.item_in_no_unit_at_er()) == without_er


def test_f9_an_item_in_no_unit_does_not_unown_a_function_node():
    assert _own_by_unit(models.item_in_no_unit_in_fld()) == SCALE


def test_f9_an_item_of_another_unit_unowns_a_function_node():
    """The container's item in `pump1`'s `=FLD` group: `pump1` loses it, `pump2` keeps its own."""
    expected = {**SCALE, "pump1/unit": ["pump1/io/group/BRD", "pump1/location/C1"]}
    assert _own_by_unit(models.item_of_another_unit_in_fld()) == expected


def test_a_second_placement_that_does_not_win_changes_nothing():
    """`effective_placement` takes the smallest placement id; the strip's own is smaller."""
    assert _own_by_unit(models.x2_placed_twice(second_wins=False)) == SCALE


def test_a_second_placement_that_wins_moves_the_strip_to_c2():
    """`pump1`'s strip `X2` and its terminals now sit at `+C2`, with `pump2`'s items.

    `pump2` no longer owns `+C2`; the only items left at `+C1` are the board's, so `pump1`'s
    board unit owns `+C1`.
    """
    expected = {
        **SCALE,
        "pump1/io/unit": ["pump1/io/group/BRD", "pump1/location/C1"],
        "pump2/unit": ["pump2/group/FLD", "pump2/io/group/BRD"],
    }
    assert _own_by_unit(models.x2_placed_twice(second_wins=True)) == expected


def test_a_node_reached_in_both_aspects_is_owned_only_if_neither_puts_it_outside():
    """`+C1` (unit a's item) has the function node `=P1` as its parent; unit b's item is at `=P1`.

    `=P1` is reached through `+C1`'s chain by a's item and placed at by b's: b's item is outside
    for a, a's item is outside for b, so nobody owns it. `+C1` is a's own alone.
    """
    assert _own_by_unit(models.cross_aspect_nodes()) == {
        "own/unit/a": ["own/node/C1"],
        "own/unit/b": [],
    }


def test_the_items_of_cables_and_harnesses_never_unown_a_location():
    """A top-level cable at `+C1` and a top-level harness's plug at `+C2` leave them unit `u`'s.

    An ordinary item in no unit at `+C3` does un-own it.
    """
    assert _own_by_unit(models.cable_ends_in_a_unit_location()) == {
        "own/unit/u": ["own/node/C1", "own/node/C2"]
    }


def test_units_that_name_each_other_as_parent_own_the_same_nodes():
    """Each unit's subtree holds the other, so an item of either is a member of both.

    Both own `+CX`, `+CY` and `=G`; `+CZ`, where an item in no unit is, is nobody's.
    """
    both = ["own/node/CX", "own/node/CY", "own/node/G"]
    assert _own_by_unit(models.units_naming_each_other_as_parent()) == {
        "own/unit/x": both,
        "own/unit/y": both,
    }


def test_an_unknown_unit_still_raises_schema_error():
    with pytest.raises(SchemaError):
        own_nodes(models.scale_model(), make_id(Unit, ("no", "such")))
