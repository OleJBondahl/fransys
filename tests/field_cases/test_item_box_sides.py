"""Field case: an item whose every function is box-drawn is one box, a pin group per side.

The engineering shape: a power supply with an AC input and a DC output, on no declared supply,
and a PLC input module with a 24 V power function and four input channels, each channel wired to
a field switch. Both items have only functions with no IEC symbol of their own.

The bug (v0.5.0 look): the supply's pins alternated top and bottom, its input split over both
sides, and the module drew each wired channel as a column end of its own, apart from its box (the
drawn-ends work, decision layout-0099, made each channel a pin of the box).
The rule (decision layout-0099): one box per item, the side order AC
above DC, then power above signal, then load above supply; the first-ranked functions take the
top side and every other function the bottom.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _layout(plant) -> tuple:
    """The built model and its result of `plant(d)` in one cabinet document."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    result = fr.build(d, doc)
    return result.model, result


def _symbols(model, tag: str) -> list:
    """Every drawn symbol owned by the item or function tagged `tag`."""
    return [s for s in _gap(model, "symbol subject").values() if s.owner.split()[0] == tag]


def _box(model, tag: str):
    """The one box of item `tag`; no function of the item is drawn apart from it."""
    (box,) = _symbols(model, tag)
    assert box.key == "generic-box"
    return box


def _box_sides(model, tag: str) -> dict[str, str]:
    """The one box of item `tag`, as {port name: side}."""
    return dict(_box(model, tag).sides)


def _psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.detail.wire(psu.output["+"], lamp[1], wire=(BU, 0.5))
    d.detail.wire(psu.output["-"], lamp[2], wire=(BU, 0.5))


def _module(d) -> None:
    module = d.device("K1", "DEMO-PLC-DI-4P")
    for i in range(1, 5):
        switch = d.device(f"S{i}", "DEMO-SWITCH-2P")
        d.detail.wire(switch.sw["B"], getattr(module, f"di_{i}")[i], wire=(BU, 0.5))


def test_a_power_supply_draws_its_ac_input_on_top_and_its_dc_output_below() -> None:
    """No supply is declared, so D5 does not decide: V1's load above supply does."""
    model, _ = _layout(_psu)
    sides = _box_sides(model, "T1")
    assert sides == {"input.L": "n", "input.N": "n", "output.+": "s", "output.-": "s"}


def test_a_plc_module_draws_one_box_with_power_on_top_and_its_channels_below() -> None:
    """The four wired channels are pins of the module's box, below its power pins."""
    model, _ = _layout(_module)
    sides = _box_sides(model, "K1")
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
    d.detail.wire(psu.output["+"], module.power["24V"], wire=(BU, 0.5))
    d.detail.wire(psu.output["-"], module.power["0V"], wire=(BU, 0.5))


def test_a_plc_module_box_takes_v1_sides_for_its_power_and_its_channels() -> None:
    """The module's box (power and four unwired channels) fixes V1 sides: power N, channels S."""
    model, _ = _layout(_module_unwired)
    sides = _box_sides(model, "K1")
    north = {name.split(".")[0] for name, side in sides.items() if side == "n"}
    south = {name.split(".")[0] for name, side in sides.items() if side == "s"}
    assert (north, south) == ({"power"}, {"di_1", "di_2", "di_3", "di_4"})


def test_a_switch_stands_under_its_channel_pin_clear_of_the_box() -> None:
    """Each wired switch is placed below the module box on its page; the first under its pin."""
    model, result = _layout(_module)
    box = _box(model, "K1")
    others = [s for s in _gap(model, "symbol subject").values() if s is not box]
    assert len(others) == 4
    assert {one.page for one in others} == {box.page}
    assert all(one.y > box.y for one in others)
    assert any(one.x == box.x + box.offsets["di_1.1"] for one in others)
    assert "SYMBOL_OVERLAP" not in {f.code for f in result.findings}
