"""Field case: a unit's drawn label and every list of its own document print the same designation.

The engineering shape: a board unit of two relays wired coil to coil, placed in a cabinet as the
instance `U1`. Its own document draws both relays and lists them.

The bug: the document drew `-U1-K1` where its lists print `-K1`. The drawn label read the
whole-model form, the lists the unit's own form (the pump cabinet of the flip rehearsal showed
`-U1-Q11` beside `-Q11`).

The rule: unit-own identity (`DESIGNATION-SCHEME`): the drawn label and every list print the same
text, and the unit's own document does not carry its instance tag.

The decision that fixes it: model-0359 (DESIGNATION-DRAWN).
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages


class _Board(NamedTuple):
    K1: fr.Device
    K2: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Board:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    u.detail.wire(k1.coil["A1"], k2.coil["A1"], wire=("RD", 0.75))
    u.detail.wire(k1.coil["A2"], k2.coil["A2"], wire=("BU", 0.75))
    return _Board(k1, k2)


def _built() -> tuple[fr.BuildResult, _Board]:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Board\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.location("C1", "Cabinet")
        board = d.add(_board, "U1", place="C1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-board", cover=cover)
        return fr.build(d, document), board


def test_the_drawn_labels_equal_the_designations_the_unit_lists_print() -> None:
    result, board = _built()
    model = result.model
    unit = next(
        u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-board"
    )
    listed = sorted(
        fr.derive.printed_designation(model, one.id, unit=unit) for one in (board.K1, board.K2)
    )
    drawn = sorted(t.text for d in drawn_pages(model).values() for t in d.texts if t.kind == "TAG")
    assert listed == ["-K1", "-K2"]
    assert drawn == listed
