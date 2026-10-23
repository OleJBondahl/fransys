"""Field case: columns whose designations differ only by a number stand in natural order.

The engineering shape: three lamps H10, H2 and H1, each wired across one supply, with no chain
hint, so each is a loose column. A second page holds a terminal strip X1 whose terminals 10, 2
and 1 each feed a lamp, so each terminal heads a column of its own.

The bug: the columns sorted by their authoring key as plain text, so H10 came before H2 and
terminal 10 before terminal 2, though every list already ran in natural order (model-0149).
The rule: the column order calls `fransys_model.derive`'s `natural_key` over each part of the
key, as the pin and function orders do. Fixed by decision layout-0193.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU


def _build(design: fr.Design) -> fr.BuildResult:
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    cabinet = design.location("CAB", "Cabinet")
    return fr.build(design, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))


def _left_to_right(built: fr.BuildResult, *tags: str) -> list[str]:
    """The tags among `tags` in the order their first symbols stand across the page."""
    at = {}
    for drawing in drawn_pages(built.model).values():
        for text in drawing.texts:
            tag = text.text.removeprefix("-")
            if tag in tags:
                at.setdefault(tag, text.box.x)
    return sorted(at, key=at.__getitem__)


@cache
def _lamps() -> list[str]:
    d = fr.design("demo_parts", place="CAB")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        for tag in ("H10", "H2", "H1"):
            lamp = d.device(tag, "DEMO-LAMP-24")
            d.detail.wire(psu.output["+"], lamp["1"], wire=(BU, 0.5))
            d.detail.wire(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    return _left_to_right(_build(d), "H1", "H2", "H10")


@cache
def _terminals() -> list[str]:
    d = fr.design("demo_parts", place="CAB")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 12)
    for number in (10, 2, 1):
        lamp = d.device(f"P{number}", "DEMO-LAMP-24")
        d.detail.wire(strip[number].inner, lamp.lamp["1"], wire=("WH", 0.75))
    return _left_to_right(_build(d), "P1", "P2", "P10")


def test_loose_lamp_columns_run_h1_h2_h10() -> None:
    assert _lamps() == ["H1", "H2", "H10"]


def test_terminal_columns_run_1_2_10() -> None:
    assert _terminals() == ["P1", "P2", "P10"]
