"""Field case: a board device holds a relay and two header connectors, one wired to the coil and one wired to nothing.
The bug: the wired header was reported FUNCTION_NOT_DRAWN, because the keep-whole lookup missed a boxed connector's port-keyed pins.
Fixed by el-0053 (KIT-X, R433) and el-0110: the unwired header gave FUNCTION_NOT_WIRED (KI-598); since R3956 it is drawn open, no finding."""

from typing import NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import WH


class _Headers(NamedTuple):
    J1: fr.Device
    X2: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-19", text="first", by="XX")
def _board(u: fr.Design) -> _Headers:
    pcb = u.device("U9", "DEMO-PCB-IO")
    k1 = u.device("K1", "DEMO-RLY-2CO-24", parent=pcb)
    j1 = u.device("X1", "DEMO-CONN-4P", parent=pcb, interface=True)
    j2 = u.device("X2", "DEMO-CONN-4P", parent=pcb, interface=True)
    u.series(j1["1"], k1.coil["A1"], wire=(WH, 0.5))
    u.series(j1["3"], k1.coil["A2"], wire=(WH, 0.5))
    return _Headers(j1, j2)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_board, "U2")
    return fr.build(d, unit_document("demo-board"))


@pytest.fixture(scope="module")
def findings(built: fr.BuildResult) -> list[fr.Finding]:
    return list(fr.check(built))


def test_a_wired_boxed_header_is_drawn_and_reported_so(built: fr.BuildResult, findings: list[fr.Finding]) -> None:
    drawings = drawn_pages(built.model).values()
    texts = {t.text for d in drawings for t in d.texts}
    assert {"-X1:1", "-X1:3"} <= texts  # positive half: the header's pins are on the page
    assert sum(len(d.wires) for d in drawings) >= 2
    assert [f for f in findings if f.code == "FUNCTION_NOT_DRAWN" and "U2-X1" in f.message] == []
    assert [f for f in findings if f.code == "CONNECTION_TO_UNDRAWN"] == []


def test_an_unwired_boxed_header_is_not_wired_and_not_undrawn(built: fr.BuildResult, findings: list[fr.Finding]) -> None:
    assert [f for f in findings if f.code == "FUNCTION_NOT_WIRED"] == []  # X2 is a boundary function: open pins, no finding (model-0426, R3956)
    texts = {t.text for d in drawn_pages(built.model).values() for t in d.texts}
    assert {"-X2:1", "-X2:2", "-X2:3", "-X2:4"} <= texts  # positive half: the open header is on the page
    assert [f for f in findings if f.code == "FUNCTION_NOT_DRAWN" and "U2-X2" in f.message] == []


@fr.unit("demo-led-board", revision=1, interface_version=1, date="2026-11-16", text="first", by="XX")
def _led_board(u: fr.Design) -> _Headers:
    pcb = u.device("U9", "FC-PCB-LED")
    return _Headers(pcb, pcb)


def test_a_port_naming_a_connector_pin_prints_its_own_designation() -> None:
    """KI-1042: a port with `connector = "j1.1"` is the header's pin 1 and prints its one designation (R2488)."""
    d = fr.design("demo_parts", "board_pin_parts")
    d.add(_led_board, "U2")
    result = fr.build(d, unit_document("demo-led-board"))
    found = list(fr.check(result))
    assert [f for f in found if f.code == "PORT_DESIGNATION_DUPLICATE"] == []
    assert found  # positive half: the build reports its other findings, and none is an error
    assert [f for f in found if f.severity is fr.Severity.ERROR] == []
