"""Field case: a changeover feeds the boundary terminals of two strips, each cabled to a by-others box.
Each terminal also stands on the SYSTEM document; its where-line led with the project title and two labels found no free candidate (KI-1010).
Fixed by model-0466: the line leads with the document code."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import _COVER
from fransys.colours import GNYE

_TB = "DEMO-TBLK-2P-DUAL"
_PINS = ("2", "4", "6", "N")


class _Io(NamedTuple):
    a: tuple[Any, ...]
    b: tuple[Any, ...]


@fr.unit("demo-switchboard", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: Any) -> _Io:
    x1 = d.terminal_strip("X1", _TB, description="Feeder A", pe=_TB)
    x2 = d.terminal_strip("X2", _TB, description="Feeder B", pe=_TB)
    x3 = d.terminal_strip("X3", _TB, description="Supply", pe=_TB)
    with d.function("SW", "Supply changeover"):
        pe = d.terminal_strip("PE", _TB, 5, bridged=True)
        k2 = d.device("K2", "DEMO-CO-4P-24")
        names = ("L1", "L2", "L3", "N")
        supply = tuple(x3.run(n, 2, bridged=True, interface=False) for n in names)
        a = (*(x1.run(n, 2, bridged=True, interface=(1,)) for n in names[:2]), *(x1.run(n, 1, interface=True) for n in names[2:]))
        b = tuple(x2.run(n, 1, interface=True) for n in names)
        mains = d.ac_supply("400V", 230, *(r[1] for r in supply[:3]), n=supply[3][1])
        d.series(mains, k2.co.no, tuple(r[1] for r in a), wire=2.5)
        d.series(mains, k2.co.nc, tuple(r[1] for r in b), wire=2.5)
        x1_pe = x1.run("PE", 1, interface=False)
        x2_pe = x2.run("PE", 1, interface=False)
        d.series(x1_pe, pe[1].outer, wire=(GNYE, 2.5))
        d.series(x2_pe, pe[2].outer, wire=(GNYE, 2.5))
        d.earth(x1_pe[1], x2_pe[1])
    return _Io(tuple(r[1] for r in a), tuple(r[1] for r in b))


def _design() -> tuple[Any, tuple[Any, ...]]:
    d = fr.design("demo_parts")
    d.project(title="Demo plant power and control system", number="P-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-01-01", text="first", created="AB")
    d.location("ROOM", "Switch room")
    d.location("FA", "Field A")
    d.location("FB", "Field B")
    u = d.add(_board, "U1", place="ROOM")
    with d.function("FEED", "Feeders"):
        a7 = d.device("A7", None, external=True, place="FA", pins=_PINS)
        a8 = d.device("A8", None, external=True, place="FB", pins=_PINS)
        for name, ends, box in (("W11", u.a, a7), ("W12", u.b, a8)):
            w = d.cable(name, "DEMO-CBL-8G0.75", external=True)
            d.series(ends, w, tuple(box[p] for p in _PINS))
            w.spare()
    docs = (
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=_COVER),
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-switchboard", cover=_COVER),
    )
    return d, docs


@pytest.mark.parametrize("hide", [True, False])
def test_every_terminal_label_under_the_changeover_is_placed(tmp_path: Any, *, hide: bool) -> None:
    toml = tmp_path / "settings.toml"
    toml.write_text(f"[export]\nhide_pe = {str(hide).lower()}\n")
    d, docs = _design()
    result = fr.build(d, *docs, settings=fr.settings(toml))
    assert [f.message for f in result.findings if f.code == "ANNEX_UNPLACED"] == []
