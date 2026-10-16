"""`derive.pin_positions` and `derive.seed_pins`: what a pin source seeds, as rows (model-0281).

Each case releases revision 1 of a small demo unit, builds revision 2 WITHOUT `releases=` and joins
the stored pins to it by hand, so the rows are seen before the facade turns them into facets.
"""

import fransys as fr
import fransys_author
import pytest

from fransys_model.derive import (
    PinPosition,
    gone_or_moved,
    numbering_pins,
    pin_positions,
    revision_findings,
    seed_pins,
)
from fransys_model.derive.numbering_pins import (
    NumberingItem,
    NumberingPins,
    NumberingRetired,
    unit_relative_key,
)
from fransys_model.vocab import items, units

_DATE = "2026-10-16"


def _relay_board(revision, *, names, tags=None):
    """A unit of free-numbered relays; `tags` maps a name to a written tag."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    u = design.scope("rb").unit("relay-board", revision=revision, interface="1")
    u.revision(revision, date=_DATE, text=f"Revision {revision}", created="OJB")
    for name in names:
        u.item("DEMO-RLY-2CO-24", name=name, tag=(tags or {}).get(name))
    return fr.build(parts, design.draft()), u


def _uid(scope):
    assert scope.unit_id is not None
    return scope.unit_id


def _names(model, seeds) -> dict[str, str]:
    return {unit_relative_key(model, s.item)[-1]: s.text for s in seeds}


@pytest.fixture(scope="module")
def source(tmp_path_factory) -> numbering_pins.NumberingPins:
    """Revision 1's pins: coil-a K1, coil-b K2, coil-c K3 with coil-c written by hand as `Z1`."""
    result, u = _relay_board(1, names=("coil-a", "coil-b", "coil-c"), tags={"coil-c": "Z1"})
    target = fr.release(result, tmp_path_factory.mktemp("seed"), unit=u)
    return numbering_pins.loads(
        (target / "baseline" / "numbering.json").read_text(encoding="utf-8")
    )


def test_a_gone_item_reserves_its_text_and_a_new_item_is_not_seeded(source):
    result, u = _relay_board(2, names=("aux", "coil-a", "coil-c"), tags={"coil-c": "Z1"})
    rows = seed_pins(result.model, _uid(u), source)
    assert _names(result.model, rows.assigned) == {"coil-a": "K1"}
    assert rows.reserved == (NumberingRetired(scope=None, code="K", text="K2"),)
    assert rows.tags == ()


def test_a_written_tag_now_or_at_release_keeps_the_pin_from_seeding(source):
    assert {row.key[-1]: row.authored for row in source.items}["coil-c"] is True
    result, u = _relay_board(2, names=("coil-a", "coil-b", "coil-c"), tags={"coil-a": "X9"})
    rows = seed_pins(result.model, _uid(u), source)
    assert _names(result.model, rows.assigned) == {"coil-b": "K2"}
    assert rows.reserved == ()


def test_a_pinned_item_whose_class_code_changed_is_reserved_not_seeded(source):
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    u = design.scope("rb").unit("relay-board", revision=2, interface="1")
    u.revision(2, date=_DATE, text="Revision 2", created="OJB")
    u.item("DEMO-RLY-2CO-24", name="coil-a")
    u.item("DEMO-PCB-IO", name="coil-b")
    result = fr.build(parts, design.draft())
    rows = seed_pins(result.model, _uid(u), source)
    assert _names(result.model, rows.assigned) == {"coil-a": "K1"}
    # coil-b moved to another class code and coil-c is gone: both texts stay reserved
    assert rows.reserved == (
        NumberingRetired(scope=None, code="K", text="K2"),
        NumberingRetired(scope=None, code="K", text="Z1"),
    )


def test_positions_list_every_non_terminal_item_by_key_with_no_text():
    result, u = _relay_board(2, names=("coil-b", "coil-a"))
    found = pin_positions(result.model, _uid(u))
    assert found == (
        PinPosition(key=("coil-a",), scope=None, code="K"),
        PinPosition(key=("coil-b",), scope=None, code="K"),
    )
    assert {items(result.model)[i].key[-1] for i in items(result.model)} >= {"coil-a", "coil-b"}


def test_an_instance_is_a_position_ending_in_unit():
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cab = design.scope("cab").unit("seed-cabinet", revision=1, interface="1", class_code="U")
    cab.revision(1, date=_DATE, text="First", created="OJB")
    board = cab.scope("m1").unit("seed-board", revision=1, interface="1", class_code="U")
    board.revision(1, date=_DATE, text="First", created="OJB")
    board.item("DEMO-PCB-IO", name="pcb")
    result = fr.build(parts, design.draft())
    (position,) = pin_positions(result.model, _uid(cab))
    assert position.key[-1] == "unit"
    assert (position.scope, position.code) == (None, "U")
    assert _uid(board) in units(result.model)


def test_revision_findings_name_a_new_item_and_a_retagged_one_with_the_pin_path(source, tmp_path):
    result, u = _relay_board(2, names=("aux", "coil-a", "coil-b", "coil-c"), tags={"coil-a": "X9"})
    found = revision_findings(result.model, _uid(u), source, tmp_path)
    moved = [f.message for f in found if f.code == "DESIGNATION_MOVED"]
    new = [f.message for f in found if f.code == "DESIGNATION_NEW_IN_REVISION"]
    where = tmp_path / "baseline" / "numbering.json"
    assert len(moved) == 2
    assert all(f"in {where}, and now prints" in text for text in moved)
    assert any("'K1'" in text and "'X9'" in text for text in moved)
    assert len(new) == 1
    assert "is new in this revision and takes" in new[0]


def test_gone_or_moved_matches_on_key_scope_and_code_and_keeps_the_retired_texts():
    pin = NumberingItem(key=("a",), scope=("b",), code="K", text="K1", authored=False)
    old = NumberingRetired(scope=None, code="K", text="K0")
    pins = NumberingPins(items=(pin,), retired=(old,))
    same = PinPosition(key=("a",), scope=("b",), code="K")
    assert gone_or_moved(pins, [same]) == (old,)
    moved = PinPosition(key=("a",), scope=("b",), code="Q")
    # sorted: a scoped text comes before an unscoped one
    assert gone_or_moved(pins, [moved]) == (
        NumberingRetired(scope=("b",), code="K", text="K1"),
        old,
    )
    swapped = PinPosition(key=("a",), scope=None, code="K")
    assert len(gone_or_moved(pins, [swapped])) == 2
