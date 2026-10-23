"""A drawing set whose core layout raises is one ERROR naming the set; `build` never raises (F2)."""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import cabinet_document
from demo_designs import cabinet_design
from fransys._layout_core import lay_out_on_core
from fransys_el import ProblemError
from fransys_render import DrawError

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


def _model() -> Any:
    parts = fransys_parts.load("demo_parts")
    document = cabinet_document(fransys_author.Design(parts).location("C1", "Demo cabinet"))
    return fr.build(parts, cabinet_design(parts).draft(), document).model


@pytest.mark.parametrize("error", _RAISED, ids=lambda e: type(e).__name__)
def test_a_solve_failure_is_one_error_naming_the_set_and_the_class(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object) -> None:
        raise error

    monkeypatch.setattr("fransys_el.lay_out_core.solve", fail)
    model = _model()
    laid, findings, _, _ = lay_out_on_core(model, LIBRARY)
    assert laid is model
    (found,) = (f for f in findings if f.severity is Severity.ERROR)
    assert found.code == "PLACEMENT_PROBLEM"
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
    (found,) = (f for f in lay_out_on_core(_model(), LIBRARY)[1] if f.severity is Severity.ERROR)
    assert "group label 'C1'" in found.message
    assert "give the two aspect nodes different labels" in found.message
    assert found.fix.startswith("No call clears this:")


def test_build_returns_the_error_and_write_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    def fail(*_: object) -> None:
        msg = "boom"
        raise CoreError(msg)

    monkeypatch.setattr("fransys_el.lay_out_core.solve", fail)
    parts = fransys_parts.load("demo_parts")
    document = cabinet_document(fransys_author.Design(parts).location("C1", "Demo cabinet"))
    result = fr.build(parts, cabinet_design(parts).draft(), document)
    assert any(f.code == "PLACEMENT_PROBLEM" for f in result.findings)
    with pytest.raises(fr.BuildErrors):
        fr.write(result, tmp_path / "out")


def test_a_draw_error_is_one_error_per_set_and_build_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_: object, **__: object) -> None:
        msg = "marker 'm' faces 'Q'"
        raise DrawError(msg)

    monkeypatch.setattr("fransys._layout_core.svg", fail)
    (found,) = (f for f in lay_out_on_core(_model(), LIBRARY)[1] if f.severity is Severity.ERROR)
    assert found.code == "DRAW_PROBLEM"
    assert "drawing set 1" in found.message
    assert "marker 'm' faces 'Q'" in found.message
    assert found.fix
