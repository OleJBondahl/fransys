"""FD3 tests: `pins()` and its codec, `dumps`/`loads`."""

import pytest

from fransys_model.derive.numbering_pins import dumps, loads, pins
from fransys_model.derive.rows import NumberingItem, NumberingPins, NumberingRetired
from fransys_model.derive.unit_relative_key import unit_relative_key
from fransys_model.kernel import (
    Draft,
    Id,
    Model,
    Origin,
    Record,
    SchemaVersionError,
    freeze,
    make_id,
)
from fransys_model.vocab.core import Item, Unit, UnitRelease
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.templates import Part

_ORIGIN = Origin(file="test_numbering_pins.py", line=1, note="hand-built")


def _model(records: list[Record]) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _release(name: str) -> UnitRelease:
    key = ("unit_release", name, "1", "1")
    return UnitRelease(
        id=make_id(UnitRelease, key), key=key, name=name, version=1, revision=1, interface="1"
    )


def _unit(prefix: tuple[str, ...], release: UnitRelease) -> Unit:
    key = (*prefix, "unit")
    return Unit(id=make_id(Unit, key), key=key, release=release.id, parent=None)


def _item(
    key: tuple[str, ...],
    *,
    unit: Id[Unit] | None = None,
    parent: Id[Item] | None = None,
    part: Id[Part] | None = None,
    tag: str | None = None,
) -> Item:
    return Item(
        id=make_id(Item, key),
        key=key,
        part=part,
        parent=parent,
        position=None,
        tag=tag,
        description="Invented",
        unit=unit,
    )


def _part(class_code: str, name: str) -> Part:
    return Part(
        id=make_id(Part, (name,)),
        key=(name,),
        mpn=f"MPN-{name}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.GENERIC,
        class_code=class_code,
    )


def _board_part(name: str) -> tuple[Part, PcbFacet]:
    part = Part(
        id=make_id(Part, (name,)),
        key=(name,),
        mpn=f"MPN-{name}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.BOARD,
        class_code="A",
    )
    facet = PcbFacet(
        id=make_id(PcbFacet, (name, "pcb")), key=(name, "pcb"), subject=part.id, revision="A"
    )
    return part, facet


def _terminal_facet(name: str, subject: Id[Item], group: str, index: int) -> TerminalFacet:
    return TerminalFacet(
        id=make_id(TerminalFacet, (name, "terminal")),
        key=(name, "terminal"),
        subject=subject,
        group=group,
        index=index,
    )


def test_a_tagged_item_with_a_part_gets_its_own_row_no_scope() -> None:
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    relay = _part("K", "relay")
    item = _item(("cab", "coil-a"), unit=unit.id, tag="K1", part=relay.id)
    model = _model([release, unit, relay, item])
    result = pins(model, unit.id)
    assert result.retired == ()
    assert len(result.items) == 1
    row = result.items[0]
    assert row.key == ("coil-a",)
    assert row.scope is None
    assert row.code == "K"
    assert row.text == "K1"
    assert row.authored is True


def test_an_item_behind_a_board_gets_the_boards_unit_relative_key_as_scope() -> None:
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    board_part, board_facet = _board_part("board")
    board = _item(("cab", "board"), unit=unit.id, tag="A1", part=board_part.id)
    relay = _part("K", "relay")
    child = _item(("cab", "board", "k1"), unit=unit.id, parent=board.id, tag="K1", part=relay.id)
    model = _model([release, unit, board_part, board_facet, relay, board, child])
    result = pins(model, unit.id)
    by_key = {row.key: row for row in result.items}
    assert by_key[("board",)].scope is None
    assert by_key[("board", "k1")].scope == unit_relative_key(model, board.id) == ("board",)


def test_a_terminal_is_excluded_even_though_its_own_text_would_print() -> None:
    """CAN-FAIL PROBE case: see the report for the source-edit-and-revert that proves this."""
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    strip = _item(("cab", "strip"), unit=unit.id, tag="X1")
    terminal_item = _item(("cab", "strip", "t1"), unit=unit.id, parent=strip.id, tag="T1")
    terminal_facet = _terminal_facet("t1", terminal_item.id, "L1", 1)
    model = _model([release, unit, strip, terminal_item, terminal_facet])
    result = pins(model, unit.id)
    assert [row.key for row in result.items] == [("strip",)]


def test_a_part_less_tagged_item_appears_with_null_code() -> None:
    """Designer ruling 2026-09-27: `code` is `None`, not `""`, for a part-less item -- one
    record, one spelling of absence, matching `scope`'s own `None`."""
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    harness = _item(("cab", "harness"), unit=unit.id, tag="W1")
    model = _model([release, unit, harness])
    result = pins(model, unit.id)
    assert len(result.items) == 1
    row = result.items[0]
    assert row.code is None
    assert row.text == "W1"
    assert row.authored is True
    assert '"code":null' in dumps(result)


def test_an_undesignated_item_is_excluded() -> None:
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    accessory = _item(("cab", "accessory"), unit=unit.id)
    model = _model([release, unit, accessory])
    result = pins(model, unit.id)
    assert result.items == ()


def test_loads_of_dumps_roundtrips_items_and_retired() -> None:
    value = NumberingPins(
        items=(
            NumberingItem(
                key=("board", "k1"), scope=("board",), code="K", text="K1", authored=True
            ),
        ),
        retired=(NumberingRetired(scope=None, code="Q", text="Q3"),),
    )
    assert loads(dumps(value)) == value


def test_loads_refuses_an_unknown_numbering_version() -> None:
    text = dumps(NumberingPins(items=(), retired=())).replace(
        '"numbering_version":1', '"numbering_version":2'
    )
    with pytest.raises(SchemaVersionError) as excinfo:
        loads(text)
    assert excinfo.value.expected == 1
    assert excinfo.value.actual == 2


def test_shuffled_insertion_order_gives_the_same_sorted_items() -> None:
    """Root CLAUDE.md invariant 7: nothing depends on insertion order; `rows.sort` proves it."""
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    relay = _part("K", "relay")
    item_a = _item(("cab", "aaa"), unit=unit.id, tag="A1", part=relay.id)
    item_z = _item(("cab", "zzz"), unit=unit.id, tag="Z1", part=relay.id)
    forward = _model([release, unit, relay, item_a, item_z])
    backward = _model([release, unit, relay, item_z, item_a])
    result_forward = pins(forward, unit.id)
    result_backward = pins(backward, unit.id)
    assert result_forward.items == result_backward.items
    assert [row.key for row in result_forward.items] == [("aaa",), ("zzz",)]
