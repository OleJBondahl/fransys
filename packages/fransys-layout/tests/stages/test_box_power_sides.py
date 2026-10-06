"""D5: a generic box's power pins go on the side their kind says (hand-made values)."""

from dataclasses import replace

from samples import connection, drawn, hid, placed

from fransys_layout.geometry import generic_box_geometry
from fransys_layout.stages import Connection, DrawnFunction, DrawnPort, PortRef, Role
from fransys_layout.stages.boxes import box_sides, potential_sides


def _port(which: int):
    return hid("port", 10 + which)


def _box(
    names: tuple[str, ...], ac: tuple[str, ...] = (), groups: dict[str, int] | None = None
) -> DrawnFunction:
    """Function 1 as a generic box; the port of `names[i]` is `_port(i + 1)`, `ac` the AC pins."""
    groups = groups or {}
    ports = tuple(
        DrawnPort(port=_port(i + 1), symbol_port=n, ac=n in ac, group=groups.get(n, 0))
        for i, n in enumerate(names)
    )
    return replace(drawn(1), geometry=generic_box_geometry(names), ports=ports)


def _sides(box: DrawnFunction) -> dict:
    return {g.name: g.facing.value for g in box.geometry.ports}


def _x(box: DrawnFunction, name: str) -> int:
    return next(g.at.x for g in box.geometry.ports if g.name == name)


def test_a_lamp_with_a_ground_pin_has_the_ground_at_the_bottom() -> None:
    """Pin `z` is ground and `h` on no rail: `z` would alternate to the top, D5 sends it S."""
    # UNDO: stages/box_power.py:pinned_sides, `forced_sides(...) or supply_sides(...)` ->
    #     `supply_sides(...)` (the lone ground pin keeps the alternating top)
    (lamp,) = potential_sides((_box(("z", "h")),), {_port(1): 1}, {_port(1): "ground"})

    assert _sides(lamp)["z"] == "s"


def test_a_dc_only_box_has_supply_on_top_and_ground_at_the_bottom() -> None:
    """`p` on 24 V (supply) goes N and `m` on 0 V (ground) goes S."""
    # UNDO: stages/box_power.py:forced_sides, `"n" if kind == "supply" and not ac` -> `"s"`
    #     (the supply pin goes to the bottom)
    kinds = {_port(1): "ground", _port(2): "supply"}  # `m` first: it would alternate to the top
    (box,) = potential_sides((_box(("m", "p")),), {_port(1): 1, _port(2): 0}, kinds)

    assert _sides(box) == {"m": "s", "p": "n"}


def test_a_power_supply_has_ac_on_top_and_every_dc_pin_at_the_bottom() -> None:
    """`L`, `N` on AC rails (ranks 2, 3) go N; `p` (supply) and `m` (ground) go S, `p` left."""
    # UNDO: stages/box_power.py:forced_sides, `and not ac` deleted (the supply pin goes to the top)
    names = ("L", "N", "p", "m")
    rank_of = {_port(1): 2, _port(2): 3, _port(3): 0, _port(4): 1}
    kinds = {_port(3): "supply", _port(4): "ground"}
    (psu,) = potential_sides((_box(names, ac=("L", "N")),), rank_of, kinds)

    assert _sides(psu) == {"L": "n", "N": "n", "p": "s", "m": "s"}
    assert _x(psu, "L") < _x(psu, "N")
    assert _x(psu, "p") < _x(psu, "m")


def test_a_box_with_no_power_kind_keeps_the_rank_rule() -> None:
    """Without a declared supply, two ranks put both ranked pins N as before D5."""
    # UNDO: stages/box_power.py:pinned_sides, `or supply_sides(ports, rank_of)` deleted
    #     (the ranked pins stay on the alternating sides)
    (box,) = potential_sides((_box(("a", "b", "c")),), {_port(1): 1, _port(3): 0}, {})

    assert _sides(box) == {"a": "n", "b": "s", "c": "n"}


def test_a_supply_pin_stays_on_top_when_its_partner_is_below() -> None:
    """C5 turns `b` (no kind) toward the partner below, but the supply pin `a` is forced N."""
    # UNDO: stages/boxes.py:_turned_box, `if name in pinned:` -> `if False:`
    #     (`a` turns to the S partner)
    box = _box(("a", "b"))
    below = placed(2, x=0, y=5000)
    at_box = replace(placed(1, x=0, y=0), geometry=box.geometry)
    args = ((at_box, below), (box, drawn(2)), (connection(1, 2, 1),))  # ends at `_port(1)`

    (forced, _) = box_sides(*args, ({_port(1): 0}, {_port(1): "supply"}, {}))
    (free, _) = box_sides(*args, ({}, {}, {}))

    assert _sides(forced) == {"a": "n", "b": "s"}
    assert _sides(free) == {"a": "s", "b": "s"}


def test_inside_an_item_box_v1_sides_beat_d5() -> None:
    """Supply `p` and ground `m` would go N and S (D5); the item box's sides put `p` S, `m` N."""
    # UNDO: stages/box_power.py:power_geometry, `item_pins(one.ports, sides) or` deleted
    #     (D5 puts the supply pin on top)
    kinds = {_port(1): "supply", _port(2): "ground"}
    sides = {_port(1): "s", _port(2): "n"}
    (box,) = potential_sides((_box(("p", "m")),), {_port(1): 1, _port(2): 0}, kinds, sides)

    assert _sides(box) == {"p": "s", "m": "n"}


