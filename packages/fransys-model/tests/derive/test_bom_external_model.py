"""Tests for `bom_lines` and external items (external-items spec Y1, Y2).

An external item, or any item below an external one, has no BOM line: someone else supplies
and owns it, exactly as for `installed=False`. Every scope kind gives the same answer.
"""

import dataclasses
from typing import Any

from plant import Plant
from query_builders import make_core, make_node, make_part, make_placement, make_terminal

from fransys_model.derive import TOP_LEVEL, BomLine, bom_lines
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item, Unit

STRIP = make_id(Item, ("x1",))
UNIT = make_id(Unit, ("cab",))
# The designations the strip's terminals print: `-<strip designation>:<group>:<index>`.
TERMINALS = ("-X1:L:1", "-X1:L:2")


def _set(plant: Plant, key: tuple[str, ...], **changes: Any) -> None:
    """Replace the item keyed `key` by a copy with `changes`."""
    item_id = make_id(Item, key)
    (at,) = [n for n, record in enumerate(plant.records) if record.id == item_id]
    plant.records[at] = dataclasses.replace(plant.records[at], **changes)


def _plant(*, external: bool, in_unit: bool = False) -> Plant:
    """Strip `X1` with two part-ful terminals, plain `K1`, cable `W1`, and `K5`, `B1`, `R1`, `S1`.

    `external` goes on the strip `X1` (its terminals are external through it), on `K5`, on
    `B1` and on `S1`; `B1` is also `installed=False`, and `R1` is `installed=False` only.
    `K1` and `K5` share one part. `in_unit` puts the strip, its terminals and `K1` in the
    unit `cab`; `K5`, `B1`, `R1`, `S1` and `W1` stay outside it.
    """
    plant = Plant()
    unit = plant.unit("cab", name="cabinet") if in_unit else None
    plant.item("x1", part=make_part(plant, "strip", "STRIP-1"), designation="X1", unit=unit)
    _set(plant, ("x1",), external=external)
    term_part = make_part(plant, "term", "TERM-1")
    first = make_terminal(plant, "x1", "t-1", group="L", index=1)
    make_terminal(plant, "x1", "t-2", group="L", index=2)
    for label in ("t-1", "t-2"):
        _set(plant, ("x1", label), part=term_part, unit=unit)
    shared = make_part(plant, "shared", "SHARED-1")
    plant.item("k1", part=shared, designation="K1", unit=unit)
    plant.item("k5", part=shared, designation="K5")
    _set(plant, ("k5",), external=external)
    plant.item("b1", part=make_part(plant, "both", "BOTH-1"), designation="B1", installed=False)
    _set(plant, ("b1",), external=external)
    plant.item("r1", part=make_part(plant, "reserved", "RESERVED-1"), designation="R1")
    _set(plant, ("r1",), installed=False)
    plant.item("s1", part=make_part(plant, "supplied", "SUPPLIED-1"), designation="S1")
    _set(plant, ("s1",), external=external)
    cable = plant.item("w1", part=make_part(plant, "cable", "CABLE-1"), designation="W1")
    make_core(plant, "w1-core", cable, (first.external, plant.pin("k1", "f", "1")), index=1)
    return plant


def _by_mpn(lines: tuple[BomLine, ...]) -> dict[str, BomLine]:
    assert lines
    return {line.mpn: line for line in lines}


def _designations(lines: tuple[BomLine, ...]) -> set[str]:
    assert lines
    return {designation for line in lines for designation in line.designations}


def test_an_external_strip_takes_its_terminals_out_of_the_bom() -> None:
    """The strip, its terminals and `K5` are listed plain and gone external; `B1` never is."""
    before = bom_lines(_plant(external=False).model())
    after = bom_lines(_plant(external=True).model())
    assert len(before) > len(after) > 0
    assert {"-X1", *TERMINALS, "-K5"} <= _designations(before)
    assert not {"-X1", *TERMINALS, "-K5", "-B1"} & _designations(after)
    assert {"STRIP-1", "TERM-1"} <= set(_by_mpn(before))
    assert not {"STRIP-1", "TERM-1", "BOTH-1"} & set(_by_mpn(after))


def test_the_cable_and_the_ordinary_item_keep_their_lines() -> None:
    """`W1` and `K1` are not external: their lines stay, and nothing else does."""
    lines = _by_mpn(bom_lines(_plant(external=True).model()))
    assert set(lines) == {"CABLE-1", "SHARED-1"}
    assert lines["CABLE-1"].designations == ("-W1",)
    assert lines["SHARED-1"].designations == ("-K1",)


def test_a_part_used_by_an_external_and_a_plain_item_counts_the_plain_one_only() -> None:
    """`K1` and `K5` share a part: plain it counts 2, with `K5` external it counts 1."""
    plain = _by_mpn(bom_lines(_plant(external=False).model()))["SHARED-1"]
    external = _by_mpn(bom_lines(_plant(external=True).model()))["SHARED-1"]
    assert (plain.count, plain.designations) == (2, ("-K1", "-K5"))
    assert (external.count, external.designations) == (1, ("-K1",))


