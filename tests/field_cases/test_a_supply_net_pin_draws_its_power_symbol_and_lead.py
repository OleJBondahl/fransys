"""Field case: a lamp on a DC supply's rail draws its supply-net pin with a power symbol and a lead.
The bug: the page carried no power symbol and no lead, so the supply-net pins printed bare.
Fixed by el-0045 (designer R285, R293), each PowerSymbol is drawn at its origin with a lead to the pin (rule POWER-NET)."""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BU

from fransys_model.layout import PowerSymbol, layout_of

if TYPE_CHECKING:
    from pathlib import Path


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    with d.function("G0", "Supply"):
        live = d.terminal_strip("X10", "DEMO-TB-2.5", 4).run("P", 4, bridged=True, rail=True)
        rail = d.terminal_strip("X11", "DEMO-TB-2.5", 4).run("M", 4, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        q = d.device("Q3", "DEMO-CTR-3P-NC")
        h = d.device("H3", "DEMO-LAMP-24")
        d.series(live, q.aux, h.lamp, rail, wire=(BU, 0.5))
        d.series(live, q.coil, rail, wire=(BU, 0.5))
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, d.location("CAB", "Cabinet"), cover=tmp_path / "c.md")
    return fr.build(d, doc)


def test_each_power_symbol_is_drawn_with_a_lead_from_its_pin(tmp_path: Path) -> None:
    result = _build(tmp_path)
    records = list(layout_of(result.model, PowerSymbol).values())
    assert {r.symbol for r in records} >= {"power-supply", "ground"}
    drawn = [s for d in result.drawings.values() for s in d.symbols]
    for r in records:
        assert any((s.key, s.x, s.y) == (r.symbol, r.x, r.y) for s in drawn), r.symbol
