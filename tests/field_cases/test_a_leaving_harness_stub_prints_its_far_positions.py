"""Field case: a leaving harness-line stub prints where its far devices are drawn.

The engineering shape: one loom runs from a board's header to the lead plugs of two contactors.
The page is too tall, so the unit group cuts: the contactors stand on page N, the board on N+1,
and the loom draws on both, each piece ending in a stub.

The bug: the stub named one far device and no place (`-W1 ← -Q1-J1`), though the loom reaches
-Q1-J1 and -Q2-J1, and an engineer had to search the set for them.
The rule (STUB-POSITIONS P1, P2, R6): a stub lists every far device, each followed by where it is
drawn in the same drawing set, in `derive.position_text`'s form: `-W1 ← -Q1-J1 p1:2C, -Q2-J1 p1:5C`.
A far end drawn in another drawing set keeps the text without a place.

The decision that fixes it: model-0186.
"""

import re
import sys
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import layout_trigger_document

sys.path.insert(0, str(Path(__file__).parent))  # the sibling case whose cut group this reuses
from test_a_harness_line_on_an_overfull_page_still_routes import _built

from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, Page, layout_of

_CELL = r"p\d+:\d+[A-Z]"


def _stub_texts(built: fr.BuildResult) -> dict[int, str]:
    """Each harness stub's printed text by its page number."""
    numbers = {page.id: page.number for page in layout_of(built.model, Page).values()}
    return {
        numbers[one.page]: marker_text(built.model, one)
        for one in layout_of(built.model, LinkMarker).values()
        if "line_stub" in one.key and "W1" in one.key
    }


def test_a_stub_lists_every_far_device_with_its_place() -> None:
    texts = _stub_texts(_built(2))
    first, second = sorted(texts)
    assert re.fullmatch(rf"-W1 ← -Q1-J1 {_CELL}, -Q2-J1 {_CELL}", texts[second])
    assert re.fullmatch(rf"-W1 → -A1-J1 {_CELL}", texts[first])
    assert f"-Q1-J1 p{first}:" in texts[second]
    assert f"-A1-J1 p{second}:" in texts[first]


class _Io(NamedTuple):
    j1: fr.Device


def _board(name: str) -> Any:
    @fr.unit(name, revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def board(u: Any) -> _Io:
        module = u.device("M1", "DEMO-RELAY-MOD-2")
        return _Io(u.device("J1", "DEMO-CONN-4P", parent=module, interface=True))

    return board


@cache
def _across_sets() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    a = d.add(_board("demo-a"), "U1", place="C1")
    b = d.add(_board("demo-b"), "U2", place="C1")
    loom = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    p2 = d.device("P2", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, a.j1)
    d.mate(p2, b.j1)
    cable = d.cable("C1", "DEMO-CBL-4G1.5", parent=loom, place="C1")
    cable.core(1, p1[1], p2[1])
    cable.core(2, p1[2], p2[2])
    return fr.build(d, layout_trigger_document())


def test_a_far_end_in_another_drawing_set_keeps_the_text_without_a_place() -> None:
    """The unit sheets' stubs name an end drawn on the top sheet: no place. The top sheet draws
    both plugs, so its stubs print the place of the far plug (P1)."""
    built = _across_sets()
    texts = sorted(
        marker_text(built.model, one)
        for one in layout_of(built.model, LinkMarker).values()
        if "line_stub" in one.key
    )
    assert texts[:2] == ["-W1 ← +C1-U1-J1", "-W1 ← +C1-U2-J1"]
    assert re.fullmatch(r"-W1 → \+C1-U1-J1 \d+[A-Z]", texts[2])
    assert re.fullmatch(r"-W1 → \+C1-U2-J1 \d+[A-Z]", texts[3])
