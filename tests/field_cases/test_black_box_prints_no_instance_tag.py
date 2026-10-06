"""Field case: a unit instance drawn as a black box prints its tag in the boundary texts only.

The engineering shape: a top-level design holds a lamp `M1` wired to pin 1 of an I/O board
instance tagged `U2`. The board is a unit, so its container draws it as a black box.

The rule (UT2, owner ruling E1, 2026-10-05): the black box's title line stays the release title
and revision, with no instance tag; the tag stands in every boundary text (`-U2-J1:1`).

The decision that fixes it: model-0134.
"""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import DrawingSet, Label, Page, layout_of


class _Io(NamedTuple):
    J1: Any


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    root = u.device("U9", "DEMO-PCB-IO")
    return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True))


def _container_texts() -> tuple[fr.Model, list[str], list[str]]:
    """The model, the black box title lines and the pin texts of the container's own set."""
    d = fr.design("demo_parts", place="C1")
    d.project(title="Box", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-05", text="First issue", created="XX")
    d.location("C1", "Cabinet")
    board = d.add(_board, "U2")
    lamp = d.device("M1", "DEMO-LAMP-24")
    d.wire(lamp["1"], board.J1["1"], wire=(BU, 0.5))
    model = fr.build(d, system_document()).model
    sets = layout_of(model, DrawingSet)
    pages = layout_of(model, Page)
    titles, pins = [], []
    for label in layout_of(model, Label).values():
        if sets[pages[label.page].drawing_set].unit is not None:
            continue
        text = label_text(model, label)
        if label.slot == "outline_title":
            titles.append(text)
        elif label.slot.startswith("tag.pin."):
            pins.append(text)
    return model, titles, pins


def test_the_black_box_title_line_has_no_instance_tag() -> None:
    model, titles, _ = _container_texts()
    unit = next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name)
    release = fr.derive.unit_release(model, unit)
    expected = f"demo-board rev {fr.derive.revision_text(release.version, release.revision)}"
    assert titles == [expected]
    assert "U2" not in titles[0]


def test_the_boundary_text_carries_the_instance_tag() -> None:
    _, _, pins = _container_texts()
    assert pins == ["-U2-J1:1"]
