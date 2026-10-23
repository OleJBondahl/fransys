"""Field case: the readability reading of a page with all three reference kinds is stable.

The engineering shape: one cabinet page holds a relay whose coil is drawn with a contact image
that lists its one wired contact, a net of three lamp ends drawn as a star with one branch, and a
connector pin wired to a connector on the next page, so the wire is cut into a marker pair.

The need: a reader judging the printed pages asked for the references of each page by kind. The
reading no longer counts references by kind (R239, the `Drawing` carries no such fact); what stays
is the rule of decision 0182: the reading is a function of the build, so the same model gives the
same rows.
"""

import tempfile
from pathlib import Path

import fransys as fr
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
    with d.function("B", "Group B") as second:
        j2 = d.device("J2", "DEMO-CONN-2P")
    wire = (BU, 0.75)
    d.detail.wire(feed.run("L", 1)[1], k1.coil["A1"], wire=wire)
    d.detail.wire(k1.co_1["11"], feed.run("M", 1)[1], wire=wire)
    d.detail.wire(k1.co_1["14"], h1.lamp["1"], wire=wire)
    d.detail.wire(h1.lamp["2"], h2.lamp["2"], wire=wire)
    d.detail.wire(h1.lamp["2"], h3.lamp["2"], wire=wire)
    d.detail.wire(k1.coil["A2"], h2.lamp["1"], wire=wire)
    d.detail.wire(j1.x1["2"], j2.x1["2"], wire=wire)
    d.layout.break_before(second)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Readability\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))


def test_two_builds_of_one_model_give_equal_rows() -> None:
    first, second = _build(), _build()
    assert fr.readability(first) == fr.readability(second)
    assert fr.readability(first) == fr.readability(first)
