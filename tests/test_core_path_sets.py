"""The core path draws one drawing set per location, in the order of their labels (Ruling 50).

Two cabinets, C2 authored first: the sets stand C1 then C2, numbered 1 and 2, each with its own
pages. A wire between the cabinets belongs to neither set.
"""

lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.derive.order import locations_in_order
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab import aspect_nodes


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C2")
    d.location("C2", "Second")
    first = d.location("C1", "First")
    with d.function("B", "Relays"):
        k = [
            d.device(f"K{n}", "DEMO-RLY-2CO-24", place=place)
            for n, place in ((1, "C2"), (2, "C2"), (3, "C1"), (4, "C1"))
        ]
        for a, b in ((0, 1), (2, 3), (1, 2)):  # the last wire crosses the two cabinets
            d.detail.wire(k[a].coil["A2"], k[b].coil["A1"], wire=(BU, 0.5))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, first, cover=cover))


def test_each_location_is_one_drawing_set_in_label_order(tmp_path) -> None:
    model = _build(tmp_path).model
    sets = sorted(layout_of(model, DrawingSet).values(), key=lambda s: s.number)
    places = [s.location for s in sets if s.location is not None]
    assert len(places) == len(sets)
    labels = [aspect_nodes(model)[place].label for place in places]
    assert (labels, [s.number for s in sets]) == (["C1", "C2"], [1, 2])
    assert locations_in_order(model, places) == tuple(places)


def test_each_drawing_set_has_its_own_page(tmp_path) -> None:
    model = _build(tmp_path).model
    owners = [p.drawing_set for p in layout_of(model, Page).values()]
    assert len(owners) == len(set(owners)) == 2


def test_a_net_with_two_pins_in_each_location_draws_distinct_wires(tmp_path) -> None:
    d = fr.design("demo_parts", place="C2")
    d.location("C2", "Second")
    first = d.location("C1", "First")
    with d.function("B", "Relays"):
        k = [
            d.device(f"K{n}", "DEMO-RLY-2CO-24", place=place)
            for n, place in ((1, "C2"), (2, "C2"), (3, "C1"), (4, "C1"))
        ]
        for a, b in ((0, 1), (2, 3), (1, 2)):
            d.detail.wire(k[a].coil["A2"], k[b].coil["A2"], wire=(BU, 0.5))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, first, cover=cover)).model
    drawings = drawn_pages(model)
    ids = [w.id for drawing in drawings.values() for w in drawing.wires]
    assert len(ids) == len(set(ids))
    assert len([page for page, drawing in drawings.items() if drawing.wires]) == 2
