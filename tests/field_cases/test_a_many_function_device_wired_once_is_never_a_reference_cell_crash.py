"""Field case: a gas monitor joined to an 80-channel analog controller by one wire, with a unit document at A3.
The bug (KI-773 REFCELL-CRASH, consumer 0.23.0): the controller's unwired channels fill one row past the frame; `write_membership._row` raised
`ReferenceCellError` before the layout's ERROR was judged. Fixed: the ERROR stops the build before any output step (designer R1945)."""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import unit_document


class _Io(NamedTuple):
    B1: Any


@fr.unit("crash-wide", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Crash wide", number="C-1")
def _crash_wide(u: Any) -> _Io:
    with u.function("F1", "Monitoring"):
        monitor = u.device("B1", "FLD-GAS-MONITOR")
        controller = u.device("A1", "FLD-AI-CTRL-80")
    u.series(monitor.X1["1"], controller.ai_1["ANALOG_INPUT_01_P"], wire=("BK", 1.0))
    return _Io(B1=monitor)


def test_the_layout_error_stops_the_build_and_nothing_is_written(tmp_path: Path) -> None:
    design = fr.design("demo_parts", "crash_parts")
    design.add(_crash_wide, "U1", place=None)
    result = fr.build(design, unit_document("crash-wide"))
    expect_codes(result, "WIDER_THAN_PAGE", "PAGE_OVERFLOW")
    assert {f.code for f in fr.check(result) if f.severity.name == "ERROR"} == {
        "WIDER_THAN_PAGE",
        "PAGE_OVERFLOW",
    }  # R1996: the set's pages are returned, so the list checks run too
    out = tmp_path / "out"
    with pytest.raises(fr.BuildFailedError):
        fr.write(result, out)
    assert not [p for p in out.rglob("*") if p.is_file()]
