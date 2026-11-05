"""Field case: a box with a coil on a pin of each half, the two coils wired to each other (CROSS-HALF-TAGS).
The bug: the coils stand in one column hung on the S half, so the N pin's wire ran round the box and the engineer got no hint.
Fixed by layout-0440 and el-0081: the net is a tag pair, one WARNING."""

from functools import cache
from itertools import pairwise
from typing import Any

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU

PINS = ("P1", "P2", "P3", "P4")


def _doc(cab):
    return unit_document(cab)


@cache
def _built(*, halves: bool) -> fr.BuildResult:
    """Coils K1 and K2 on P1 and P4 and wired to each other; `halves` False puts both on P3 and P4, the S half."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Controller"):
        box = d.device("A1", None, pins=PINS, external=True)
    with d.function("B", "Relays"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        k2 = d.device("K2", "DEMO-RLY-2CO-24")
        d.series(box["P1" if halves else "P3"], k1.coil["A1"], wire=(BU, 0.5))
        if not halves:  # two lone coils fill the N half
            for pin, tag in (("P1", "K3"), ("P2", "K4")):
                coil = d.device(tag, "DEMO-RLY-2CO-24").coil
                d.series(box[pin], coil["A1"], wire=(BU, 0.5))
                d.series(coil["A2"], k1.coil["A2"], wire=(BU, 0.5))
        d.series(box["P4"], k2.coil["A1"], wire=(BU, 0.5))
        d.series(k1.coil["A2"], k2.coil["A2"], wire=(BU, 0.5))
    return fr.build(d, _doc(cab))


def _wires(result: fr.BuildResult) -> list[Any]:
    return [w for drawing in result.drawings.values() for w in drawing.wires]


def _markers(result: fr.BuildResult) -> list[Any]:
    return [s for drawing in result.drawings.values() for s in drawing.symbols if s.key.startswith("marker")]


@pytest.mark.rule("CROSS-HALF-TAGS")
def test_the_net_across_the_halves_is_two_tags_and_no_wire_round_the_box() -> None:
    result = _built(halves=True)
    assert _wires(result)
    assert all(len(w.points) == 2 for w in _wires(result))
    assert len(_markers(result)) == 2


@pytest.mark.rule("CROSS-HALF-TAGS")
def test_the_net_across_the_halves_warns_once_and_names_pins_below() -> None:
    found = [f for f in _built(halves=True).findings if f.code == "TAG_ACROSS_BODY"]
    assert len(found) == 1


def test_control_both_coils_on_one_half_stay_wires() -> None:
    result = _built(halves=False)
    assert not _markers(result)
    assert not [f for f in result.findings if f.code == "TAG_ACROSS_BODY"]


@cache
def _with_terminal() -> fr.BuildResult:
    """Box pins P1 and P4 on both halves wired to one terminal: the net holds a terminal."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Controller"):
        box = d.device("A1", None, pins=PINS, external=True)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2)
    d.series(box["P1"], x1[1], wire=(BU, 0.5))
    d.series(box["P4"], x1[1], wire=(BU, 0.5))
    return fr.build(d, _doc(cab))


@pytest.mark.rule("CROSS-HALF-TAGS")
def test_a_net_with_a_terminal_across_the_halves_is_never_a_tag_pair() -> None:
    """TERMINAL-COPIES: a terminal copies per page, never a reference."""
    result = _with_terminal()
    assert _wires(result)
    assert not [s for s in _markers(result) if s.key.startswith("marker")]
    assert not [f for f in result.findings if f.code == "TAG_ACROSS_BODY"]


@cache
def _overfull_and_crossed() -> fr.BuildResult:
    """A 40-pin box of coils too wide for its card, with the K1 and K2 coils on the first and last pin wired to each other."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    pins = tuple(f"P{i}" for i in range(1, 41))
    with d.function("PLC", "Controller"):
        box = d.device("A1", None, pins=pins, external=True)
    with d.function("B", "Relays"):
        coils = [d.device(f"K{i}", "DEMO-RLY-2CO-24").coil for i in range(1, 41)]
        for pin, coil in zip(pins, coils, strict=True):
            d.series(box[pin], coil["A1"], wire=(BU, 0.5))
        d.series(coils[0]["A2"], coils[-1]["A2"], wire=(BU, 0.5))
        for left, right in pairwise(coils[1:-1]):
            d.series(left["A2"], right["A2"], wire=(BU, 0.5))
    return fr.build(d, _doc(cab))


@pytest.mark.rule("CROSS-HALF-TAGS")
def test_a_box_both_overfull_and_crossed_gets_both_findings() -> None:
    """The tag pair finding is the core's own at the decision, so CARD_OVERFULL on the box does not hide it."""
    codes = {f.code for f in _overfull_and_crossed().findings}
    assert {"CARD_OVERFULL", "TAG_ACROSS_BODY"} <= codes


def test_a_box_both_overfull_and_crossed_leaves_no_marker_unplaced() -> None:
    """The lost link's tag pair is planned by the cut, so the first row has room for the tags above its pins (layout-0508)."""
    assert not [f for f in _overfull_and_crossed().findings if f.code == "MARKER_UNPLACED"]


def test_a_net_across_a_full_width_card_is_drawn_whole() -> None:
    """KI-404: K2 to K13 stand on the card's N edge, K21 under it, and the card spans the page: the router has no path."""
    result = _overfull_and_crossed()
    assert not [f for f in result.findings if f.code == "CONNECTION_NOT_DRAWN"]
