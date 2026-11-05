"""Field case: a cabinet page holds a relay, a three-lamp star net and a connector cut across pages, each reference kind present.
The bug: none; a reader asked for references by kind, and R239 dropped that count, so only the stable reading remains.
Fixed by decision 0182, the reading is a function of the build, so the same model gives the same rows."""

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Readability", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("A", "Group A"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        feed = d.terminal_strip("X1", "DEMO-TB-2.5")
        h1, h2, h3 = (d.device(f"H{n}", "DEMO-LAMP-24") for n in (1, 2, 3))
        j1 = d.device("J1", "DEMO-CONN-2P")
    with d.function("B", "Group B"):
        j2 = d.device("J2", "DEMO-CONN-2P")
    wire = (BU, 0.75)
    d.series(feed.run("L", 1)[1].inner, k1.coil["A1"], wire=wire)
    d.series(k1.co_1["11"], feed.run("M", 1)[1].inner, wire=wire)
    d.series(k1.co_1["14"], h1.lamp["1"], wire=wire)
    d.series(h1.lamp["2"], h2.lamp["2"], wire=wire)
    d.series(h1.lamp["2"], h3.lamp["2"], wire=wire)
    d.series(k1.coil["A2"], h2.lamp["1"], wire=wire)
    d.series(h3.lamp["1"], d.device("G1", None, external=True, pins=("P",)).P, wire=wire)
    d.series(j1.x1["2"], j2.x1["2"], wire=wire)
    return fr.build(d, unit_document(cabinet))


def test_two_builds_of_one_model_give_equal_rows() -> None:
    first, second = _build(), _build()
    assert fr.readability(first) == fr.readability(second)
    assert fr.readability(first) == fr.readability(first)
