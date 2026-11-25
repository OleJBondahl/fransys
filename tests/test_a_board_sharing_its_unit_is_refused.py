"""A board that shares its unit with another top-level device is refused with BOARD_SHARES_UNIT (R2484), never built as a black box.

The shape: a PLC output card sits under a rack board next to a relay; one channel pin is wired to a coil. A board with
no unit is its own unit (R2481) and is not refused (R2496).
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from _model_build_cover import unit_document
from fransys.colours import BU


class _Io(NamedTuple):
    R1: fr.Device


def _rack_and_relay(d: fr.Design) -> _Io:
    rack = d.device("R1", "DEMO-PCB-IO")
    card = d.device("KE1", "DEMO-PLC-DO-2", parent=rack, position=1)
    relay = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(card.do_1["1"], relay.coil["A1"], wire=(BU, 0.5))
    d.series(card.do_2["2"], relay.coil["A2"], wire=(BU, 0.5))
    return _Io(rack)


@fr.unit("demo-shared", revision=1, interface_version=1, date="2026-11-16", text="first", by="XX")
def _shared(u: fr.Design) -> _Io:
    return _rack_and_relay(u)


def test_a_board_beside_another_device_in_a_unit_is_refused_and_names_the_fix() -> None:
    d = fr.design("demo_parts")
    d.add(_shared, "U1")
    result = fr.build(d, unit_document("demo-shared"))
    expect_codes(result, "BOARD_SHARES_UNIT")
    codes = {f.code: f for f in fr.check(result)}
    assert "R1" in codes["BOARD_SHARES_UNIT"].message
    assert "unit of its own" in codes["BOARD_SHARES_UNIT"].message


def test_a_board_with_no_unit_is_its_own_unit_and_is_not_refused() -> None:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    rack = d.device("R1", "DEMO-PCB-IO")
    j1 = d.device("X1", "DEMO-CONN-2P", parent=rack)  # a board is a black box (R2627): a connector of it is what is wired
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(j1["1"], k1.coil["A1"], wire=(BU, 0.5))
    d.series(k1.coil["A2"], j1["2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    assert "BOARD_SHARES_UNIT" not in {f.code for f in result.findings}
    assert "FUNCTION_HALF_CONNECTED" not in {f.code for f in result.findings}
    assert result.findings, "positive half: the build still reports its findings"


@fr.unit("demo-beside", revision=1, interface_version=1, date="2026-11-16", text="first", by="XX")
def _beside(u: fr.Design) -> _Io:
    rack = u.device("R1", "DEMO-PCB-IO")
    j1 = u.device("X1", "DEMO-CONN-2P", parent=rack)
    strip = u.terminal_strip("X9", "DEMO-TB-2.5")
    u.series(j1["1"], strip[1].outer, wire=(BU, 0.5))
    return _Io(rack)


def test_a_shared_board_with_nothing_wired_inside_is_not_refused() -> None:
    d = fr.design("demo_parts")
    d.add(_beside, "U1")
    assert "BOARD_SHARES_UNIT" not in {f.code for f in fr.build(d, unit_document("demo-beside")).findings}
