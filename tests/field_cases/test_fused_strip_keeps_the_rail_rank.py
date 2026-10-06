"""Field case: a strip behind a fuse ranks as its rail but draws no power bar.

The engineering shape: a 24 V DC supply on a rail terminal row, a fuse wired from that row to a
terminal strip "valve supply", a lamp fed from the strip, and the lamp's return wired to a 0 V
row. The strip carries no 24 V net of its own.

The bug: a fuse link was `conductive`, so the physical net ran through the fuse and the strip pin
drew a 24 V bar as if it were the supply itself; ranked through the physical net alone, it had no
rank once that link stopped being conductive.

The rule (decision layout-0105, spec electrical-facts F1, CONVENTIONS-V06 V3 and V11): a fuse
link is `protective`. The physical net stops at it, so the strip pin draws no bar (V3), but the
rail closure crosses it, so the pin ranks as 24 V (V11). The return keeps the 0 V bar.
"""

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.derive import net_of, port_potential_rank, port_power_kind
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import functions, items, ports

_VALVE = ("X2", "terminal", "1")


def _build(tmp_path) -> fr.BuildResult:
    """Fuse F1 feeds strip X2 "valve supply" from the 24 V row; lamp P1 returns to the 0 V row."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        fuse = d.device("F1", "DEMO-FUSE-ABAT")
        lamp = d.device("P1", "DEMO-LAMP-24")
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
        zero = d.terminal_strip("X3", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        valve = d.terminal_strip("X2", "DEMO-TB-2.5", 1, description="valve supply")
        d.wire(live[1].outer, fuse["1"], wire=(BU, 0.5))
        d.wire(fuse["2"], valve[1].outer, wire=(BU, 0.5))
        d.wire(valve[1].inner, lamp["1"], wire=(BU, 0.5))
        d.wire(lamp["2"], zero[1].outer, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _port(model, who: str | tuple[str, ...], name: str):
    """The port `name` of the item tagged `who`, or keyed `who` when a terminal has no tag."""
    (item,) = (i for i in items(model).values() if who in (i.tag, i.key))
    fns = {f.id for f in functions(model).values() if f.item == item.id}
    return next(p.id for p in ports(model).values() if p.function in fns and p.name == name)


def test_the_strip_behind_the_fuse_ranks_as_the_rail(tmp_path) -> None:
    model = _build(tmp_path).model
    feed = _port(model, "F1", "1")
    behind = _port(model, "F1", "2")
    strip_pin = _port(model, _VALVE, "internal")
    assert port_potential_rank(model, feed) is not None
    assert port_potential_rank(model, behind) == port_potential_rank(model, feed)
    assert port_potential_rank(model, strip_pin) == port_potential_rank(model, feed)
    assert {s.port: s.rank for f in read_inputs(model).functions for s in f.ports}[
        strip_pin
    ] == port_potential_rank(model, feed)


def test_the_strip_draws_no_rail_bar_and_the_return_draws_the_ground(tmp_path) -> None:
    model = _build(tmp_path).model
    feed = _port(model, "F1", "1")
    behind = _port(model, "F1", "2")
    strip_pin = _port(model, _VALVE, "internal")
    ground = _port(model, "P1", "2")
    assert net_of(model, feed) != net_of(model, behind)  # the physical net stops at the fuse
    assert port_power_kind(model, feed) is PowerKind.SUPPLY
    assert port_power_kind(model, strip_pin) is PowerKind.NONE
    bars = {s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "power-supply"}
    assert feed in bars
    assert not bars & {behind, strip_pin}
    assert port_power_kind(model, ground) is not PowerKind.NONE
