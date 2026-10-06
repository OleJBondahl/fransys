"""Field case: a box that feeds one pin group of another box stands over that group.

The engineering shape: two power supplies side by side, each with an AC input on top and a DC
output below, and a redundancy module with one input group per supply and an output to the 24 V
and 0 V rails. Each supply's output is wired plus to plus and minus to minus to its own group.

The bug: the module's groups do not stand under their feeders, so the supply wires bend or cross
on the way to the module, and a supply authored second can end up over the first one's group.
The rule (spec CONVENTIONS-V06 V1, decision layout-0107): a box fed by one box over a whole pin
group is placed so pin stands under pin, and every wire between them is one vertical segment.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _plant(d, order: tuple[str, str]) -> None:
    with d.function("G", "Group"):
        psus = {tag: d.device(tag, "DEMO-PSU-24") for tag in order}
        module = d.device("U1", "DEMO-RED-2IN")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.wire(module.out["+"], live[1].outer, wire=(BU, 0.5))
    d.wire(module.out["-"], zero[1].outer, wire=(BU, 0.5))
    for tag, group, n in (("T1", module.in_1, "1"), ("T2", module.in_2, "2")):
        d.wire(psus[tag].output["+"], group[f"{n}+"], wire=(BU, 0.5))
        d.wire(psus[tag].output["-"], group[f"{n}-"], wire=(BU, 0.5))


def _built(order: tuple[str, str]) -> tuple:
    """The model and layout of the two supplies and the module, authored in `order`."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d, order)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    return model, stage_results(model, read_inputs(model))[0].layout


def _box(model, layout, tag: str):
    (item,) = (one.id for one in items(model).values() if one.key[-1] == f"G/{tag}")
    (box,) = (one for one in layout.placed if one.function == item)
    return box


def _pin_x(box, name: str) -> int:
    (pin,) = (g for g in box.geometry.ports if g.name == name)
    return box.at.x + pin.at.x


def _check(order: tuple[str, str]) -> None:
    model, layout = _built(order)
    module = _box(model, layout, "U1")
    pairs = (("T1", "in_1", "1"), ("T2", "in_2", "2"))
    for tag, group, number in pairs:
        psu = _box(model, layout, tag)
        for out, pin in (("+", "+"), ("-", "-")):
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"{group}.{number}{pin}")
    item_of = {pid: functions(model)[p.function].item for pid, p in ports(model).items()}
    feeders = {_box(model, layout, t).function for t in ("T1", "T2")}
    wires = [r for r in layout.routes if {item_of[r.a], item_of[r.b]} & feeders]
    assert len(wires) == 4
    assert all(len({p.at.x for p in r.points}) == 1 for r in wires), "a wire bends"
    boxes = [_box(model, layout, tag) for tag in ("T1", "T2", "U1")]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not _overlap(a, b), "two boxes overlap"
    outs = {
        pid
        for pid, p in ports(model).items()
        if item_of[pid] == module.function and functions(model)[p.function].key[-1] == "out"
    }
    drawn = {s.port for s in layout_of(model, PowerSymbol).values()}
    assert len(outs) == 2
    assert outs <= drawn, "the module's output pins draw power symbols"


def _overlap(a, b) -> bool:
    def span(box):
        k = box.geometry.keepout
        return box.at.x + k.x, box.at.x + k.x + k.width, box.at.y + k.y, box.at.y + k.y + k.height

    ax0, ax1, ay0, ay1 = span(a)
    bx0, bx1, by0, by1 = span(b)
    return a.page == b.page and ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def test_each_supply_stands_over_its_own_pin_group_of_the_redundancy_module() -> None:
    """Output pins share x with the group's pins, no wire bends, no box overlaps, power symbols."""
    _check(("T1", "T2"))


def test_the_pairing_sets_the_x_when_the_supplies_are_authored_in_swapped_order() -> None:
    """The second supply authored first still stands over its own group."""
    _check(("T2", "T1"))
