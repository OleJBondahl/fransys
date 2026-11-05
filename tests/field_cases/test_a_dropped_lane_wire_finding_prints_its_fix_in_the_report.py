"""Field case: the report of a build that drops a lane wire prints the fix, not a SchemaError.
The bug: LANE_WIRE_DROPPED named no model record, so `fr.report(result)` raised SchemaError (kind Finding) for it.
Fixed by `kernel_findings`; no design drops a lane wire since R868 (the core turns a free hub), so the drop is forced."""
# CONNECTION_NOT_DRAWN 3 per default-salt build set (FORCED_FAILURES): forced core failure, asserted through expect_codes.

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys.colours import WH

from fransys_layout.core import route_wires

if TYPE_CHECKING:
    from pathlib import Path

_WIRE = (WH, 0.5)


class _Io(NamedTuple):
    pass


@fr.unit("fc-lane", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _build(d: fr.Design) -> _Io:
    strip = d.terminal_strip("X1", None, 8, external=True)
    with d.function("CTRL", "Control"):
        relay = d.device("K1", "DEMO-RLY-2CO-24")
        hold = d.device("Q1", "DEMO-RLY-2CO-24")
        button = d.device("S1", "DEMO-PB-NO")
        load = d.device("Y1", "DEMO-RLY-2CO-24")
        d.series(strip[1].outer, relay.coil, strip[2].outer, wire=_WIRE)
        d.series(hold.coil, relay.co_1.nc, button.sw, wire=_WIRE)
        d.series(strip[5].outer, hold.coil, wire=_WIRE)
        d.series(button.sw, strip[3].outer, wire=_WIRE)
        d.series(relay.co_1.no, load.coil, wire=_WIRE)
        d.series(load.coil, strip[4].outer, wire=_WIRE)
    return _Io()


def _result(root: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_build, "U1")
    (root / "cover.md").write_text("# cover\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "fc-lane", cover=root / "cover.md")
    result = fr.build(d, document)
    with pytest.raises(fr.BuildFailedError):  # the write runs the layout that holds the finding
        fr.write(result, root / "out", intermediates=root / "inter")
    return result


def test_a_dropped_lane_wire_names_its_cell_and_the_report_prints_the_fix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route_wires, "_between", lambda env, col, i, cells: route_wires._dropped(env, col, i, cells, "has a facing pin on no net"))
    result = _result(tmp_path)
    dropped = [f for f in result.findings if f.code == "LANE_WIRE_DROPPED"]
    expect_codes(result, "LANE_WIRE_DROPPED", "CONNECTION_NOT_DRAWN")
    assert all(f.subjects for f in dropped)
    report = fr.report(result)
    assert "Put the facing pins of -U1-" in report
    assert "<subject>" not in report
