"""UNIT-ID I1, I4, I6 (model half): a unit's own title and number, and its own root's silence.

`docs/archive/specs/2026-09-25-unit-own-identity.md`. The fixture is a cabinet (`+C1`, two root
parts) that places a relay interface board `-U2` (a real board, `PcbFacet`) holding one relay `-K1`.
"""

import dataclasses
from dataclasses import dataclass

import pytest
from plant import Plant
from query_builders import make_node, make_placement

from fransys_model.derive import (
    TOP_LEVEL,
    BomLine,
    bom_lines,
    designation_list,
    is_own_unit_root,
    is_sole_unit_root,
    printed_designation,
    takes_parents_designation,
)
from fransys_model.derive import external as derive_external
from fransys_model.derive.external import external as module_external
from fransys_model.kernel import Id, Model, SchemaError, make_id
from fransys_model.vocab.core import Item, Unit, UnitRelease
from fransys_model.vocab.membership import external as membership_external
from fransys_model.vocab.membership import unit_own_roots


@dataclass(frozen=True)
class _Station:
    model: Model
    cabinet: Id[Unit]
    board_unit: Id[Unit]
    board: Id[Item]
    relay: Id[Item]
    loose: Id[Item]
    extra: Id[Item] | None = None


def _mark_external(plant: Plant, item: Id[Item]) -> None:
    """Replace the plant's record for `item` by a copy with `external=True`."""
    (at,) = [n for n, record in enumerate(plant.records) if record.id == item]
    plant.records[at] = dataclasses.replace(plant.records[at], external=True)


def _unit(  # noqa: PLR0913 -- the Unit fields these tests vary
    plant: Plant,
    key: str,
    *,
    name: str,
    revision: int = 1,
    title: str = "",
    number: str = "",
    parent: Id[Unit] | None = None,
) -> Id[Unit]:
    """Add a `Unit`, an instance of the release carrying its own title and number (once)."""
    release_key = ("unit_release", name, "1", str(revision))
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name=name,
        version=1,
        revision=revision,
        interface="1",
        title=title,
        number=number,
    )
    if not plant.has(release.id):
        plant.add(release)
    unit = Unit(id=make_id(Unit, (key,)), key=(key,), release=release.id, parent=parent)
    plant.add(unit)
    return unit.id


def _station(*, external_root: bool = False) -> _Station:
    """A top-level cabinet at `+C1` (two root parts) holding a relay interface board unit.

    `external_root` adds one more root item `-E1` to the board unit, flagged external.
    """
    plant = Plant()
    node = make_node("c1", None)
    plant.add(node)
    cabinet = _unit(
        plant, "cab", name="cabinet", revision=2, title="Pump cabinet", number="SKX-PC-2"
    )
    board_unit = _unit(
        plant,
        "board-unit",
        name="relay-board",
        title="Relay interface board",
        number="SKX-RIB-2",
        parent=cabinet,
    )
    board = plant.item("board", part=plant.board_part(), designation="U2", unit=board_unit)
    relay = plant.item("k1", part=plant.part("K"), designation="K1", parent=board, unit=board_unit)
    for key, designation in (("q1", "Q1"), ("q2", "Q2")):
        item = plant.item(key, part=plant.part("Q"), designation=designation, unit=cabinet)
        plant.add(make_placement(f"p-{key}", item, node.id))
    loose = plant.item("loose", part=plant.part("F"), designation="F1")
    extra = None
    if external_root:
        extra = plant.item("ext", part=plant.part("E"), designation="E1", unit=board_unit)
        _mark_external(plant, extra)
    return _Station(plant.model(), cabinet, board_unit, board, relay, loose, extra)


def _unit_lines(lines: tuple[BomLine, ...]) -> list[BomLine]:
    return [line for line in lines if line.part is None]


def _by_mpn(lines: tuple[BomLine, ...]) -> dict[str, BomLine]:
    return {line.mpn: line for line in lines}


# ---- I1: the fields --------------------------------------------------------------------------


def test_a_unit_release_built_without_title_and_number_has_empty_strings() -> None:
    release = UnitRelease(
        id=make_id(UnitRelease, ("u",)),
        key=("u",),
        name="n",
        version=1,
        revision=1,
        interface="1",
    )
    assert (release.title, release.number) == ("", "")


# ---- I4: the predicate -----------------------------------------------------------------------


def test_is_own_unit_root_truth_table() -> None:
    s = _station()
    assert is_own_unit_root(s.model, s.board, s.board_unit) is True
    assert is_own_unit_root(s.model, s.board, None) is False
    assert is_own_unit_root(s.model, s.board, s.cabinet) is False
    assert is_own_unit_root(s.model, s.relay, s.board_unit) is False
    assert is_own_unit_root(s.model, s.loose, s.board_unit) is False


# ---- I4: the two model sites (acceptance 4, model half) --------------------------------------


