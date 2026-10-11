"""Tests: board netlists, aspect trees and `ext` usage. Plus `schematic_functions`."""

from plant import Plant
from query_builders import (
    make_part,
    reversed_tables,
    with_ext,
)

from fransys_model.derive import (
    board_netlist,
    ext_usage,
)

# -- board_netlist's connected groups (decision model-0042) ------------------------------


def test_ext_usage_counts_top_level_keys_per_kind_sorted_with_subjects_in_id_order() -> None:
    """One row per `(kind, key)`; nested keys are not walked; nothing in `ext` means no row."""
    plant = Plant()
    plant.item("clean", designation="K1")
    made = [plant.item(key, designation=key.upper()) for key in ("i-a", "i-b", "i-c")]
    more = [plant.item(f"i-{n}", designation=f"M{n}") for n in range(8)]
    for item_id in more:
        with_ext(plant, item_id, {"beta": "x"})
    nested = frozendict({"deep": 1})
    with_ext(plant, made[0], {"beta": "x", "nest": nested})
    with_ext(plant, made[1], {"beta": "x", "nest": nested})
    with_ext(plant, made[2], {"alpha": 1})
    part = make_part(plant, "p", "P-1")
    with_ext(plant, part, {"alpha": "y"})
    rows = ext_usage(plant.model())
    assert [(r.kind, r.key, r.count) for r in rows] == [
        ("item", "alpha", 1),
        ("item", "beta", 10),
        ("item", "nest", 2),
        ("part", "alpha", 1),
    ]
    assert rows[1].subjects == tuple(sorted((*made[:2], *more)))
    assert rows[0].subjects == (made[2],)
    assert rows[3].subjects == (part,)
    model = plant.model()
    assert ext_usage(reversed_tables(model)) == rows


# -- schematic_functions (model-0039) -----------------------------------------------


# -- schematic_functions and is_sole_unit_root (board-unit ruling, model-0041) --

_BOARD_UNIT_FUNCTION_COUNT = 2  # the board's own edge connector plus the relay coil


# -- effective_placement (model-0040) ------------------------------


def test_board_netlist_names_an_undeclared_group_by_its_lowest_pin_in_natural_order() -> None:
    """`K1` has pins `10` and `2` in one group: the name takes `2`, not the plain-string `10`."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    hub = plant.port(plant.function(x1, "x1"), "1")
    k1_fn = plant.function(k1, "coil")
    plant.wire(plant.port(k1_fn, "10"), hub, key="w10")
    plant.wire(plant.port(k1_fn, "2"), hub, key="w2")
    (net,) = board_netlist(plant.model(), board).nets
    assert net.name == "Net-(K1-2)"
