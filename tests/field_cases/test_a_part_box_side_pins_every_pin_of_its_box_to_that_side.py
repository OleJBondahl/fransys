"""Field case: a small signal box draws its pins half over half; a part may pin every pin of a function to one side (BOX-SIDES, designer R2060).
A part's `box_side = "top"` puts every drawn pin of the box on N, `"bottom"` on S; another value is an ENUM_VALUE error naming the function."""

from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import item_box
from _model_build_cover import unit_document
from fransys.colours import BU

DATA = Path(__file__).parent / "data"
_PINS = ("p1", "p2", "p3", "p4")


def _model(part: str) -> fr.Model:
    d = fr.design("box_side_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "BOX-TB", 4).run("L", 4)
    with d.function("G", "Group"):
        box = d.device("U1", part)
        for n, pin in enumerate(_PINS, start=1):
            d.series(strip[n].outer, box[pin], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab)).model


@pytest.fixture(scope="module", autouse=True)
def _library():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(DATA))
        yield


@pytest.mark.parametrize(("part", "side"), [("BOX-TOP", "n"), ("BOX-BOTTOM", "s")])
def test_every_pin_of_a_pinned_box_is_on_its_side(part: str, side: str) -> None:
    sides = item_box(_model(part), "U1").sides
    assert {sides[pin] for pin in _PINS} == {side}
    assert len(sides) == len(_PINS)
