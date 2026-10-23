"""`unread_hint_findings` (SW9, el-0002): one WARNING per authored `SideHint` the core ignores."""

from typing import NamedTuple

import fransys as fr
from fransys_el import unread_hint_findings

from fransys_model.derive import function_designation
from fransys_model.kernel import Model, Severity
from fransys_model.layout import SideHint, layout_of


class _Io(NamedTuple):
    X1: fr.Device
    X2: fr.Device


@fr.unit("demo-unread", revision=1, interface_version=1, date="2026-10-18", text="t", by="XX")
def _board(d: fr.Design) -> _Io:
    return _Io(
        d.device("X1", "DEMO-CONN-2P", interface=True),
        d.device("X2", "DEMO-CONN-2P", interface=True),
    )


def _model(*, hint: bool) -> Model:
    d = fr.design("demo_parts", place="C1")
    io = d.add(_board, "U1", unused=("X1", "X2"))
    if hint:
        d.layout.side(io.X1, fr.ABOVE)
    return fr.build(d).model


def test_one_side_hint_gives_one_warning_naming_its_function() -> None:
    model = _model(hint=True)
    (hint,) = layout_of(model, SideHint).values()
    (found,) = unread_hint_findings(model)
    assert (found.code, found.severity) == ("HINT_NOT_READ", Severity.WARNING)
    assert found.subjects == (hint.function,)
    assert "d.layout.side" in found.message
    assert function_designation(model, hint.function) in found.message
    assert found.fix.startswith("No call clears this:")


def test_no_side_hint_gives_none() -> None:
    assert unread_hint_findings(_model(hint=False)) == ()
