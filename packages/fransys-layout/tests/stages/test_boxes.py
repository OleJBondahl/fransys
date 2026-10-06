"""The generic-box rules (D8): hand-made values, no model and no engine."""

from dataclasses import replace

from samples import drawn, function_spec, hid

from fransys_layout.geometry import GENERIC_BOX_KEY, SymbolGeometry, generic_box_geometry
from fransys_layout.stages import DrawnFunction, DrawnPort
from fransys_layout.stages.boxes import port_ranks, potential_sides


def _port(function: int, which: int):
    return hid("port", function * 10 + which)


def _box(number: int, geometry: SymbolGeometry) -> DrawnFunction:
    """Function `number` drawn as a generic box: port `13` at `a`, `14` at `b`, and so on."""
    ports = tuple(
        DrawnPort(port=_port(number, i + 1), symbol_port=port.name)
        for i, port in enumerate(geometry.ports)
    )
    return replace(drawn(number), geometry=geometry, ports=ports)


# --- port_ranks ----------------------------------------------------------------------


def test_a_port_takes_the_rank_the_model_shipped_and_an_unranked_port_is_out() -> None:
    """Ports with a `rank` on their `PortSpec` are ranked; one with `None` is left out."""
    # UNDO: stages/boxes.py:port_ranks, drop the `if p.rank is not None` filter (None is ranked)
    specs = tuple(function_spec(n) for n in (1, 2))
    first, second = specs[0].ports
    ranked = replace(specs[0], ports=(replace(first, rank=0), replace(second, rank=1)))
    bare = replace(specs[1], ports=(replace(specs[1].ports[0], rank=2), specs[1].ports[1]))

    assert port_ranks((ranked, bare)) == {first.port: 0, second.port: 1, bare.ports[0].port: 2}


# --- potential_sides -----------------------------------------------------------------


def _supply_box() -> DrawnFunction:
    return _box(1, generic_box_geometry(("a", "b", "c")))


def test_a_box_on_two_potentials_puts_its_supply_on_top_highest_potential_leftmost() -> None:
    """Ports `a` (rank 1) and `c` (rank 0) go N, `c` left of `a`; `b`, on no potential, goes S."""
    # UNDO: stages/boxes.py:potential_sides, `key=lambda n: ranks[n]` -> `key=lambda n: -ranks[n]`
    #     (the highest potential is rightmost)
    (box,) = potential_sides((_supply_box(),), {_port(1, 1): 1, _port(1, 3): 0})
    ports = {g.name: g for g in box.geometry.ports}

    assert {name: g.facing.value for name, g in ports.items()} == {"a": "n", "b": "s", "c": "n"}
    assert ports["c"].at.x < ports["a"].at.x
    plain = generic_box_geometry(("c", "a", "b"), ("n", "n", "s"))
    assert box.geometry == plain  # R6: no rail band above the body, the keep-out is the plain box's


def test_a_box_on_one_potential_or_a_symbol_that_is_no_box_is_left_as_drawn() -> None:
    """One rank is no supply row; a through symbol is no generic box."""
    # UNDO: stages/boxes.py:potential_sides, `< 2` -> `< 1` (a single potential is rebuilt)
    one = _supply_box()
    through = drawn(2)

    found = potential_sides((one, through), {_port(1, 1): 0, _port(1, 3): 0, _port(2, 1): 0})

    assert found == (one, through)
    assert one.geometry.key == GENERIC_BOX_KEY
    assert through.geometry.key != GENERIC_BOX_KEY
