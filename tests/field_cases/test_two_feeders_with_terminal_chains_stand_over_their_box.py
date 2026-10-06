"""Field case: two supplies fed from terminal runs stand over the module they feed.

The engineering shape: two 24 V supplies, each fed from its own pair of strip terminals (L and N
runs), feed one redundancy module with an input group per supply. The module stands on one page
as one box, with the groups on top and the output below.

The bug: a supply stands over its module only when it is alone in its column. Fed from terminals
its column is a chain of three cells, so both supplies stood beside the module and all four wires
to it were link markers.
The rule (decision layout-0122, amending layout-0107 How 3): a feeder at the bottom of its column
attaches with its column, so the chain stands above the feeder and the feeders stand side by side
over their paired pins.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BN, BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports


def _built() -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    ac = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    live, neutral = ac.run("L", 2, bridged=True), ac.run("N", 2, bridged=True)
    with d.function("G", "Supply"):
        m1 = d.device("M1", "DEMO-RED-2IN")
        psus = [d.device(f"G{n}", "DEMO-PSU-24") for n in (1, 2)]
    for n, psu in enumerate(psus, start=1):
        d.wire(live[n].outer, psu.input["L"], wire=(BN, 1.5))
        d.wire(neutral[n].outer, psu.input["N"], wire=(BU, 1.5))
        group = getattr(m1, f"in_{n}")
        d.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.dc_supply("S", plus=m1.out["+"], minus=m1.out["-"], voltage=24)
    d.wire(m1.out["+"], rail.run("P", 2, bridged=True)[1].outer, wire=(BN, 1.5))
    d.wire(m1.out["-"], rail.run("M", 2, bridged=True)[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    return model, stage_results(model, read_inputs(model))[0].layout


def _box(model, layout, tag: str):
    (item,) = (one.id for one in items(model).values() if one.key[-1] in (f"G/{tag}", tag))
    return next(one for one in layout.placed if one.function == item)


def _pin_x(box, name: str) -> int:
    (pin,) = (g for g in box.geometry.ports if g.name == name)
    return box.at.x + pin.at.x


def test_supplies_fed_from_terminals_stand_over_the_module_pin_over_pin() -> None:
    """No marker to the module, output pins over input pins, strip terminals on the same page."""
    model, layout = _built()
    module = _box(model, layout, "M1")
    psus = {n: _box(model, layout, f"G{n}") for n in (1, 2)}
    boxes = {module.function, *(p.function for p in psus.values())}
    fn_of = {pid: functions(model)[p.function] for pid, p in ports(model).items()}
    wires = [
        m for m in layout.markers if fn_of[m.port].item in boxes and fn_of[m.port].key[-1] != "out"
    ]
    assert not wires, "a wire between a supply and the module is a link marker"
    for n, psu in psus.items():
        for out in ("+", "-"):
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"in_{n}.{n}{out}")
    strip = {i for i, one in items(model).items() if one.key[0] == "X1" and len(one.key) == 4}
    held = functions(model)  # a placed box names its item, any other placed thing its function
    terminals = [
        one
        for one in layout.placed
        if (held[one.function].item if one.function in held else one.function) in strip
    ]
    assert len(terminals) == 4
    assert {one.page for one in (*terminals, module, *psus.values())} == {module.page}
