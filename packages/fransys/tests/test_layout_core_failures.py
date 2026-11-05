"""A drawing set whose core layout raises is one ERROR naming the set; `build` never raises (F2)."""
# The write-refuse-on-CND witness (R1462, R1568) is test_write_refuses_on_connection_not_drawn.py, a row of its own (R1708).

from typing import Any

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_build
from fransys._layout_core import lay_out_on_core
from fransys_el import ProblemError

from electrical_symbols import LIBRARY
from fransys_layout.core import CoreError
from fransys_layout.core.place_y import YCycleError
from fransys_layout.core.topology_cycles import CycleCutError
from fransys_layout.core.topology_split import BundleError
from fransys_model.kernel import Severity

_RAISED = [
    CoreError("plain"),
    CycleCutError("cut"),
    BundleError("bundle"),
    YCycleError("ycycle"),
    KeyError("pin"),
    IndexError("tuple index out of range"),
]


@pytest.mark.parametrize("error", _RAISED, ids=lambda e: type(e).__name__)
def test_a_solve_failure_is_one_error_naming_the_set_and_the_class(error: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object) -> None:
        raise error

    monkeypatch.setattr("fransys_el.lay_out_core.solve", fail)
    built = cabinet_build()
    model = built.model
    laid, findings, _, _ = lay_out_on_core(model, LIBRARY)
    assert laid is model
    (found,) = (f for f in findings if f.severity is Severity.ERROR and f.code == "PLACEMENT_PROBLEM")  # the undrawn nets follow as CND ERRORs
    expect_codes(built, "PLACEMENT_PROBLEM", "CONNECTION_NOT_DRAWN")
    assert "drawing set 1" in found.message
    assert type(error).__name__ in found.message
    assert found.fix


def test_a_problem_error_while_writing_a_set_is_one_error_with_the_known_limit_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_: object, **__: object) -> None:
        subject = "group label 'C1'"
        raise ProblemError(subject, "give the two aspect nodes different labels")

    monkeypatch.setattr("fransys_el.lay_out_core.write_layout_drawn", fail)
    built = cabinet_build()
    expect_codes(built, "PLACEMENT_PROBLEM", "CONNECTION_NOT_DRAWN")
    (found,) = (f for f in lay_out_on_core(built.model, LIBRARY)[1] if f.severity is Severity.ERROR and f.code == "PLACEMENT_PROBLEM")
    assert "group label 'C1'" in found.message
    assert "give the two aspect nodes different labels" in found.message
    assert found.fix.startswith("No call clears this:")


def test_build_returns_the_error_and_write_refuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    def fail(*_: object) -> None:
        msg = "boom"
        raise CoreError(msg)

    monkeypatch.setattr("fransys_el.lay_out_core.solve", fail)
    result = cabinet_build()
    expect_codes(result, "PLACEMENT_PROBLEM", "CONNECTION_NOT_DRAWN")
    with pytest.raises(fr.BuildFailedError):
        fr.write(result, tmp_path / "out")
