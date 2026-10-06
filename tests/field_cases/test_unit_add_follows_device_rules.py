"""Field case: `d.add` follows `device`: the open function block, the default place, `place=`.

The engineering shape: a controller cabinet with an I/O board built as a unit, added inside the
`PLC` function block of a design whose default place is the cabinet `C1`. A second board is
added with `place="C2"`.

The bug: `d.add` took no place and ignored the open block, so the board's boundary device carried
neither `=PLC` nor `+C1`: its designation lost the function group (0.5.1 wrote scope at=C1,
group=PLC).

The rule (EA15, G27): `d.add` joins the open `d.function` block, takes the default place, and
takes `place=` with `device`'s meaning. The board's own drawing does not change.
"""

from typing import NamedTuple

import fransys as fr

from fransys_model.vocab.tables import aspect_nodes, items, placements


class _Board(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: fr.Design) -> _Board:
    return _Board(d.device("X1", "DEMO-CONN-2P", interface=True))


def _labels(model: fr.Model, device: fr.Device) -> set[str]:
    """The labels of the aspect nodes the device's item is placed at."""
    nodes = aspect_nodes(model)
    return {nodes[p.node].label for p in placements(model).values() if p.item == device.id}


def _design() -> fr.Design:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.location("C2", "Field box")
    return d


def test_add_joins_the_block_and_the_default_place() -> None:
    d = _design()
    with d.function("PLC", "Control"):
        a = d.add(_board, "A")
    assert _labels(fr.build(d).model, a.X1) == {"PLC", "C1"}


def test_add_takes_place_with_devices_meaning() -> None:
    """Outside a block no group; `place="C2"` replaces the default; `place=None` has none."""
    d = _design()
    b = d.add(_board, "B", place="C2")
    with d.function("PLC", "Control"):
        c = d.add(_board, "C", place=None)
    model = fr.build(d).model
    assert _labels(model, b.X1) == {"C2"}
    assert _labels(model, c.X1) == {"PLC"}


def test_the_boards_own_drawing_does_not_carry_the_instances_place() -> None:
    """In the unit's own context X1 reads `-X1`; the cabinet's `=PLC+C1` is not the board's.

    The instance tag A prints before it in the cabinet, `-A-X1` (UT2).
    """
    d = _design()
    with d.function("PLC", "Control"):
        a = d.add(_board, "A")
        d.add(_board, "B", place=None)  # a second unit shares =PLC, so it is not a's own
        d.device("P1", "DEMO-CONN-2P")  # outside any unit, so C1 is not a's own either
    model = fr.build(d).model
    unit_id = items(model)[a.X1.id].unit
    assert fr.derive.reference_designation(model, a.X1.id) == "=PLC+C1-A-X1"
    assert fr.derive.reference_designation(model, a.X1.id, unit=unit_id) == "-X1"
