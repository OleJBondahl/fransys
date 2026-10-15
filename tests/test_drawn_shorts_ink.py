"""render-0012: the drawn-short check reads the ink render draws, no more and no less.

A shared box's mate draws its stub only (its lead draws the box and rail), and a connector box at a
line's end is its connector's drawn body.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK, BN, BU
from fransys_render._ink import page_ink
from fransys_render._markers import markers_on_page

from fransys_model.layout import ConnectorBox, Page, layout_of


class _Io(NamedTuple):
    X1: Any


@fr.unit(
    "flags", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Flags", number="F-1",
)  # fmt: skip
def _flags(d: Any) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 8)
    for i in range(12):
        with d.function(f"C{i + 1:02d}", f"Circuit {i + 1}"):
            k = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            h = d.device(f"H{i + 1}", "DEMO-LAMP-24")
            d.detail.wire(x1[1 + i % 6], k.coil["A1"], wire=("RD", 0.75))
            d.detail.wire(x1[8], k.coil["A2"], wire=("BK", 0.75))
            d.detail.wire(x2[1 + i % 6], k.co_1["11"], wire=("RD", 0.75))
            d.detail.wire(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
            d.detail.wire(h.lamp[2], x2[8], wire=("BU", 0.75))
    return _Io(x1)


@fr.unit(
    "plug", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Plug", number="P-1", class_code="U",
)  # fmt: skip
def _plug(c: Any) -> _Io:
    g1 = c.device("G1", "DEMO-PSU-24")
    j1 = c.device("J1", "DEMO-CONN-4P", interface=True)
    c.detail.wire(g1.output["+"], j1[1], wire=(BU, 0.75))
    c.detail.wire(g1.output["-"], j1[2], wire=(BU, 0.75))
    return _Io(j1)


def _build(d: fr.Design, unit: str, folder: Path) -> Any:
    cover = folder / "cover.md"
    cover.write_text("# c\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, unit, cover=cover)).model


@pytest.fixture(scope="module")
def flags(tmp_path_factory: pytest.TempPathFactory) -> Any:
    d = fr.design("demo_parts")
    d.add(_flags, "U1")
    return _build(d, "flags", tmp_path_factory.mktemp("flags"))


@pytest.fixture(scope="module")
def plug(tmp_path_factory: pytest.TempPathFactory) -> Any:
    d = fr.design("demo_parts")
    unit = d.add(_plug, "U1")
    loom = d.harness("W1")
    cable = d.cable("C1", "DEMO-CBL-4G1.5", length_m=5, parent=loom)
    p1 = d.device("P1", "DEMO-HSG-4F", parent=loom)
    p2 = d.device("P2", "DEMO-HSG-4F", parent=loom)
    d.mate(p1, unit.X1)
    cable.core(BN, p1[1], p2[1])
    cable.core(BK, p1[2], p2[2])
    return _build(d, "plug", tmp_path_factory.mktemp("plug"))


def _pages(model: Any) -> list[Any]:
    return sorted(layout_of(model, Page).values(), key=lambda one: one.id)


def test_a_mate_of_a_shared_box_draws_no_rail_and_no_box(flags: Any) -> None:
    mates = 0
    for page in _pages(flags):
        markers = markers_on_page(flags, page)
        page_mates = sum(1 for one in markers if one.box_x is not None and not one.lead)
        strokes, bodies = page_ink(flags, page)
        assert sum(1 for one in bodies if one.kind == "flag") <= len(markers) - page_mates
        assert sum(1 for one in strokes if one.kind == "rail") <= len(markers) - page_mates
        mates += page_mates
    assert mates, "the circuit has mates"


def test_a_connector_box_is_its_connectors_body(plug: Any) -> None:
    boxes = layout_of(plug, ConnectorBox).values()
    assert boxes, "the circuit draws connector boxes"
    drawn = {
        (one.subject, one.box)
        for page in _pages(plug)
        for one in page_ink(plug, page)[1]
        if one.kind == "symbol"
    }
    for box in boxes:
        assert (box.function, (box.x, box.y, box.x + box.width, box.y + box.height)) in drawn
