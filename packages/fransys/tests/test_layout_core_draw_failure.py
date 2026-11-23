"""A drawing set whose render raises a `DrawError` is one DRAW_PROBLEM error naming the set; `build` never raises (F2)."""

import fransys as fr
import fransys_parts
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from demo_designs import cabinet_design
from fransys._layout_core import lay_out_on_core
from fransys_author.design import Design
from fransys_render import DrawError
lazy import pytest

from electrical_symbols import LIBRARY
from fransys_model.kernel import Severity


def test_a_draw_error_is_one_error_per_set_and_build_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> None:
        msg = "marker 'm' faces 'Q'"
        raise DrawError(msg)

    monkeypatch.setattr("fransys._layout_core.svg", fail)
    parts = fransys_parts.load("demo_parts")
    built = fr.build(parts, cabinet_design(parts).draft(), cabinet_document(Design(parts).location("C1", "Demo cabinet")))
    expect_codes(built, "DRAW_PROBLEM")
    (found,) = (f for f in lay_out_on_core(built.model, LIBRARY)[1] if f.severity is Severity.ERROR)
    assert "drawing set 1" in found.message
    assert "marker 'm' faces 'Q'" in found.message
    assert found.fix
