"""Field case: a lamp wired to pin 1 of an I/O board instance tagged U2, which the container draws as a black box.
The bug: a black box's title line must not carry the instance tag, which stands only in boundary texts such as -U2-J1:1 (owner 2026-10-05).
Fixed by model-0134, the black box's title keeps the release title and revision, and the tag stands in every boundary text."""

from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, unit_document
from fransys.colours import BU


class _Io(NamedTuple):
    J1: Any


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    root = u.device("U9", "DEMO-PCB-IO")
    return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True))


def _container_texts() -> tuple[fr.Model, list[str]]:
    """The model and the black box title lines the container's pages draw."""
    d = fr.design("demo_parts", place="C1")
    d.project(title="Box", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-05", text="First issue", created="XX")
    _cabinet = d.location("C1", "Cabinet")
    board = d.add(_board, "U2")
    lamp = d.device("M1", "DEMO-LAMP-24")
    d.series(lamp["1"], board.J1["1"], wire=(BU, 0.5))
    d.earth(lamp["2"])
    model = fr.build(d, cabinet_document(_cabinet), unit_document("demo-board")).model
    titles: list[str] = []
    for drawing in drawn_pages(model).values():
        titles += [o.label.text for o in drawing.outlines if o.label]
    return model, titles


def test_the_container_place_page_draws_no_frame_title() -> None:
    """R833: a place page frames no unit, so no title line (and so no instance tag) stands on it."""
    _, titles = _container_texts()
    assert titles == []
