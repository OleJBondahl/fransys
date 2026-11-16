"""Field case: a redundancy module box, fed by two supplies, also carries a service connector wired to a strip terminal.
The bug: the box's sides ranked the connector's pin views, which are not functions, so a KeyError stopped the drawing.
Fixed by layout-0123, the sides rank only the functions the box is made of; the rule is unchanged."""

from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import item_box, wire_nets
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BN, BU


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
    with d.function("G", "Group"):
        psus = [d.device(f"T{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN-NET")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.series(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.series(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.series(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.series(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    d.series(m1.svc["1"], live[2].outer, wire=(BN, 0.5))
    return fr.build(d, unit_document(cab))


@pytest.mark.rule("SERIES-PARALLEL")
def test_the_two_supplies_stand_side_by_side_above_the_module() -> None:
    """Series(Parallel(T1, T2), M1): one column, no CHAIN_REFUSED (it was refused before P2)."""
    built = _built()
    assert "CHAIN_REFUSED" not in {f.code for f in built.findings}
    boxes = [s for d in drawn_pages(built.model).values() for s in d.symbols]
    tops = [s.y for s in boxes if s.key == "generic-box"]
    assert len(tops) == 3
    assert tops.count(min(tops)) == 2, "the two supplies stand on one row"
    assert max(tops) > min(tops), "the module stands below them"


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
def test_two_boxes_wired_below_one_box_stand_in_one_column(monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-997 (R2393 (3), R2399, R2404): a card wired p1, p2 to one box and p3, p4 to another, both below it: one column, every net drawn."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent / "data"))
    d = fr.design("box_side_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        card, *boxes = (d.device(tag, part) for tag, part in (("U1", "BOX-BOTTOM"), ("U2", "BOX-TOP"), ("U3", "BOX-TOP")))
        for n, pin in enumerate(("p1", "p2", "p3", "p4")):
            d.series(card[pin], boxes[n // 2][f"p{n % 2 + 1}"], wire=(BU, 0.5))
    built = fr.build(d, unit_document(cab))
    assert not {f.code for f in built.findings} & {"CHAIN_REFUSED", "CONNECTION_NOT_DRAWN", "WIRE_AS_REFERENCE", "OVERLAP", "OUT_OF_PAGE"}
    card, first, second = (item_box(built.model, f"U{n}") for n in (1, 2, 3))
    assert card.y < first.y == second.y, "the card stands alone on the top row, the boxes share the next"
    assert card.x + card.offsets["p1"] == first.x + first.offsets["p1"], "the first box's wired pin is plumb under the card's"
    hop = [w for _, w in wire_nets(built.model) if w.points[0][0] in (card.x + card.offsets["p3"], card.x + card.offsets["p4"])]
    p3, p4 = sorted(hop, key=lambda w: w.points[0][0])
    assert all(w.points[1][1] > w.points[0][1] == min(y for _, y in w.points) for w in hop), "each wire leaves its pin downward, never round the card"
    assert p4.points[1][1] < p3.points[1][1], "the inner wire takes the upper row, so the hop's wires do not cross"
    assert (p3.points[-1][0], p4.points[-1][0]) == (second.x + second.offsets["p1"], second.x + second.offsets["p2"])
