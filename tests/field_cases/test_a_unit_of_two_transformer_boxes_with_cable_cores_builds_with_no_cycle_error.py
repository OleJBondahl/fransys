"""Field case TBOX-CYCLE: a unit of two transformer-box parts wired by cable cores and a 2-pole breaker builds with no PLACEMENT_PROBLEM.
The bug (0.23.12): a chain walked T1 twice (T1, K1, T1), a CycleCutError. Fixed: a chain visits each symbol once (layout-0576)."""

import re
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

from fransys_model.kernel import Severity
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    pass


@fr.unit("tbox-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    x1, x3, x4 = (u.terminal_strip(n, "DEMO-TB-2.5", 2) for n in ("X1", "X3", "X4"))
    t1, t2 = u.device("T1", "TBOX-TRAFO"), u.device("T2", "TBOX-TRAFO")
    k, q = u.device("K1", "DEMO-RLY-2CO-24"), u.device("Q1", "DEMO-MCB-2P")
    w1 = u.cable("W1", "DEMO-CBL-3X0.34", length_m=1)
    w1.core(1, x1[1].inner, t1.primary["1U"])
    w1.core(2, x1[2].inner, t1.primary["1V"])
    w2 = u.cable("W2", "DEMO-CBL-3X0.34", length_m=1)
    w2.core(1, t1.secondary["2U"], k.coil["A1"])
    w2.core(2, t1.secondary["2V"], k.coil["A2"])
    u.series(x3[1].inner, t2.primary["1U"], wire=("BK", 0.75))
    u.series(x3[2].inner, t2.primary["1V"], wire=("BK", 0.75))
    u.series(t2.secondary["2U"], q.pole_1["1"], wire=("BK", 0.75))
    u.series(t2.secondary["2V"], q.pole_2["3"], wire=("BK", 0.75))
    u.series(q.pole_1["2"], x4[1].inner, wire=("BK", 0.75))
    u.series(q.pole_2["4"], x4[2].inner, wire=("BK", 0.75))
    return _Open()


def test_the_unit_builds_with_no_placement_error(tmp_path: Path) -> None:
    d = fr.design("demo_parts", "tbox_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    result = fr.build(d, unit_document(cab), unit_document(d.add(_cab, "U1")))
    errors = [f for f in result.findings if f.severity == Severity.ERROR]
    assert not errors, [(f.code, str(f.message)[:200]) for f in errors]
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")
    texts = [
        t
        for p in layout_of(result.model, Page).values()
        for t in re.findall(r">([^<>]*)</text>", (tmp_path / "inter" / f"layout.page-{p.id.value}.svg").read_text("utf-8"))
    ]
    assert (texts.count("-T1"), texts.count("-T2")) == (1, 1)  # each transformer body is drawn once
