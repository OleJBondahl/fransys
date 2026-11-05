"""`placement_chains.anchored`: the box-drawn ends of a bundle's series, from the drawn wires."""

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU
from fransys_el import build, house_conventions, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import topology_orient


@pytest.mark.rule("FLOW-DOWN")
def test_chains_in_one_bundle_wired_to_box_pins_on_n_and_s_turn_each_by_its_own_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catches the bundle sum turning a chain against its box pin: six contactors on a card, N pins 1-3 and S pins 4-6.

    A lamp whose loop through a terminal returns to the card's other side anchors nothing.
    The bundle sums come out of both signs; only the N-pin chains anchor, and no wire runs over another.
    """
    signs: list[bool] = []
    flips = topology_orient._group_flips
    monkeypatch.setattr(topology_orient, "_group_flips", lambda *a: signs.append(flips(*a)) or signs[-1])
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC inputs"):
        module = d.device("K1", "DEMO-PLC-DI-16")
    source = d.device("A1", "DEMO-CTRL-8")
    for group, channels in {"A": (1, 4), "B": (2, 5), "C": (3, 6)}.items():
        with d.function(group, f"Group {group}"):
            for n in channels:
                contactor = d.device(f"Q{n}", "DEMO-CTR-3P-NC")
                d.series(source.X1[str(n)], contactor.aux["14"], wire=(BU, 0.5))
                d.series(contactor.aux["13"], getattr(module, f"di_{n}")[str(n)], wire=(BU, 0.5))
    with d.function("R", "Ring"):
        ring, lamp = d.device("K2", "DEMO-PLC-DI-16P"), d.device("H9", "DEMO-LAMP-24")
        feed = d.device("G9", "DEMO-PSU-24")
    d.series(feed.output["+"], ring.power["24V"], wire=(BU, 0.5))
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN")
    d.series(ring.power["0V"], lamp["1"], wire=(BU, 0.5))
    d.series(lamp["2"], strip[1].inner, wire=(BU, 0.5))
    d.series(ring.di_1["1"], strip[1].inner, wire=(BU, 0.5))
    fr.build(d, cabinet_document(cab))
    assert set(signs) == {True, False}
    built = fr.build(d)
    problem, _ = build(built.model, symbol_kit(built.model, LIBRARY), house_conventions(fr.settings().layout, LIBRARY, text_height=8), LIBRARY)
    anchored = {s.parts[0] for s in problem.facts.series if s.anchor}
    assert {str(a).split(" ")[0] for a in anchored} == {
        "Q1",
        "Q2",
        "Q3",
    }  # not the lamp: its N pin and, through the terminal, an S pin reach the same box (R932)
