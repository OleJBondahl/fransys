"""Field case: a bank of sixteen relays, wider than the page and fed from one controller's pins, builds.
The bug: a hosted cell's lane was read through its host in one step, so a host that was itself hosted raised KeyError in lane_of.
Fixed by layout-0232, a hosted cell takes the lane of the first cell up its host chain that has one."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
import ring_cases
from _bank_case import built_bank
from _model_build_cover import unit_document
from fransys_el.drawing_invariants import page_overlaps

from fransys_model.layout import Page, layout_of


def test_sixteen_relays_fed_from_one_controller_build_and_take_several_pages() -> None:
    """The build returns, the bank takes more than one page, and it raises no ERROR finding."""
    built = built_bank(16)
    assert len(layout_of(built.model, Page)) > 1
    assert [f for f in fr.check(built) if f.severity.name == "ERROR"] == []


def test_no_lane_runs_on_the_content_box_edge_so_no_junction_dot_leaves_the_page() -> None:
    """The bank's net lanes keep one wiring step inside the box, so the check holds no OUT_OF_PAGE (G09-PAGE, R1300)."""
    assert [f for f in fr.check(built_bank(16)) if f.code == "OUT_OF_PAGE"] == []


class _Io(NamedTuple):
    feed: fr.TerminalStrip


# KI-569 (TEXT-IN-LOOP-T7, R1497): the chained N=10 bank loses one fan to a label keep in round 1 and the re-cut with its tag pair makes one page.
# The coarser-module twin of this pin went with the sheet setting (R1458, R1464); when T7 routes the fan, change this to the page count it gives.
def test_a_chained_bank_of_ten_takes_one_page_until_t7_routes_its_fan() -> None:
    @fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
        back = u.terminal_strip("X2", "DEMO-TB-2.5", 8)
        with u.function("PLC", "Controller"):
            controller = u.device("A1", None, pins=tuple(f"CH{j:02d}-" for j in range(1, 17)), external=True)
        ends: dict[Any, Any] = {}
        for i in range(10):
            with u.function(f"R{i + 1}", f"Relay {i + 1}"):
                relay = u.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
                u.series(ends.get(("feed", i % 4), feed[1 + i % 4]), relay.coil["A1"], wire=("WH", 0.75))
                u.series(controller[f"CH{i % 16 + 1:02d}-"], relay.coil["A2"], wire=("BU", 0.75))
                ends[("feed", i % 4)] = relay.coil["A1"]
                lamp = u.device(f"P{i + 1}", "DEMO-LAMP-24")
                u.series(relay.co_1["14"], lamp.lamp[1], wire=("WH", 0.75))
                u.series(ends.get(("back", i % 6), back[1 + i % 6]), relay.co_1["11"], wire=("WH", 0.75))
                u.series(lamp.lamp[2], ends.get("lamp", back[7]), wire=("BU", 0.75))
                ends[("back", i % 6)], ends["lamp"] = relay.co_1["11"], lamp.lamp[2]
        return _Io(feed)

    d = fr.design("demo_parts")
    d.add(bank, "U1")
    built = fr.build(d, unit_document("demo-bank"), settings=fr.settings(paper={fr.PageKind.SCHEMATIC: "A3", fr.PageKind.BLOCK_DIAGRAM: "A3"}))
    assert len(layout_of(built.model, Page)) == 1


# BANK-PIECES-JOINED (R1711, R1713): on main size 60 lost five connections; a piece apart from its group is joined by a loop reference.
# R1722: at 56 the handed link was tagged, its in-page ends never routed, and two connections went undrawn.
# R1727: at 47 the handed link stayed on one page, got no planned tag, and its fallback tag found no stand.
@pytest.mark.parametrize("n", [47, 56, 60])
def test_a_bank_draws_every_connection(n: int) -> None:
    built = built_bank(n)
    assert [f for f in (*built.findings, *fr.check(built)) if f.code == "CONNECTION_NOT_DRAWN"] == []


# KI-640 (R1731): bank of 40, loop-placed reference markers overlap on page 4f2c6ea0 (CH09 / -K41); gap row GAP-FLIP-640.
def test_no_reference_marker_overlaps_another_on_the_bank_of_forty() -> None:
    drawings = ring_cases.built_bank(40).drawings.values()
    assert [m for d in drawings for m in page_overlaps(d) if m == "reference-marker / reference-marker"] == []
