"""Field case: a supply with an unwired DC-OK contact and a four-channel PLC input module with a spare channel, both drawn as boxes.
The bug (v0.5.0 look): the supply box carried its idle contact's pins and the module box a pin per channel, leading nowhere.
Fixed by the hide_unused_pins profile rule (no record named): a box leaves out pins and functions with no conductor when on."""

from functools import cache

import fransys as fr
from _drawn_facts import symbol_subjects
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import plc_channel_rows
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions, items


@cache
def _layout(plant, *, hide: bool):
    """The model of `plant(d)` in one cabinet document, built once."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        plant(d)
    doc = unit_document(cab)
    return fr.build(d, doc).model


def _drawn_ports(model, tag: str) -> list[str]:
    """Every port name drawn for item `tag`'s functions, over all placements, and its box."""
    (item,) = (one.id for one in items(model).values() if one.tag == tag)
    own = {f.id.value for f in functions(model).values() if f.item == item}
    return [name for one in symbol_subjects(model) if one.owner in own or one.tag == tag for name in one.offsets]


def _channel_ports(model) -> list[str]:
    """K1's drawn ports but its power pins: a channel is a box pin or a column end of its own."""
    return [name for name in _drawn_ports(model, "K1") if not name.startswith("power")]


def _psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24-OK")
    lamp = d.device("P1", "DEMO-LAMP-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    d.series(psu.output["+"], lamp["1"], wire=(BU, 0.5))
    d.series(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    d.series(psu.input["L"], mains["1"], wire=(BU, 0.5))
    d.series(psu.input["N"], mains["2"], wire=(BU, 0.5))


def _module(d) -> None:
    module = d.device("K1", "DEMO-PLC-DI-4P")
    feed = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    for i in range(1, 4):
        switch = d.device(f"S{i}", "DEMO-SWITCH-2P")
        d.series(switch.sw["B"], getattr(module, f"di_{i}")[i], wire=(BU, 0.5))
        d.series(switch.sw["A"], feed[i].outer, wire=(BU, 0.5))


def test_a_supply_box_leaves_out_its_unwired_signal_contact() -> None:
    """The box keeps the four wired pins; the idle contact is a contact_no, not a box pin."""
    # UNDO: the layout's `hide_unused_pins` branch removed
    model = _layout(_psu, hide=True)
    ports = _drawn_ports(model, "T1")
    assert {"input.L", "input.N", "output.+", "output.-"} <= set(ports)
    assert sorted(ports) == ["input.L", "input.N", "output.+", "output.-"]
    assert _dc_ok_kind(model) is FunctionKind.CONTACT_NO
    assert _box_width(model) == _box_width(_layout(_psu, hide=False))


def _dc_ok_kind(model) -> FunctionKind:
    """The kind of the supply's idle DC-OK contact function."""
    (contact,) = (f for f in functions(model).values() if f.name == "dc_ok")
    return contact.kind


def _box_width(model) -> int:
    """The body width of T1's item box."""
    (box,) = (one for one in symbol_subjects(model) if one.key == "generic-box" and one.tag == "T1")
    return max(dict(box.offsets).values())


def _half_wired_psu(d) -> None:
    psu = d.device("T1", "DEMO-PSU-24-OK")
    lamp = d.device("P1", "DEMO-LAMP-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
    d.series(psu.output["+"], lamp["1"], wire=(BU, 0.5))
    d.series(lamp["2"], zero[1].outer, wire=(BU, 0.5))
    d.series(psu.input["L"], mains["1"], wire=(BU, 0.5))
    d.series(psu.input["N"], mains["2"], wire=(BU, 0.5))


def test_a_half_wired_box_function_keeps_its_wired_pin_and_drops_the_bare_one() -> None:
    """The output's + is wired and its - is not: the box draws output.+ alone."""
    # UNDO: the unused-pin filter of the layout, the box-drawn branch that drops bare ports removed
    model = _layout(_half_wired_psu, hide=True)
    ports = _drawn_ports(model, "T1")
    assert {"input.L", "input.N", "output.+"} <= set(ports)
    assert "output.-" not in ports


def test_a_plc_module_box_leaves_out_its_spare_channel() -> None:
    """Three channel ports are drawn over all placements, none for the spare di_4."""
    model = _layout(_module, hide=True)
    channels = _channel_ports(model)
    assert len(channels) == 3
    assert not [name for name in channels if name.endswith("4")]


def test_with_the_switch_off_every_pin_is_drawn() -> None:
    """The supply draws its four wired pins (its contact_no is no box pin); the module all four."""
    model = _layout(_psu, hide=False)
    assert sorted(_drawn_ports(model, "T1")) == [
        "input.L",
        "input.N",
        "output.+",
        "output.-",
    ]
    assert _dc_ok_kind(model) is FunctionKind.CONTACT_NO
    model = _layout(_module, hide=False)
    assert len(_channel_ports(model)) == 4


def test_the_plc_list_keeps_the_spare_channel_with_the_switch_on() -> None:
    """The list is a list, not a page: di_4 has its row, wired to nothing."""
    model = _layout(_module, hide=True)
    rows = plc_channel_rows(model)
    assert len(rows) == 4
    assert rows[-1].pin.endswith(":4")
    assert rows[-1].wired_to is None
