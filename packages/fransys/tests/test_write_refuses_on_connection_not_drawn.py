"""The release bar's standing witness (R1462, R1568): CONNECTION_NOT_DRAWN as an ERROR makes `fr.write` raise and write nothing.
The finding is forced, so this file's one build carries it by its input (R1708); it was in test_layout_core_failures."""
# CONNECTION_NOT_DRAWN 54 per default-salt build set (FORCED_FAILURES): forced core failure, asserted through expect_codes.

from typing import Any

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_build
from fransys_el import drawn_nets
from fransys_el.set_findings import _INFO


def test_write_refuses_on_connection_not_drawn_and_writes_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setattr(drawn_nets, "_verdict", lambda _net, members, *_: (members[:1], members[1:], 2))
    result = cabinet_build()
    expect_codes(result, "CONNECTION_NOT_DRAWN")
    out = tmp_path / "out"
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.write(result, out)
    assert {f.code for f in raised.value.findings} == {"CONNECTION_NOT_DRAWN"}
    assert not out.exists() or not any(out.iterdir())


def test_write_refuses_on_dangling_wire_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """KI284-FLIP (R1669): DANGLING_WIRE_END is an ERROR too; a forced finding of it makes `fr.write` raise and write nothing."""
    codes = ("DANGLING_WIRE_END",)
    monkeypatch.setattr("fransys_el.lay_out_core.drawing_sweep", lambda *_: tuple(_INFO[c].finding((), "forced") for c in codes))
    built = cabinet_build()
    expect_codes(built, *codes)
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.write(built, tmp_path / "out")
    assert {f.code for f in raised.value.findings} == set(codes)
    assert not any((tmp_path / "out").rglob("*"))
