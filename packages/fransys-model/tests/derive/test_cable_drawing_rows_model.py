"""The cable drawing's end rows and drawn pins (CT5, CD5, CD6, Q9)."""

from typing import Any

import pytest
from cable_drawing_builders import cable, device
from connector_builders import make_connector
from plant import Plant
from query_builders import make_core, make_pin, make_terminal

from fransys_model.derive.cable_drawing import (
    DrawnPin,
    block_cables,
    drawn_pins,
    end_rows,
    row_links,
)


def test_a_unit_end_stands_on_top_of_one_in_no_unit() -> None:
    """CD5 'inside': `X1` in a unit is on top, `M1` in none at the bottom."""
    plant = Plant()
    unit = plant.unit("u")
    w1 = cable(plant, "w1", "W1")
    m1, m = device(plant, "m1", "M1", "1")
    x1, x = device(plant, "x1", "X1", "1", unit=unit)
    make_core(plant, "c1", w1, (m["1"], x["1"]), index=1)
    assert end_rows(plant.model(), w1, None) == ((x1,), (m1,))


def test_with_no_end_in_a_unit_the_lowest_ranked_end_seeds_the_top() -> None:
    """Cores 1 (`Z1`-`Y1`), 2 (`M1`-`Y1`): `M1` ranks first and tops its group; `Z1` joins it."""
    plant = Plant()
    w1 = cable(plant, "w1", "W1")
    m1, m = device(plant, "m1", "M1", "1")
    y1, y = device(plant, "y1", "Y1", "1", "2")
    z1, z = device(plant, "z1", "Z1", "1")
    make_core(plant, "c1", w1, (z["1"], y["1"]), index=1)
    make_core(plant, "c2", w1, (m["1"], y["2"]), index=2)
    assert end_rows(plant.model(), w1, None) == ((z1, m1), (y1,))


def test_with_every_end_in_a_unit_only_the_lowest_ranked_end_stands_on_top() -> None:
    """Absolute reading, both ends inside: `A1` on top alone, `B1` below."""
    plant = Plant()
    unit = plant.unit("u")
    w1 = cable(plant, "w1", "W1")
    b1, b = device(plant, "b1", "B1", "1", unit=unit)
    a1, a = device(plant, "a1", "A1", "1", unit=unit)
    make_core(plant, "c1", w1, (b["1"], a["1"]), index=1)
    assert end_rows(plant.model(), w1, None) == ((a1,), (b1,))


@pytest.mark.parametrize(("first", "second"), [("X1", "X2"), ("X9", "X2")])
def test_a_fan_in_row_runs_by_lowest_core_key_not_by_rank(first: str, second: str) -> None:
    """Cores 1, 2 land on `first`, core 3 on `second` (in a unit), `M1` outside: top by core."""
    plant = Plant()
    unit = plant.unit("u")
    w5 = cable(plant, "w5", "W5")
    m1, m = device(plant, "m1", "M1", "1", "2", "3")
    one, p = device(plant, "one", first, "1", "2", unit=unit)
    two, q = device(plant, "two", second, "1", unit=unit)
    make_core(plant, "c1", w5, (p["1"], m["1"]), index=1)
    make_core(plant, "c2", w5, (p["2"], m["2"]), index=2)
    make_core(plant, "c3", w5, (q["1"], m["3"]), index=3)
    assert end_rows(plant.model(), w5, None) == ((one, two), (m1,))


def test_in_a_units_reading_its_nested_units_end_is_inside_and_a_blank_end_is_below() -> None:
    """`Z1` in nested `sub` tops `B1` in `top` only in `sub`'s reading; `M1` in no unit is below."""
    plant = Plant()
    top = plant.unit("top")
    sub = plant.unit("sub", parent=top)
    w1 = cable(plant, "w1", "W1", unit=sub)
    w2 = cable(plant, "w2", "W2", unit=sub)
    z1, z = device(plant, "z1", "Z1", "1", "2", unit=sub)
    b1, b = device(plant, "b1", "B1", "1", unit=top)
    m1, m = device(plant, "m1", "M1", "1")
    make_core(plant, "c1", w1, (z["1"], b["1"]), index=1)
    make_core(plant, "c2", w2, (z["2"], m["1"]), index=1)
    w3 = cable(plant, "w3", "W3", unit=top)
    make_core(plant, "c3", w3, (z["1"], b["1"]), index=1)
    model = plant.model()
    assert end_rows(model, w1, sub) == ((z1,), (b1,))
    assert end_rows(model, w3, top) == ((b1,), (z1,))
    assert end_rows(model, w2, sub) == ((z1,), (m1,))


