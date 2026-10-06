"""Field case: an item whose every function is box-drawn is one box, a pin group per side.

The engineering shape: a power supply with an AC input and a DC output, on no declared supply,
and a PLC input module with a 24 V power function and four input channels, each channel wired to
a field switch. Both items have only functions with no IEC symbol of their own.

The bug (v0.5.0 look): the supply's pins alternated top and bottom, its input split over both
sides, and the module drew each wired channel as a column end of its own, apart from its box (the
drawn-ends work, decision layout-0099, made each channel a pin of the box).
The rule (spec CONVENTIONS-V06 V1, decision layout-0099): one box per item, the side order AC
above DC, then power above signal, then load above supply; the first-ranked functions take the
top side and every other function the bottom.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab import FunctionKind
from fransys_model.vocab.tables import functions, items, ports


def _layout(plant) -> tuple:
    """The model and the staged layout of `plant(d)` in one cabinet document."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    return model, results.layout


def _box_sides(model, layout, tag: str) -> dict[str, str]:
    """The one placement of item `tag`'s box, as {port name: side}; no function placed apart."""
    (item,) = (one.id for one in items(model).values() if one.key[-1] == tag)
    own = {f.id for f in functions(model).values() if f.item == item}
    assert not [one for one in layout.placed if one.function in own]
    (box,) = (one for one in layout.placed if one.function == item)
    return {g.name: g.facing.value for g in box.geometry.ports}


def _psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.wire(psu.output["+"], lamp[1], wire=(BU, 0.5))
    d.wire(psu.output["-"], lamp[2], wire=(BU, 0.5))


def _module(d) -> None:
    module = d.device("K1", "DEMO-PLC-DI-4P")
    for i in range(1, 5):
        switch = d.device(f"S{i}", "DEMO-SWITCH-2P")
        d.wire(switch.sw["B"], getattr(module, f"di_{i}")[i], wire=(BU, 0.5))


def test_a_power_supply_draws_its_ac_input_on_top_and_its_dc_output_below() -> None:
    """No supply is declared, so D5 does not decide: V1's load above supply does."""
    model, layout = _layout(_psu)
    sides = _box_sides(model, layout, "T1")
    assert sides == {"input.L": "n", "input.N": "n", "output.+": "s", "output.-": "s"}


def test_a_plc_module_draws_one_box_with_power_on_top_and_its_channels_below() -> None:
    """The four wired channels are pins of the module's box, below its power pins."""
    model, layout = _layout(_module)
    sides = _box_sides(model, layout, "K1")
    assert sides == {
        "power.24V": "n",
        "power.0V": "n",
        "di_1.1": "s",
        "di_2.2": "s",
        "di_3.3": "s",
        "di_4.4": "s",
    }


def _module_unwired(d) -> None:
    module = d.device("K1", "DEMO-PLC-DI-4P")
    psu = d.device("T1", "DEMO-PSU-24")
    d.wire(psu.output["+"], module.power["24V"], wire=(BU, 0.5))
    d.wire(psu.output["-"], module.power["0V"], wire=(BU, 0.5))


def test_a_plc_module_box_takes_v1_sides_for_its_power_and_its_channels() -> None:
    """The module's box (power and four unwired channels) fixes V1 sides: power N, channels S."""
    model, _ = _layout(_module_unwired)
    inputs = read_inputs(model)
    kind = {port.id: functions(model)[port.function].kind for port in ports(model).values()}
    owner = {f.id: items(model)[f.item].key[-1] for f in functions(model).values()}
    tag = {p.id: owner[ports(model)[p.id].function] for p in ports(model).values()}
    north = {kind[port] for port in inputs.item_north if tag[port] == "K1"}
    south = {kind[port] for port in inputs.item_south if tag[port] == "K1"}
    assert (north, south) == ({FunctionKind.LOAD}, {FunctionKind.PLC_CHANNEL})


def test_a_switch_stands_under_its_channel_pin_clear_of_the_box() -> None:
    """Each wired switch is placed below the module box on its page; the first under its pin."""
    model, layout = _layout(_module)
    (item,) = (one.id for one in items(model).values() if one.key[-1] == "K1")
    (box,) = (one for one in layout.placed if one.function == item)
    pin = next(g for g in box.geometry.ports if g.name == "di_1.1")
    bottom = box.at.y + box.geometry.keepout.y + box.geometry.keepout.height
    others = [one for one in layout.placed if one is not box]
    assert len(others) == 4
    assert {one.page for one in others} == {box.page}
    assert all(one.at.y + one.geometry.keepout.y > bottom for one in others)
    assert any(one.at.x == box.at.x + pin.at.x for one in others)