def test_uninstalled_and_external_each_remove_an_item_alone_and_together() -> None:
    """`R1` is uninstalled only, `S1` external only, `B1` both, each on its own part."""
    plain = _by_mpn(bom_lines(_plant(external=False).model()))
    flagged = _by_mpn(bom_lines(_plant(external=True).model()))
    # only `installed=False` removes R1 and B1 while nothing is external
    assert "SUPPLIED-1" in plain
    assert {"RESERVED-1", "BOTH-1"}.isdisjoint(plain)
    # the flag alone removes S1 (an installed item that would otherwise appear)
    assert {"SUPPLIED-1", "RESERVED-1", "BOTH-1"}.isdisjoint(flagged)
    assert "SHARED-1" in flagged


def test_an_item_scope_on_the_external_strip_gives_no_line() -> None:
    """The strip's own subtree, terminals included, is empty; unflagged it is not."""
    assert _designations(bom_lines(_plant(external=False).model(), STRIP)) == {"-X1", *TERMINALS}
    assert bom_lines(_plant(external=True).model(), STRIP) == ()


def test_a_terminal_scope_is_empty_though_only_its_strip_carries_the_flag() -> None:
    """A terminal's own subtree is external through its strip."""
    terminal = make_id(Item, ("x1", "t-1"))
    assert _designations(bom_lines(_plant(external=False).model(), terminal)) == {TERMINALS[0]}
    assert bom_lines(_plant(external=True).model(), terminal) == ()


def test_a_unit_scope_and_the_top_level_leave_the_external_strip_out() -> None:
    """Unit `cab` holds the strip, its terminals and `K1`; the top level holds `K5`, `W1`."""
    plain, flagged = (_plant(external=flag, in_unit=True) for flag in (False, True))
    for plant in (plain, flagged):  # a second plain root, so `K1` is not the unit's sole root
        plant.item("k2", part=make_part(plant, "second", "SECOND-1"), designation="K2", unit=UNIT)
    plain, flagged = plain.model(), flagged.model()
    assert _designations(bom_lines(plain, UNIT)) == {"-X1", *TERMINALS, "-K1", "-K2"}
    assert _designations(bom_lines(flagged, UNIT)) == {"-K1", "-K2"}
    assert "SHARED-1" in _by_mpn(bom_lines(flagged, UNIT))
    assert {"-K5", "-W1"} <= _designations(bom_lines(plain, TOP_LEVEL))
    top = _designations(bom_lines(flagged, TOP_LEVEL))
    assert "-W1" in top
    assert not {"-K5", "-B1"} & top


def test_a_units_only_plain_root_next_to_an_external_strip_is_silent_on_its_own_set() -> None:
    """UNIT-ID I4: the external strip is no root, so `K1` is the sole one and prints no tag."""
    flagged = _plant(external=True, in_unit=True).model()
    line = _by_mpn(bom_lines(flagged, UNIT))["SHARED-1"]
    assert (line.count, line.designations) == (1, ())
    plain = _by_mpn(bom_lines(_plant(external=False, in_unit=True).model(), UNIT))["SHARED-1"]
    assert plain.designations == ("-K1",)


def _nested_unit_plant(*, external: bool) -> Plant:
    """Unit `top` nests unit `board`, which holds root `K1` and root strip `X1` (flag varies)."""
    plant = Plant()
    top = plant.unit("top", name="pump-cabinet")
    board = plant.unit("board", name="relay-board", parent=top)
    plant.item("k1", part=make_part(plant, "relay", "RELAY-1"), designation="K1", unit=board)
    plant.item("x1", part=make_part(plant, "strip", "STRIP-1"), designation="X1", unit=board)
    _set(plant, ("x1",), external=external)
    return plant


def test_a_unit_line_lists_only_the_non_external_roots_and_stays() -> None:
    """The external strip leaves the unit line's designations; the line and its count stay."""
    top = make_id(Unit, ("top",))
    (plain,) = bom_lines(_nested_unit_plant(external=False).model(), top)
    (flagged,) = bom_lines(_nested_unit_plant(external=True).model(), top)
    assert plain.part is None
    assert plain.designations == ("-K1", "-X1")
    assert flagged.part is None
    assert (flagged.mpn, flagged.count) == ("relay-board", plain.count) == ("relay-board", 1)
    assert flagged.designations == ("-K1",)


def test_an_external_root_does_not_turn_a_one_root_unit_into_a_located_one() -> None:
    """Both roots at `+C1`: plain, the unit reads its location; with `X1` external, `-K1` alone.

    The external root is not a root (decision model-0045), so the remaining root gives the
    "one root item" branch, which prints its own signed designation, not the location.
    """
    top = make_id(Unit, ("top",))
    lines = {}
    for external in (False, True):
        plant = _nested_unit_plant(external=external)
        node = make_node("c1", None)
        plant.add(node)
        for key in ("k1", "x1"):
            plant.add(make_placement(f"p-{key}", make_id(Item, (key,)), node.id))
        (lines[external],) = bom_lines(plant.model(), top)
    assert lines[False].designations == ("+C1",)
    assert lines[True].designations == ("-K1",)