def test_an_item_two_cables_land_on_is_one_end_and_a_cable_with_no_cores_has_no_ends() -> None:
    """Q9: `W1`, `W2` of a harness both land on `H1`: one end. A cable with no cores: `((), ())`."""
    plant = Plant()
    harness = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=harness)
    w2 = cable(plant, "w2", "W2", parent=harness)
    h1, h = device(plant, "h1", "H1", "1", "2")
    s1, s = device(plant, "s1", "S1", "1")
    s2, t = device(plant, "s2", "S2", "1")
    make_core(plant, "c1", w1, (h["1"], s["1"]), index=1)
    make_core(plant, "c2", w2, (h["2"], t["1"]), index=1)
    bare = cable(plant, "bare", "W9")
    model = plant.model()
    top, bottom = end_rows(model, harness, None)
    assert sorted(top + bottom) == sorted([h1, s1, s2])
    assert end_rows(model, bare, None) == ((), ())


def test_a_connector_end_shows_landed_pins_in_core_order_then_free_pins_in_pin_order() -> None:
    """Cores on `A1` then `2`: those, then free `1`, `10`; markings are the harness end's."""
    plant = Plant()
    w1 = cable(plant, "w1", "W1")
    h1 = plant.item("h1", designation="H1")
    _, ports = make_connector(plant, ("h1", "P1"), ("1", "2", "10", "A1"))
    far = [make_pin(plant, f"far{n}", f"F{n}") for n in (1, 2)]
    c1 = make_core(plant, "c1", w1, (ports["A1"], far[0]), index=1)
    c2 = make_core(plant, "c2", w1, (ports["2"], far[1]), index=2)
    model = plant.model()
    pins = drawn_pins(model, w1, h1, None)
    assert pins == (
        DrawnPin(port=ports["A1"], marking="A1", landed=True, cores=(c1,)),
        DrawnPin(port=ports["2"], marking="2", landed=True, cores=(c2,)),
        DrawnPin(port=ports["1"], marking="1", landed=False),
        DrawnPin(port=ports["10"], marking="10", landed=False),
    )
    (row,) = block_cables(model, w1, None)
    (end,) = [e for e in row.ends if e.item == h1]
    assert {(p.port, p.marking) for p in end.pins} == {(p.port, p.marking) for p in pins[:2]}


def test_a_pin_holds_one_place_per_core_landing_on_it_in_core_key_order() -> None:
    """P1: cores 3 and 1 of `W1` and core 2 of `W2` land on `A1`: three places, keyed 1, 3, W2's.

    A core with both ends on `A1` counts once, and a pin one core lands on holds one place.
    """
    plant = Plant()
    harness = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=harness)
    w2 = cable(plant, "w2", "W2", parent=harness)
    h1 = plant.item("h1", designation="H1")
    _, ports = make_connector(plant, ("h1", "P1"), ("A1", "B2"))
    far = [make_pin(plant, f"far{n}", f"F{n}") for n in range(4)]
    c3 = make_core(plant, "c3", w1, (ports["A1"], far[0]), index=3)
    c1 = make_core(plant, "c1", w1, (ports["A1"], far[1]), index=1)
    c4 = make_core(plant, "c4", w1, (ports["B2"], far[2]), index=4)
    c5 = make_core(plant, "c5", w2, (far[3], ports["A1"]), index=2)
    pins = drawn_pins(plant.model(), harness, h1, None)
    assert [(p.marking, p.cores) for p in pins] == [("A1", (c1, c3, c5)), ("B2", (c4,))]


def test_a_terminal_strip_end_shows_only_the_landed_pin_marked_group_colon_index() -> None:
    """Strip `X1`, `L:1` landed and `L:2` not: one pin marked `L:1`, as the harness end marks it."""
    plant = Plant()
    w1 = cable(plant, "w1", "W1")
    x1 = plant.item("x1", designation="X1")
    landed = make_terminal(plant, "x1", "t1", group="L", index=1)
    make_terminal(plant, "x1", "t2", group="L", index=2)
    far = make_pin(plant, "far", "F1")
    c1 = make_core(plant, "c1", w1, (landed.external, far), index=1)
    model = plant.model()
    assert drawn_pins(model, w1, x1, None) == (
        DrawnPin(port=landed.external, marking="L:1", landed=True, cores=(c1,)),
    )
    (row,) = block_cables(model, w1, None)
    (end,) = [e for e in row.ends if e.item == x1]
    assert [p.marking for p in end.pins] == ["L:1"]


