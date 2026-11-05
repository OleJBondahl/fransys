"""Field case: a strip behind a fuse ranks as its rail but draws no power bar.
The bug: a fuse link was conductive, so the strip pin drew a 24 V bar as if it were the supply itself.
Fixed by layout-0105, a fuse link is protective: the physical net stops at it, but the rail closure still ranks the pin 24 V."""

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import net_of, port_potential_rank, port_power_kind
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import functions, items, ports

_VALVE = ("X2", "terminal", "1")


def _build() -> fr.BuildResult:
    """Fuse F1 feeds strip X2 "valve supply" from the 24 V row; lamp P1 returns to the 0 V row."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        fuse = d.device("F1", "DEMO-FUSE-ABAT")
        lamp = d.device("P1", "DEMO-LAMP-24")
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        zero = d.terminal_strip("X3", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        valve = d.terminal_strip("X2", "DEMO-TB-2.5", 1, description="valve supply")
        d.series(live[1].outer, fuse["1"], wire=(BU, 0.5))
        d.series(fuse["2"], valve[1].outer, wire=(BU, 0.5))
        d.series(valve[1].inner, lamp["1"], wire=(BU, 0.5))
        d.series(lamp["2"], zero[1].outer, wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _port(model, who: str | tuple[str, ...], name: str):
    """The port `name` of the item tagged `who`, or keyed `who` when a terminal has no tag."""
    (item,) = (i for i in items(model).values() if who in (i.tag, i.key))
    fns = {f.id for f in functions(model).values() if f.item == item.id}
    return next(p.id for p in ports(model).values() if p.function in fns and p.name == name)


def test_the_strip_behind_the_fuse_ranks_as_the_rail() -> None:
    model = _build().model
    feed = _port(model, "F1", "1")
    behind = _port(model, "F1", "2")
    strip_pin = _port(model, _VALVE, "internal")
    assert port_potential_rank(model, feed) is not None
    assert port_potential_rank(model, behind) == port_potential_rank(model, feed)
    assert port_potential_rank(model, strip_pin) == port_potential_rank(model, feed)


def test_the_strip_draws_no_rail_bar_and_the_return_draws_the_ground() -> None:
    model = _build().model
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
