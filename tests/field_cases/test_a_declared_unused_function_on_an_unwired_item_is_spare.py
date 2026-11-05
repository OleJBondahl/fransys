"""Field case FNW-SPARE (KI-585): a device wholly unwired but for a function declared `unused=` that the interface does not hold.
The bug: the declared function was reported FUNCTION_NOT_WIRED (WARNING) though its remedy, `unused=`, was applied.
Fixed by model-0420 (designer R1528), a function declared unused is a spare function whatever its item's wiring."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document


class _Io(NamedTuple):
    pass


def _built(*, declared: bool) -> fr.BuildResult:
    @fr.unit("io", revision=1, interface_version=1, date="2026-11-01", text="x", by="AB")
    def unit(u: Any) -> _Io:
        board = u.device("B1", "DEMO-PCB-IO")
        u.device("A1", "DEMO-IO-2X", parent=board, interface=("x1",), unused=("x2",) if declared else False)
        return _Io()

    d = fr.design("demo_parts")
    d.add(unit, "U1")
    return fr.build(d, unit_document("io"))


def _not_wired(result: fr.BuildResult) -> list[str]:
    return [f.message for f in result.findings if f.code == "FUNCTION_NOT_WIRED" and "A1:x2" in f.message]


@pytest.mark.rule("NO-SILENT-DROP")
def test_a_declared_unused_function_is_spare_not_not_wired() -> None:
    assert _not_wired(_built(declared=True)) == []
    assert [f.severity for f in _built(declared=True).findings if f.code == "SPARE_FUNCTIONS"] == [fr.Severity.INFO]


def test_the_undeclared_control_still_warns() -> None:
    assert len(_not_wired(_built(declared=False))) == 1