def test_a_pin_landed_by_either_cable_of_a_harness_is_landed_at_its_lowest_core_key() -> None:
    """Q9: `W1` lands `A1`, `1`, `2` (cores 1-3); `W2` lands `10` (core 2) and `2` (core 5)."""
    plant = Plant()
    harness = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=harness)
    w2 = cable(plant, "w2", "W2", parent=harness)
    h1 = plant.item("h1", designation="H1")
    _, ports = make_connector(plant, ("h1", "P1"), ("1", "2", "10", "A1", "B2"))
    far = [make_pin(plant, f"far{n}", f"F{n}") for n in range(5)]
    make_core(plant, "c1", w1, (ports["A1"], far[0]), index=1)
    make_core(plant, "c2", w1, (ports["1"], far[1]), index=2)
    make_core(plant, "c3", w1, (ports["2"], far[2]), index=3)
    make_core(plant, "c4", w2, (ports["10"], far[3]), index=2)
    make_core(plant, "c5", w2, (ports["2"], far[4]), index=5)
    pins = drawn_pins(plant.model(), harness, h1, None)
    assert [(p.marking, p.landed) for p in pins] == [
        ("A1", True),
        ("1", True),
        ("2", True),
        ("10", True),
        ("B2", False),
    ]


def _two_unit_harness(plant: Plant):
    """A harness `WH` of `W1` in unit `u1` and `W2` in `u2`, each on its own device pair."""
    u1, u2 = plant.unit("u1"), plant.unit("u2")
    harness = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=harness, unit=u1)
    w2 = cable(plant, "w2", "W2", parent=harness, unit=u2)
    a1, a = device(plant, "a1", "A1", "1", unit=u1)
    b1, b = device(plant, "b1", "B1", "1", unit=u1)
    a2, c = device(plant, "a2", "A2", "1", unit=u2)
    b2, d = device(plant, "b2", "B2", "1", unit=u2)
    make_core(plant, "c1", w1, (a["1"], b["1"]), index=1)
    make_core(plant, "c2", w2, (c["1"], d["1"]), index=1)
    return harness, w1, w2, u1, u2, (a1, b1, a2, b2)


def test_a_units_block_holds_only_the_cables_of_that_unit_and_the_absolute_one_both() -> None:
    """A harness with two cables in two units: each unit's block has its own, the absolute both."""
    plant = Plant()
    harness, w1, w2, u1, u2, (a1, b1, a2, b2) = _two_unit_harness(plant)
    model = plant.model()
    assert [c.cable for c in block_cables(model, harness, u1)] == [w1]
    assert [c.cable for c in block_cables(model, harness, u2)] == [w2]
    assert [c.cable for c in block_cables(model, harness, None)] == [w1, w2]
    assert sorted(sum(end_rows(model, harness, u1), ())) == sorted([a1, b1])
    assert sorted(sum(end_rows(model, harness, u2), ())) == sorted([a2, b2])


def test_pins_are_drawn_from_the_cables_of_the_blocks_own_reading() -> None:
    """`W1`, `W2` in unit `u`, `W3` in none, all on `H1`: `u` draws only the pins of `W1`, `W2`."""
    plant = Plant()
    unit = plant.unit("u")
    harness = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=harness, unit=unit)
    w2 = cable(plant, "w2", "W2", parent=harness, unit=unit)
    other = cable(plant, "w3", "W3", parent=harness)
    h1, h = device(plant, "h1", "H1", "1", "2", "3", unit=unit)
    far = [make_pin(plant, f"far{n}", f"F{n}") for n in range(3)]
    make_core(plant, "c1", w2, (h["2"], far[0]), index=1)
    make_core(plant, "c2", w1, (h["1"], far[1]), index=1)
    make_core(plant, "c3", other, (h["3"], far[2]), index=1)
    model = plant.model()
    pins = {
        r: [p.port for p in drawn_pins(model, harness, h1, r) if p.landed] for r in (unit, None)
    }
    assert pins[unit] == [h["1"], h["2"]]
    assert pins[None] == [h["1"], h["2"], h["3"]]


def _ring(*ends: str) -> tuple[Plant, dict[str, Any]]:
    """Cable `W1` with a core per consecutive pair of `ends`, the last joining back."""
    plant = Plant()
    w1 = cable(plant, "w1", "W1")
    made = {name: device(plant, name.lower(), name, "1", "2") for name in ends}
    cores = []
    for n, name in enumerate(ends):
        other = ends[(n + 1) % len(ends)]
        pair = (made[name][1]["1"], made[other][1]["2"])
        cores.append(make_core(plant, f"c{n}", w1, pair, index=n + 1))
    return plant, {"w1": w1, "cores": cores, **{name: made[name][0] for name in ends}}


