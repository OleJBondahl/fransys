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
from typing import Any

import fransys as fr
from _drawn_facts import symbol_subjects
from fransys.colours import BN, BU

from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _built() -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    ac = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    live, neutral = ac.run("L", 2, bridged=True), ac.run("N", 2, bridged=True)
    with d.function("G", "Supply"):
        m1 = d.device("M1", "DEMO-RED-2IN")
        psus = [d.device(f"G{n}", "DEMO-PSU-24") for n in (1, 2)]
    for n, psu in enumerate(psus, start=1):
        d.detail.wire(live[n].outer, psu.input["L"], wire=(BN, 1.5))
        d.detail.wire(neutral[n].outer, psu.input["N"], wire=(BU, 1.5))
        group = getattr(m1, f"in_{n}")
        d.detail.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.detail.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.dc_supply("S", plus=m1.out["+"], minus=m1.out["-"], voltage=24)
    d.detail.wire(m1.out["+"], rail.run("P", 2, bridged=True)[1].outer, wire=(BN, 1.5))
    d.detail.wire(m1.out["-"], rail.run("M", 2, bridged=True)[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _box(model, tag: str) -> tuple[object, Any]:
    """The (page, generic box) drawn for the function of item `tag`."""
    (found,) = (
        (one.page, one)
        for one in symbol_subjects(model)
        if one.key == "generic-box" and one.tag == tag
    )
    return found


def _held_by(model, held: set) -> list[tuple[object, Any]]:
    """The (page, drawn symbol) pairs drawn for the functions in `held`."""
    return [(one.page, one) for one in symbol_subjects(model) if one.owner in held]


def _pin_x(box, name: str) -> int:
    return box.x + dict(box.offsets)[name]


def test_supplies_fed_from_terminals_stand_over_the_module_pin_over_pin() -> None:
    """No marker to the module, output pins over input pins, strip terminals on the same page."""
    model = _built()
    module_page, module = _box(model, "M1")
    psus = {n: _box(model, f"G{n}") for n in (1, 2)}
    boxes = [module, *(box for _, box in psus.values())]
    box_items = {
        f.item for f in functions(model).values() if f.id.value in {b.owner for b in boxes}
    }
    fn_of = {pid: functions(model)[p.function] for pid, p in ports(model).items()}
    wires = [
        m
        for m in layout_of(model, LinkMarker).values()
        if fn_of[m.port].item in box_items and fn_of[m.port].key[-1] != "out"
    ]
    assert not wires, "a wire between a supply and the module is a link marker"
    for n, (_, psu) in psus.items():
        for out in ("+", "-"):
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"in_{n}.{n}{out}")
    strip = {i for i, one in items(model).items() if one.key[0] == "X1" and len(one.key) == 4}
    held = {f.id.value for f in functions(model).values() if f.item in strip}
    terminals = _held_by(model, held)
    assert len(terminals) == 4
    assert {p for p, _ in (*terminals, (module_page, module), *psus.values())} == {module_page}