def test_an_item_box_pin_keeps_its_side_and_each_side_orders_by_partner_x() -> None:
    """`c` stays N though its partner is below; S pins wired to x 200 and 0 order `b` first."""
    # UNDO: stages/boxes.py:_turned_box, `v1 = item_pins(one.ports, sides)` -> `v1 = {}`
    #     (`c` turns S toward its partner)
    box = _box(("a", "b", "c"))
    sides = {_port(1): "s", _port(2): "s", _port(3): "n"}
    below = {2: 200, 3: 0, 4: 0}  # partner function -> x; port `i` of the box is wired to i + 1
    wires = tuple(
        Connection(
            handle=hid("conductor", n),
            physical_net=hid("net", n),
            role=Role.CONTROL,
            a=PortRef(function=hid("function", n + 1), port=hid("port", (n + 1) * 10 + 1)),
            b=PortRef(function=hid("function", 1), port=_port(n)),
        )
        for n in (1, 2, 3)
    )
    at_box = replace(placed(1, x=0, y=0), geometry=box.geometry)
    others = tuple(placed(n, x=x, y=5000) for n, x in below.items())
    drawn_all = (box, *(drawn(n) for n in below))

    (turned, *_) = box_sides((at_box, *others), drawn_all, wires, ({}, {}, sides))

    assert _sides(turned) == {"a": "s", "b": "s", "c": "n"}
    assert _x(turned, "b") < _x(turned, "a")


def test_a_ranked_channel_that_is_not_ac_does_not_flip_a_dc_box() -> None:
    """24 V through a contact gives channels `c`, `d` a rank; D5 still puts `p` N and `m` S."""
    # UNDO: stages/box_power.py:_forced_sides, `p.ac and` -> `p.port in rank_of and`, with
    #     `rank_of` passed back in (the ranked channels read as AC: `p` goes S)
    box = _box(("c", "p", "m", "d"))
    kinds = {_port(2): "supply", _port(3): "ground"}
    rank_of = {_port(1): 0, _port(2): 0, _port(3): 1, _port(4): 0}
    (found,) = potential_sides((box,), rank_of, kinds)

    assert _sides(found)["p"] == "n"
    assert _sides(found)["m"] == "s"


_T1 = ("SIG", "L", "N", "+", "-")  # SIG first: it would tie with `+` (the switched DC-OK link)
_T1_GROUPS = {"L": 0, "N": 0, "+": 1, "-": 1, "SIG": 2}  # input, output, dc_ok in V1's order
_T1_RANKS = {_port(2): 0, _port(3): 1, _port(4): 2, _port(5): 3, _port(1): 2}  # SIG = `+`'s rank
_T1_SIDES = {_port(1): "s", _port(2): "n", _port(3): "n", _port(4): "s", _port(5): "s"}


def _t1_order(box: DrawnFunction, side: str) -> list[str]:
    on = [g for g in box.geometry.ports if g.facing.value == side]
    return [g.name for g in sorted(on, key=lambda g: g.at.x)]


def test_a_psu_box_keeps_each_pin_group_whole_on_its_side() -> None:
    """T1: L, N on top; below `+`, `-` (one function) before SIG, which shares `+`'s rank."""
    # UNDO: stages/boxes.py:_turned_box and stages/box_power.py:power_geometry, the group index
    #     dropped from the sort keys (SIG sorts between `+` and `-`, or before `+`)
    box = _box(_T1, ac=("L", "N"), groups=_T1_GROUPS)
    at_box = replace(placed(1, x=0, y=0), geometry=box.geometry)

    (turned,) = box_sides((at_box,), (box,), (), (_T1_RANKS, {}, _T1_SIDES))

    assert _t1_order(turned, "n") == ["L", "N"]
    assert _t1_order(turned, "s") == ["+", "-", "SIG"]


def test_the_first_placement_of_a_psu_box_keeps_its_groups_whole_too() -> None:
    """`potential_sides` draws T1's box before any placement: the same order, groups whole."""
    # UNDO: stages/box_power.py:power_geometry, `(p.group, rank_of.get(p.port, 0))` ->
    #     `rank_of.get(p.port, 0)` (SIG stands first on the bottom)
    box = _box(_T1, ac=("L", "N"), groups=_T1_GROUPS)

    (found,) = potential_sides((box,), _T1_RANKS, {}, _T1_SIDES)

    assert _t1_order(found, "n") == ["L", "N"]
    assert _t1_order(found, "s") == ["+", "-", "SIG"]


def test_an_item_box_pin_on_a_ranked_potential_keeps_c22_order_before_partner_x() -> None:
    """V1 S pins `a`, `b` on ranked potentials: `b` (rank 0) stands left, its partner right."""
    # UNDO: stages/boxes.py:_turned_box, `(not v1 or port in rank_of)` -> `not v1`
    #     (V1 pins order by partner x only: `a` goes left)
    box = _box(("a", "b"))
    sides = {_port(1): "s", _port(2): "s"}
    wires = tuple(
        Connection(
            handle=hid("conductor", n),
            physical_net=hid("net", n),
            role=Role.CONTROL,
            a=PortRef(function=hid("function", n + 1), port=hid("port", (n + 1) * 10 + 1)),
            b=PortRef(function=hid("function", 1), port=_port(n)),
        )
        for n in (1, 2)
    )
    at_box = replace(placed(1, x=0, y=0), geometry=box.geometry)
    others = (placed(2, x=0, y=5000), placed(3, x=200, y=5000))
    rank_of = {_port(1): 1, _port(2): 0}

    (turned, *_) = box_sides(
        (at_box, *others), (box, drawn(2), drawn(3)), wires, (rank_of, {}, sides)
    )

    assert _sides(turned) == {"a": "s", "b": "s"}
    assert _x(turned, "b") < _x(turned, "a")