def test_a_board_units_own_bom_keeps_the_bare_board_line_without_its_tag() -> None:
    s = _station()
    lines = _by_mpn(bom_lines(s.model, s.board_unit))
    board_line = lines["EXAMPLE-BOARD"]
    assert (board_line.count, board_line.designations) == (1, ())
    assert lines["EXAMPLE-K"].designations == ("-K1",)


def test_the_child_prints_the_board_tag_outside_the_boards_own_scope() -> None:
    """Proves the fixture is a real board: `-U2-K1` unit-less, `-K1` in the board's own set."""
    s = _station()
    assert printed_designation(s.model, s.relay) == "-U2-K1"
    assert printed_designation(s.model, s.relay, unit=s.board_unit) == "-K1"


def test_the_parents_bom_still_names_the_board_as_u2() -> None:
    s = _station()
    (line,) = _unit_lines(bom_lines(s.model, s.cabinet))
    assert line.designations == ("-U2",)


def test_a_boards_own_designation_list_has_no_row_for_the_board() -> None:
    s = _station()
    rows = designation_list(s.model, unit=s.board_unit)
    assert [(row.designation, row.item) for row in rows] == [("-K1", s.relay)]


def test_the_whole_model_designation_list_keeps_the_board_row() -> None:
    s = _station()
    rows = {row.item: row.designation for row in designation_list(s.model)}
    assert rows[s.board] == "-U2"
    assert rows[s.relay] == "-U2-K1"


def test_the_parents_designation_list_is_its_own_items_only() -> None:
    """Direct membership (U6): the board is a nested unit's item, never a row of the cabinet's."""
    s = _station()
    rows = designation_list(s.model, unit=s.cabinet)
    assert [row.designation for row in rows] == ["-Q1", "-Q2"]


# ---- I6: the unit's BOM line (acceptance 5) --------------------------------------------------


def test_the_cabinets_line_for_the_board_reads_its_number_and_title() -> None:
    s = _station()
    (line,) = _unit_lines(bom_lines(s.model, s.cabinet))
    assert line.mpn == "SKX-RIB-2"
    assert line.description == "Relay interface board"
    assert line.manufacturer == ""
    assert (line.revision, line.count, line.designations) == ("1.1", 1, ("-U2",))


def test_a_top_level_unit_line_reads_its_number_title_and_location() -> None:
    s = _station()
    (line,) = _unit_lines(bom_lines(s.model, TOP_LEVEL))
    assert line.mpn == "SKX-PC-2"
    assert line.description == "Pump cabinet"
    assert (line.revision, line.count, line.designations) == ("1.2", 1, ("+C1",))


def test_a_unit_with_no_number_prints_its_name_and_still_its_title() -> None:
    plant = Plant()
    _unit(plant, "u", name="cabinet", title="Pump cabinet")
    (line,) = _unit_lines(bom_lines(plant.model(), TOP_LEVEL))
    assert (line.mpn, line.description) == ("cabinet", "Pump cabinet")


def test_two_instances_of_one_name_and_revision_are_one_line_of_count_two() -> None:
    plant = Plant()
    for key in ("a", "b"):
        _unit(plant, key, name="board", title="T", number="N-1")
    (line,) = _unit_lines(bom_lines(plant.model(), TOP_LEVEL))
    assert (line.mpn, line.description, line.count) == ("N-1", "T", 2)


def test_an_accessory_of_the_own_root_is_silent_in_either_item_order() -> None:
    """The root holder `-F11` and its accessory share one part line; the cell omits both.

    The accessory (`takes_parents_designation`) prints its holder's text, so it is silent too.
    Both key namings are run, so the holder comes first in one and second in the other (the
    order of one line's items follows their ids).
    """
    for holder_key, accessory_key in (("h-a", "h-b"), ("h-b", "h-a")):
        plant = Plant()
        unit = _unit(plant, "u", name="holder-unit")
        part = plant.part("H")
        holder = plant.item(holder_key, part=part, designation="F11", unit=unit)
        accessory = plant.item(accessory_key, part=part, parent=holder, unit=unit)
        model = plant.model()
        assert takes_parents_designation(model, accessory)
        (own,) = bom_lines(model, unit)
        assert (own.mpn, own.count, own.designations) == ("EXAMPLE-H", 2, ())
        (whole,) = bom_lines(model)
        assert (whole.count, whole.designations) == (2, ("-F11",))


# ---- I4 amended: one definition of a unit's own roots (`unit_own_roots`) ---------------------


def test_the_one_external_function_is_reexported_not_copied() -> None:
    assert derive_external is membership_external
    assert module_external is membership_external