def test_a_daisy_chain_colours_its_ends_in_two_rows() -> None:
    """CT5-4 Q1, acceptance 20: cores `X1`-`X2`, `X2`-`X3` put `X1`, `X3` on top, `X2` below."""
    plant = Plant()
    w1, w2 = cable(plant, "w1", "W1"), cable(plant, "w2", "W2")
    x1, a = device(plant, "x1", "X1", "1")
    x2, b = device(plant, "x2", "X2", "1", "2")
    x3, c = device(plant, "x3", "X3", "1")
    make_core(plant, "c1", w1, (a["1"], b["1"]), index=1)
    make_core(plant, "c2", w2, (b["2"], c["1"]), index=1)
    harness = plant.model()
    assert end_rows(harness, w1, None) == ((x1,), (x2,))
    assert end_rows(harness, w2, None) == ((x2,), (x3,))


def test_two_independent_cables_each_seed_their_own_top_end() -> None:
    """Cables `A1`-`B1` and `A2`-`B2` in one harness: `A1`, `A2` on top, `B1`, `B2` below."""
    plant = Plant()
    h = plant.item("wh", designation="WH1")
    w1 = cable(plant, "w1", "W1", parent=h)
    w2 = cable(plant, "w2", "W2", parent=h)
    a1, p = device(plant, "a1", "A1", "1")
    b1, q = device(plant, "b1", "B1", "1")
    a2, r = device(plant, "a2", "A2", "1")
    b2, s = device(plant, "b2", "B2", "1")
    make_core(plant, "c1", w1, (p["1"], q["1"]), index=1)
    make_core(plant, "c2", w2, (r["1"], s["1"]), index=1)
    assert end_rows(plant.model(), h, None) == ((a1, a2), (b1, b2))


def test_a_mixed_group_seeds_on_its_inside_end() -> None:
    """`M1` outside, `X1`, `X2` inside, cores `M1`-`X1`, `X1`-`X2`: `X1` tops; `M1`, `X2` below."""
    plant = Plant()
    unit = plant.unit("u")
    w1 = cable(plant, "w1", "W1")
    m1, m = device(plant, "m1", "M1", "1")
    x1, p = device(plant, "x1", "X1", "1", "2", unit=unit)
    x2, q = device(plant, "x2", "X2", "1", unit=unit)
    make_core(plant, "c1", w1, (m["1"], p["1"]), index=1)
    make_core(plant, "c2", w1, (p["2"], q["1"]), index=2)
    assert end_rows(plant.model(), w1, None) == ((x1,), (m1, x2))


def test_an_odd_ring_draws_two_rows_and_its_highest_keyed_core_is_the_link() -> None:
    """Acceptance 24 (model half): ring `A1`-`B1`-`C1`; core 3 closes it, so core 3 is the link.

    Probe: `_ordered_cores` sorted in reverse key order, so core 1 closes the ring instead.
    """
    plant, ids = _ring("A1", "B1", "C1")
    model = plant.model()
    assert end_rows(model, ids["w1"], None) == ((ids["A1"], ids["C1"]), (ids["B1"],))
    assert row_links(model, ids["w1"], None) == (ids["cores"][2],)


def test_a_looped_core_is_a_link_and_its_item_stands_on_top() -> None:
    """A core with both ends on one item is always a row link (CD5, L1); the item is one end."""
    plant = Plant()
    w1 = cable(plant, "w1", "W1")
    a1, a = device(plant, "a1", "A1", "1", "2")
    core = make_core(plant, "c1", w1, (a["1"], a["2"]), index=1)
    model = plant.model()
    assert end_rows(model, w1, None) == ((a1,), ())
    assert row_links(model, w1, None) == (core,)


def test_a_two_colourable_block_has_no_link() -> None:
    """A daisy chain and an even ring join the rows with every core: no row link (CD5, L1)."""
    plant = Plant()
    w1, w2 = cable(plant, "w1", "W1"), cable(plant, "w2", "W2")
    _, a = device(plant, "x1", "X1", "1")
    _, b = device(plant, "x2", "X2", "1", "2")
    _, c = device(plant, "x3", "X3", "1")
    make_core(plant, "c1", w1, (a["1"], b["1"]), index=1)
    make_core(plant, "c2", w2, (b["2"], c["1"]), index=1)
    assert row_links(plant.model(), w1, None) == ()
    plant, ids = _ring("A1", "B1", "C1", "D1")
    assert row_links(plant.model(), ids["w1"], None) == ()


def test_links_run_in_core_key_order_and_a_five_ring_closes_on_its_last_core() -> None:
    """A ring's closing core 3, then a looped core 4 on its own item: `(core 3, core 4)`."""
    plant, ids = _ring("A1", "B1", "C1")
    _, loop = device(plant, "l1", "L1", "1", "2")
    core = make_core(plant, "loop", ids["w1"], (loop["1"], loop["2"]), index=4)
    assert row_links(plant.model(), ids["w1"], None) == (ids["cores"][2], core)
    plant, ids = _ring("A1", "B1", "C1", "D1", "E1")
    assert row_links(plant.model(), ids["w1"], None) == (ids["cores"][4],)
