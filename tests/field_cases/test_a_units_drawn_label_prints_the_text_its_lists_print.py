"""Field case: a board unit of two relays wired coil to coil, placed in a cabinet as instance `U1`, whose own document draws and lists them.
The bug: the document drew `-U1-K1` where its lists printed `-K1`, the drawn label using the whole-model form.
Fixed by model-0359 (DESIGNATION-DRAWN), the drawn label and every list print the same text, with no instance tag."""

from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document


class _Board(NamedTuple):
    K1: fr.Device
    K2: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Board:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    u.series(k1.coil["A1"], k2.coil["A1"], wire=("RD", 0.75))
    u.series(k1.coil["A2"], k2.coil["A2"], wire=("BU", 0.75))
    return _Board(k1, k2)


def _built() -> tuple[fr.BuildResult, _Board]:
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    board = d.add(_board, "U1", place="C1")
    document = unit_document("demo-board")
    return fr.build(d, document), board


def test_the_drawn_labels_equal_the_designations_the_unit_lists_print() -> None:
    result, board = _built()
    model = result.model
    unit = next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-board")
    listed = sorted(fr.derive.printed_designation(model, one.id, unit=unit) for one in (board.K1, board.K2))
    drawn = sorted(t.text for d in drawn_pages(model).values() for t in d.texts if t.kind == "TAG")
    assert listed == ["-K1", "-K2"]
    assert drawn == listed