def test_own_roots_are_the_parentless_items_and_not_their_children() -> None:
    plant = Plant()
    unit = plant.unit("u")
    a = plant.item("a", part=plant.part("A"), unit=unit)
    b = plant.item("b", part=plant.part("A"), unit=unit)
    c = plant.item("c", part=plant.part("A"), parent=a, unit=unit)
    assert unit_own_roots(plant.model(), unit) == tuple(sorted((a, b)))  # the table is id-sorted
    assert c not in unit_own_roots(plant.model(), unit)


def test_an_item_whose_parent_is_in_another_unit_is_an_own_root() -> None:
    plant = Plant()
    outer, inner = plant.unit("outer"), plant.unit("inner")
    holder = plant.item("holder", part=plant.part("A"), unit=outer)
    placed = plant.item("placed", part=plant.part("A"), parent=holder, unit=inner)
    model = plant.model()
    assert unit_own_roots(model, inner) == (placed,)
    assert unit_own_roots(model, outer) == (holder,)


def test_external_items_are_no_own_roots() -> None:
    plant = Plant()
    unit, other = plant.unit("u"), plant.unit("other")
    plain = plant.item("plain", part=plant.part("A"), unit=unit)
    flagged = plant.item("flagged", part=plant.part("A"), unit=unit)
    supplier = plant.item("supplier", part=plant.part("A"), unit=other)
    below = plant.item("below", part=plant.part("A"), parent=supplier, unit=unit)
    _mark_external(plant, flagged)
    _mark_external(plant, supplier)
    model = plant.model()
    assert unit_own_roots(model, unit) == (plain,)
    assert flagged not in unit_own_roots(model, unit)
    assert below not in unit_own_roots(model, unit)
    assert unit_own_roots(model, other) == ()


def test_a_unit_with_no_items_has_no_own_roots() -> None:
    plant = Plant()
    unit = plant.unit("u")
    assert unit_own_roots(plant.model(), unit) == ()


def test_unit_own_roots_of_an_unknown_unit_returns_empty() -> None:
    """The documented contract: a unit the model does not hold has none (no `SchemaError`)."""
    plant = Plant()
    plant.unit("u")
    assert unit_own_roots(plant.model(), make_id(Unit, ("nope",))) == ()


def test_a_plain_root_next_to_an_external_root_is_the_sole_root() -> None:
    plant = Plant()
    unit = plant.unit("u")
    plain = plant.item("plain", part=plant.part("A"), unit=unit)
    flagged = plant.item("flagged", part=plant.part("A"), unit=unit)
    _mark_external(plant, flagged)
    model = plant.model()
    assert is_sole_unit_root(model, plain) is True
    assert is_sole_unit_root(model, flagged) is False


def test_a_units_only_root_being_external_is_not_a_sole_root() -> None:
    plant = Plant()
    unit = plant.unit("u")
    flagged = plant.item("flagged", part=plant.part("A"), unit=unit)
    _mark_external(plant, flagged)
    assert is_sole_unit_root(plant.model(), flagged) is False


def test_sole_root_truth_on_plain_units_is_unchanged() -> None:
    plant = Plant()
    one, two = plant.unit("one"), plant.unit("two")
    solo = plant.item("solo", part=plant.part("A"), unit=one)
    child = plant.item("child", part=plant.part("A"), parent=solo, unit=one)
    left = plant.item("left", part=plant.part("A"), unit=two)
    right = plant.item("right", part=plant.part("A"), unit=two)
    loose = plant.item("loose", part=plant.part("A"))
    model = plant.model()
    assert is_sole_unit_root(model, solo) is True
    assert [is_sole_unit_root(model, i) for i in (child, left, right, loose)] == [False] * 4


def test_is_sole_unit_root_refuses_an_unknown_item() -> None:
    """Unknown identity: `SchemaError` on the item, not the unit (decision 0021)."""
    plant = Plant()
    plant.unit("u")
    nope = make_id(Item, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        is_sole_unit_root(plant.model(), nope)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("item", nope)


def test_a_board_with_an_extra_external_root_still_prints_u2_above_and_nothing_below() -> None:
    """Acceptance 4's second case: the parent's BOM names the board, the own set stays silent."""
    s = _station(external_root=True)
    assert s.extra is not None
    (line,) = _unit_lines(bom_lines(s.model, s.cabinet))
    assert line.designations == ("-U2",)
    assert is_own_unit_root(s.model, s.board, s.board_unit) is True
    assert is_own_unit_root(s.model, s.extra, s.board_unit) is False
    own = _by_mpn(bom_lines(s.model, s.board_unit))
    assert (own["EXAMPLE-BOARD"].count, own["EXAMPLE-BOARD"].designations) == (1, ())
    assert own["EXAMPLE-K"].designations == ("-K1",)
    assert "EXAMPLE-E" not in own
    rows = designation_list(s.model, unit=s.board_unit)
    assert (s.relay, "-K1") in [(row.item, row.designation) for row in rows]
    assert s.board not in [row.item for row in rows]
