"""The 24V net of the 16-input panel reaches every device end in the card's set (R418, layout-0378).

The card's own supply pin hung from the trunk its inputs drive, one y node above and below the
trunk. The whole net left its fan, was cut as one tag pair, and F21, K1, S1, S5, S6 and DI1 got
no wire. Now only the supply pin leaves, and a cut net keeps its wires among one page's ends.
One build of the panel, about 20 s: the case needs the whole corpus circuit.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from fransys_el import lay_out_core

_RUN = Path(__file__).parent.parent / "internal" / "placement_corpus" / "run.py"
DEVICE_ENDS = {
    ("U1-F21", "out"),
    ("U1-K1", "in"),
    ("U1-S1", "in"),
    ("U1-S5", "in"),
    ("U1-S6", "in"),
    ("U1-DI1", "power.24V"),
}


def _layouts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, Any]]:
    spec = importlib.util.spec_from_file_location("corpus_run_r418", _RUN)
    assert spec is not None
    assert spec.loader is not None
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    solved: list[tuple[Any, Any]] = []
    solve = lay_out_core.solve

    def spy(problem: Any, options: Any) -> Any:
        out = solve(problem, options)
        solved.append((problem, out))
        return out

    monkeypatch.setattr(lay_out_core, "solve", spy)
    (circuit,) = (c for c in run.circuits("standard") if c[0] == "panel_di16p")
    run.build("panel_di16p", circuit)
    return solved


def _reached(layout: Any, net_id: str) -> set[tuple[str, str]]:
    points = {
        (pr.page, p)
        for pr in layout.routes.pages
        for w in pr.wires
        if w.net == net_id
        for p in w.points
    }
    return {
        (pl.sym.split()[0], q.pin)
        for pp in layout.placement.pages
        for pl in pp.placed
        for q in pl.pin_xy
        if (pl.page, (q.x, q.y)) in points
    }


@pytest.mark.private_input  # reads internal/ (R462)
def test_every_device_end_of_the_card_supply_net_is_wired(monkeypatch: pytest.MonkeyPatch) -> None:
    found = []
    for problem, layout in _layouts(monkeypatch):
        for net in problem.nets:
            ends = {(p.sym.split()[0], p.pin) for p in net.pins}
            if ends >= DEVICE_ENDS:
                found.append(DEVICE_ENDS - _reached(layout, net.id))
    assert found == [set()]
