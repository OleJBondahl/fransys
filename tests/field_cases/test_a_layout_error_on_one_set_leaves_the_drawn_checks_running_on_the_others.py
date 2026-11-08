"""Field case: a layout ERROR on one drawing set must not mask the drawn-page checks of the sets that laid out.
The bug (KI-779, consumer 0.23.1): after KI-773 any layout ERROR skipped every drawn-page check, so a real CONNECTION_NOT_DRAWN went unreported.
Fixed (R1977, R1978): the checks run on every set that laid out, the failed set's ERROR says it was skipped; fr.write still refuses."""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document, unit_document
from fransys_el import placement_sets
from test_a_many_function_device_wired_once_is_never_a_reference_cell_crash import _crash_wide
from test_core_path_lays_out_a_unit_document import _box

if TYPE_CHECKING:
    from pathlib import Path


def _build(tmp_path: Path, *, crash: bool) -> fr.BuildResult:
    d = fr.design("demo_parts", "crash_parts")
    room = d.location("R", "Room")
    if crash:
        d.add(_crash_wide, "U1", place=None)
    room2 = d.location("R2", "Room 2")
    box = d.add(_box, "U2", place="R")
    lamp = d.device("H1", "DEMO-LAMP-24", place="R")
    d.series(box.out.outer, lamp.lamp["1"], wire=("WH", 0.75))
    x9 = d.terminal_strip("X9", "DEMO-TB-2.5", 2, place="R")
    d.series(x9[1].inner, lamp.lamp["2"], wire=("WH", 0.75))
    far = d.device("H2", "DEMO-LAMP-24", place="R2")
    d.series(lamp.lamp["2"], far.lamp["1"], wire=("WH", 0.75))
    d.series(x9[2].inner, far.lamp["2"], wire=("WH", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=tmp_path / "r.md")
    return fr.build(d, cover, cabinet_document(room2), unit_document("demo-core-box"), *([unit_document("crash-wide")] if crash else []))


def _force_drop(monkeypatch: pytest.MonkeyPatch) -> None:
    real = placement_sets._net

    def drop(net: Any, symbols: Any, *rest: Any) -> Any:
        made = real(net, symbols, *rest)
        lamp_cut = made is not None and bool(made.cut) and any(s.startswith("H1") for s in symbols)
        return None if lamp_cut else made

    monkeypatch.setattr(placement_sets, "_net", drop)


def test_a_forced_drop_on_a_good_set_is_reported_beside_a_layout_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _force_drop(monkeypatch)
    result = _build(tmp_path, crash=True)
    expect_codes(result, "WIDER_THAN_PAGE", "PAGE_OVERFLOW", "CONNECTION_NOT_DRAWN")
    skipped = [f for f in fr.check(result) if f.code in {"WIDER_THAN_PAGE", "PAGE_OVERFLOW"}]
    assert skipped
    assert {f.code for f in skipped} == {"WIDER_THAN_PAGE", "PAGE_OVERFLOW"}
    assert all("drawing set 'crash-wide' is not drawn, its drawn-page checks did not run" in f.message for f in skipped)
    assert "CONNECTION_NOT_DRAWN" in {f.code for f in fr.check(result)}
    with pytest.raises(fr.BuildFailedError):
        fr.write(result, tmp_path / "out")


def test_the_same_forced_drop_without_the_layout_error_gives_connection_not_drawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in _build(tmp_path, crash=False).findings}
    _force_drop(monkeypatch)
    expect_codes(_build(tmp_path, crash=False), "CONNECTION_NOT_DRAWN")
