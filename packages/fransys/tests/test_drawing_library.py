"""The facade writes the model's `layout.drawing_library` record and refuses an authored one."""

from decimal import Decimal

import fransys as fr
import pytest
from fransys._drawing_library import with_drawing_library

from electrical_symbols import LIBRARY
from fransys_model.derive import mm_per_division
from fransys_model.derive.library_grid import divisions
from fransys_model.kernel import Draft, Origin, SchemaError, freeze, make_id
from fransys_model.layout import DrawingLibrary, default_sheet_format, layout_of

pytestmark = pytest.mark.wp("facade")

_ORIGIN = Origin(file="test_drawing_library.py", line=1, note="planted")


def _authored() -> DrawingLibrary:
    key = ("authored", "library")
    return DrawingLibrary(
        id=make_id(DrawingLibrary, key),
        key=key,
        module_mm=Decimal(5),
        divisions=16,
        wire_pitch=8,
        wire_pitch_fine=4,
        font_family="Authored",
        capital_ratio=Decimal(1),
        ascent_ratio=Decimal(1),
        descent_ratio=Decimal(1),
        heights=frozendict({"body": Decimal(1)}),
    )


def _built():
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    return fr.build(d).model


def test_a_built_model_holds_the_library_record_once() -> None:
    model = _built()
    (record,) = layout_of(model, DrawingLibrary).values()
    assert record.divisions == LIBRARY.grid.divisions_per_module == divisions(model)
    assert record.font_family == "DejaVu Sans"


def test_the_record_gives_the_millimetres_of_one_grid_unit() -> None:
    sheet = default_sheet_format()
    assert mm_per_division(_built(), sheet) == sheet.module_mm / 8


def test_a_planted_authored_record_is_refused() -> None:
    draft = Draft()
    draft.extend([_authored()], origin=_ORIGIN)
    with pytest.raises(SchemaError, match=r"layout\.drawing_library"):
        fr.build(draft)


def test_a_model_that_already_holds_the_record_is_refused() -> None:
    once = with_drawing_library(freeze(Draft()))
    with pytest.raises(SchemaError, match=r"layout\.drawing_library"):
        with_drawing_library(once)


def test_the_refusal_comes_before_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    def _no_model(*_args: object) -> None:
        msg = "freeze ran before the authored record was refused"
        raise AssertionError(msg)

    monkeypatch.setattr("fransys.pipeline.freeze", _no_model)
    draft = Draft()
    draft.extend([_authored()], origin=_ORIGIN)
    with pytest.raises(SchemaError, match=r"layout\.drawing_library"):
        fr.build(draft)
