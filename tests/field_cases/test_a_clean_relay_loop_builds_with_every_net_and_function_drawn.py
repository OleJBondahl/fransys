"""Field case: a circuit whose every net, function, lane wire and set is drawn writes clean.
Shape: a 24 V supply through a fuse and a contact to a coil and a lamp, plus a three-pole breaker, in one unit with a document.
Rule: NET_NOT_DRAWN, FUNCTION_NOT_DRAWN, LANE_WIRE_DROPPED, SET_WITHOUT_PAGE and UNPRINTED_SET are ERRORs (SPEC-022 L1); none fires here."""

from functools import cache
from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from _model_build_cover import unit_document

_CODES = (
    "NET_NOT_DRAWN",
    "FUNCTION_NOT_DRAWN",
    "LANE_WIRE_DROPPED",
    "SET_WITHOUT_PAGE",
    "UNPRINTED_SET",
)


class _Io(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cab(u: fr.Design) -> _Io:
    g1 = u.device("G1", "DEMO-PSU-24")
    dc = u.dc_supply("24VDC", g1.output)
    f1 = u.device("F1", "DEMO-FUSE-DC-160")
    s1 = u.device("S1", "DEMO-CTR-BLOCK-1NO1NC")
    k1 = u.device("K1", "DEMO-CTR-LEADS")
    h1 = u.device("H1", "DEMO-LAMP-24")
    u.series(dc.plus, f1.element, s1.no, u.parallel(k1.coil, h1.lamp), dc.minus, wire=0.75)
    x0 = u.terminal_strip("X0", "DEMO-TB-2.5", 4)
    out = u.terminal_strip("X2", "DEMO-TB-2.5", 3)
    mains = u.ac_supply("400V", 230, x0[1], x0[2], x0[3])
    u.series(mains, u.device("Q1", "DEMO-MCB-3P").element, out, wire=0.75)
    return _Io()


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    return fr.build(d, unit_document("demo-cab"))


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    return _built()


@pytest.mark.parametrize("code", _CODES)
def test_no_drawn_stage_code_fires_and_the_write_succeeds(built: fr.BuildResult, code: str, tmp_path: Path) -> None:
    """Catches a net, function, lane wire, set page or print dropped: the write then raises."""
    assert [f for f in fr.check(built) if f.code == code] == []
    assert any(p.suffix == ".pdf" for p in fr.write(built, tmp_path / "out"))
