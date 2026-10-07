"""Field case: a pin with no conductor, and a function with none at all, can be left off the page.

The engineering shape: a power supply with a DC-OK signal contact that nobody wired, and a PLC
input module with four channels of which the fourth is a spare. Both are drawn as boxes.

The bug (v0.5.0 look): the supply's box carried the idle contact's two pins and the module's
box one pin per channel, so a page showed pins that lead nowhere. The rule (spec CONVENTIONS-V06
V1, `d.profile(hide_unused_pins=True)`): with the switch on, a box leaves out its pins and its
functions without a conductor; every list keeps them, and with it off nothing changes.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.derive import plc_channel_rows
from fransys_model.vocab.tables import functions, items


@cache
def _layout(plant, *, hide: bool) -> tuple:
    """The model and the staged layout of `plant(d)` in one cabinet document, built once."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    return model, results.layout


def _drawn_ports(model, layout, tag: str) -> list[str]:
    """Every port name drawn for item `tag`'s functions, over all placements, and its box."""
    (item,) = (one.id for one in items(model).values() if one.tag == tag)
    own = {f.id for f in functions(model).values() if f.item == item} | {item}
    return [g.name for one in layout.placed if one.function in own for g in one.geometry.ports]


def _channel_ports(model, layout) -> list[str]:
    """K1's drawn ports but its power pins: a channel is a box pin or a column end of its own."""
    return [name for name in _drawn_ports(model, layout, "K1") if not name.startswith("power")]


def _psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24-OK")
    lamp = d.device("P1", "DEMO-LAMP-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    d.wire(psu.output["+"], lamp["1"], wire=(BU, 0.5))
    d.wire(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    d.wire(psu.input["L"], mains["1"], wire=(BU, 0.5))
    d.wire(psu.input["N"], mains["2"], wire=(BU, 0.5))


def _module(d) -> None:
    module = d.device("K1", "DEMO-PLC-DI-4P")
    for i in range(1, 4):
        switch = d.device(f"S{i}", "DEMO-SWITCH-2P")
        d.wire(switch.sw["B"], getattr(module, f"di_{i}")[i], wire=(BU, 0.5))


def test_a_supply_box_leaves_out_its_unwired_signal_contact() -> None:
    """The box keeps the four wired pins and loses dc_ok.13 and dc_ok.14."""
    # UNDO: read/__init__.py:read_inputs, the `if profile.hide_unused_pins:` branch removed
    model, layout = _layout(_psu, hide=True)
    ports = _drawn_ports(model, layout, "T1")
    assert {"input.L", "input.N", "output.+", "output.-"} <= set(ports)
    assert not [name for name in ports if name.startswith("dc_ok")]
    assert _box_width(*_layout(_psu, hide=True)) < _box_width(*_layout(_psu, hide=False))


def _box_width(model, layout) -> int:
    """The body width of T1's item box."""
    (item,) = (one.id for one in items(model).values() if one.tag == "T1")
    (box,) = (one for one in layout.placed if one.function == item)
    return box.geometry.body.width


def _half_wired_psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24-OK")
    lamp = d.device("P1", "DEMO-LAMP-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    d.wire(psu.output["+"], lamp["1"], wire=(BU, 0.5))
    d.wire(psu.input["L"], mains["1"], wire=(BU, 0.5))
    d.wire(psu.input["N"], mains["2"], wire=(BU, 0.5))


def test_a_half_wired_box_function_keeps_its_wired_pin_and_drops_the_bare_one() -> None:
    """The output's + is wired and its - is not: the box draws output.+ alone."""
    # UNDO: read/unused.py:without_unused, the box-drawn branch that drops bare ports removed
    model, layout = _layout(_half_wired_psu, hide=True)
    ports = _drawn_ports(model, layout, "T1")
    assert {"input.L", "input.N", "output.+"} <= set(ports)
    assert "output.-" not in ports


def test_a_plc_module_box_leaves_out_its_spare_channel() -> None:
    """Three channel ports are drawn over all placements, none for the spare di_4."""
    model, layout = _layout(_module, hide=True)
    channels = _channel_ports(model, layout)
    assert len(channels) == 3
    assert not [name for name in channels if name.endswith("4")]


def test_with_the_switch_off_every_pin_is_drawn() -> None:
    """Both plants draw the idle contact's two pins and all four channel ports."""
    model, layout = _layout(_psu, hide=False)
    ports = _drawn_ports(model, layout, "T1")
    assert {"dc_ok.13", "dc_ok.14"} <= set(ports)
    model, layout = _layout(_module, hide=False)
    assert len(_channel_ports(model, layout)) == 4


def test_the_plc_list_keeps_the_spare_channel_with_the_switch_on() -> None:
    """The list is a list, not a page: di_4 has its row, wired to nothing."""
    model, _ = _layout(_module, hide=True)
    rows = plc_channel_rows(model)
    assert len(rows) == 4
    assert rows[-1].channel_designation.endswith(":4")
    assert rows[-1].wired_to is None
