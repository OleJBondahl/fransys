"""F5-C (layout deep dive): one undo test per ruling for D4 (rack order, page packing), D5 (item
views and generic boxes) and D6 (PLC channels), built through the `fransys` facade from
`examples/demo-parts` and read from the laid-out `layout.*` records only.

Not covered: D4's "the rack's supply is drawn as rails in their own band" and D5's "an item
whose functions all choose one named symbol is one view" (the PSU). Both need a multi-function
part whose functions are not PLC channels and whose ports fit one symbol; the only such demo parts
are the relay (8 ports) and the contactor (10), and no library symbol has more than 5.
"""

import shutil
from importlib.resources import as_file, files
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document

import electrical_symbols
from fransys_model.layout import (
    Label,
    LabelKind,
    LinkMarker,
    Page,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Rack boxes",
    "number": "P-1003",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_GENERIC_BOX = "generic-box"
_CHANNEL = "plc-channel"
_HALF_BODY = 16  # G, half the box body height: a port stands this far above or below the origin


def _design():
    parts = fransys_parts.load("demo_parts")
    design = fransys_author.Design(parts)
    design.project(**_PROJECT)
    design.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, design


def _function(model, item, name):
    """The id of function `name` of the item authored as `item`."""
    return next(f.id for f in functions(model).values() if f.key[0] == item and f.name == name)


def _placed(model, item, name):
    """The one placement of function `name` of `item`."""
    (found,) = (
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == _function(model, item, name)
    )
    return found


def _box(model, item):
    """The one placement of the item authored as `item`: a PLC module is one box (V1)."""
    (found,) = _placements_of_item(model, item)
    return found


def _placements_of_item(model, item):
    """Every placement of every function of the item authored as `item`."""
    ids = {f.id for f in functions(model).values() if f.key[0] == item}
    return [p for p in layout_of(model, SymbolPlacement).values() if p.function in ids]


def _rack_of_three_modules():
    """Modules whose position order (DO9, DO2, DO5) runs against their keys and their tags,
    each with its own relay wired to its first channel."""
    parts, d = _design()
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    rack = d.item(None, tag="U1", at=c1, group=plc)
    wire = d.wiring(colour="BU", gauge="0.5")
    for name, tag, position, relay in (
        ("z", "DO9", 1, "k3"),
        ("a", "DO2", 2, "k2"),
        ("m", "DO5", 3, "k1"),
    ):
        module = d.item(
            "DEMO-PLC-DO-2", tag=tag, name=name, parent=rack, position=position, at=c1, group=plc
        )
        k = d.item("DEMO-RLY-2CO-24", tag=relay.upper(), name=relay, at=c1, group=plc)
        wire(module.fn("do_1")["1"], k.fn("coil")["A1"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def test_a_racks_modules_and_their_attached_columns_stand_in_authored_position_order() -> None:
    """D4: modules run in position order, each with the columns attached to it beside it."""
    # UNDO: fransys_layout/stages/arrange.py:rack_order
    #     returns `columns` unchanged (modules then stand a, m, z)
    model = _rack_of_three_modules()
    chan = [_box(model, module) for module in ("z", "a", "m")]
    coil = [_placed(model, relay, "coil") for relay in ("k3", "k2", "k1")]
    assert chan[0].x < chan[1].x < chan[2].x
    for at, (module, relay) in enumerate(zip(chan, coil, strict=True)):
        assert module.x <= relay.x
        if at + 1 < len(chan):
            assert relay.x < chan[at + 1].x


def test_several_groups_share_one_page() -> None:
    """D4: groups pack onto pages by measured width, so small groups stand together."""
    # UNDO: fransys_layout/stages/_packing.py:pack
    #     `used + run.width > content_width` becomes `True`
    parts, d = _design()
    c1 = d.location("C1", "Cabinet")
    for name in ("G1", "G2", "G3"):
        d.item(
            "DEMO-LAMP-24", tag=f"P{name[-1]}", name=name.lower(), at=c1, group=d.group(name, name)
        )
    pages = layout_of(fr.build(parts, d.draft(), layout_trigger_document()).model, Page).values()
    assert len(pages) < 3
    assert max(len(page.groups) for page in pages) >= 2


def _plc_modules():
    """DO1 with both channels wired to relay coils; DI1 with both channels unwired."""
    parts, d = _design()
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", at=c1, group=plc)
    d.item("DEMO-PLC-DI-2", tag="DI1", name="di", at=c1, group=plc)
    wire = d.wiring(colour="BU", gauge="0.5")
    for name, channel in (("k1", "do_1"), ("k2", "do_2")):
        k = d.item("DEMO-RLY-2CO-24", tag=name.upper(), name=name, at=c1, group=plc)
        wire(do.fn(channel)[channel[-1]], k.fn("coil")["A1"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _marking_labels(model, placement, item):
    """The MARKING labels of `item`'s ports, keyed by port name, that stand on `placement`."""
    ids = {f.id for f in functions(model).values() if f.key[0] == item}
    names = {p.id: p.name for p in ports(model).values() if p.function in ids}
    return {
        names[label.port]: label
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.MARKING
        and label.port in names
        and label.page == placement.page
        and placement.x <= label.x <= placement.x + 48
    }


def test_an_item_of_generic_functions_is_one_box_showing_every_functions_ports() -> None:
    """D5: two or more generic functions of one item are one box carrying all their ports."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     never merges (`found.extend(group)` for every group)
    model = _plc_modules()
    (box,) = _placements_of_item(model, "di")
    assert box.symbol == _GENERIC_BOX
    assert set(_marking_labels(model, box, "di")) == {"1", "2"}


def _channel_pin_y(model, item, channel):
    """The y where `channel`'s wire leaves `item`'s box: its route end, or its link marker."""
    port = next(
        p.id for p in ports(model).values() if p.function == _function(model, item, channel)
    )
    for route in layout_of(model, Route).values():
        if port in (route.a, route.b):
            points = sorted(route.points, key=lambda p: p.index)
            return (points[-1] if route.b == port else points[0]).y
    (marker,) = [m for m in layout_of(model, LinkMarker).values() if m.port == port]
    return marker.y


def test_a_wired_plc_channel_is_a_pin_on_the_south_side_of_its_modules_box() -> None:
    """D6, V1: each wired channel is a pin of the module's one box; the wire leaves side S."""
    # UNDO: fransys_layout/engines/schematic/read/item_sides.py:item_sides
    #     returns `{}` for a box with a PLC channel (the old landing order): pins then take the
    #     default sides, not S
    model = _plc_modules()
    box = _box(model, "do")
    assert box.symbol == _GENERIC_BOX
    assert set(_marking_labels(model, box, "do")) == {"1", "2"}
    for channel, relay in (("do_1", "k1"), ("do_2", "k2")):
        assert _placed(model, relay, "coil").page == box.page
        assert _channel_pin_y(model, "do", channel) == box.y + _HALF_BODY


def test_no_plc_module_is_drawn_with_channel_symbols_wired_or_not() -> None:
    """D6, V1: wired DO1 and unwired DI1 are each one generic box; no plc-channel end exists."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (rule C2, gone with layout-0099)
    model = _plc_modules()
    for item in ("do", "di"):
        assert [p.symbol for p in _placements_of_item(model, item)] == [_GENERIC_BOX]
    assert _CHANNEL not in {p.symbol for p in layout_of(model, SymbolPlacement).values()}


def test_a_module_tag_is_shown_once_on_its_box() -> None:
    """D6, V1: the two channels of one module print the module tag once, on the box."""
    # UNDO: fransys_layout/stages/tags.py:one_module_tag
    #     returns `requests` unchanged
    model = _plc_modules()
    box = _box(model, "do")
    ids = {f.id for f in functions(model).values() if f.key[0] == "do"}
    tags = [
        label
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.TAG and label.function in ids
    ]
    assert [label.function for label in tags] == [box.function]
    assert box.x <= tags[0].x <= box.x + 48


def test_a_boxs_port_pitch_comes_from_its_longest_port_name_in_whole_modules() -> None:
    """D5: pitch = ceil(text_width / 8 + 0.5) M, at least 2 M, by the name after its dot."""

    # UNDO: electrical_symbols/generic_box.py:_pitch measures the whole
    # name (drop `.rsplit(".", 1)[-1]`), or drops the `math.ceil`
    def pitch(*names):
        symbol = electrical_symbols.generic_box(names)
        return symbol.ports[2].position.x - symbol.ports[0].position.x

    assert pitch("1", "2", "3", "4") == 2
    assert pitch("do_1.1", "do_2.2", "do_3.3", "do_4.4") == 2
    assert pitch("ABC", "D", "E", "F") == 3
    assert pitch("internal", "x", "y", "z") == 4


def test_the_engines_box_keeps_two_modules_between_ports_on_one_side() -> None:
    """D5: the unwired motor's ports on one side stand 2 M (16 G) apart."""
    # UNDO: electrical_symbols/generic_box.py:_pitch returns 1.0
    parts, d = _design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    d.item("DEMO-MOTOR-4KW", tag="M1", name="m1", at=c1, group=grp)
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    motor = _placed(model, "m1", "motor")
    marks = _marking_labels(model, motor, "m1")
    assert marks["V"].y == marks["PE"].y
    assert marks["W"].y == marks["U"].y
    assert marks["V"].x - marks["PE"].x == 16
    assert marks["W"].x - marks["U"].x == 16


def _motor_with_partner(relay_function, relay_port, motor_port):
    parts, d = _design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    m1 = d.item("DEMO-MOTOR-4KW", tag="M1", name="m1", at=c1, group=grp)
    d.wiring(colour="BU", gauge="0.5")(k1.fn(relay_function)[relay_port], m1[motor_port])
    return fr.build(parts, d.draft(), layout_trigger_document()).model, m1.fn("motor")[
        motor_port
    ].id


@pytest.mark.parametrize(
    ("relay_function", "relay_port", "motor_port", "partner_above"),
    [("coil", "A2", "U", True), ("co_1", "11", "V", False)],
    ids=["partner above turns U (default S) north", "partner below turns V (default N) south"],
)
def test_box_ports_face_their_placed_partners(
    relay_function, relay_port, motor_port, partner_above
) -> None:
    """D5: a wired box port stands on the side that faces its partner."""
    # UNDO: fransys_layout/stages/pagerun.py:place_pages
    #     skips `stages.boxes.box_sides` (`turned = drawn`)
    model, port = _motor_with_partner(relay_function, relay_port, motor_port)
    box = _placed(model, "m1", "motor")
    (route,) = layout_of(model, Route).values()
    points = sorted(route.points, key=lambda p: p.index)
    end = points[-1] if route.b == port else points[0]
    assert (end.y < box.y) is partner_above
    assert end.y == box.y + (-_HALF_BODY if partner_above else _HALF_BODY)


def test_an_unwired_channel_of_a_half_wired_module_is_a_port_on_the_modules_box() -> None:
    """D6: with one channel wired and one not, both are pins of the module's one box."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (rule C2, gone with layout-0099)
    parts, d = _design()
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", at=c1, group=plc)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=plc)
    d.wiring(colour="BU", gauge="0.5")(do.fn("do_1")["1"], k1.fn("coil")["A1"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    box = _box(model, "do")
    assert box.symbol == _GENERIC_BOX
    assert set(_marking_labels(model, box, "do")) == {"1", "2"}
    assert _channel_pin_y(model, "do", "do_1") == box.y + _HALF_BODY


_THREE_CHANNEL_PART = """\
schema = 1

[part]
mpn = "DEMO-PLC-DO-3"
manufacturer = "Demo"
description = "PLC digital output module, 3 channels (synthetic, for this test only)"
category = "plc_module"
class_code = "K"
""" + "".join(
    f"""
[[function]]
name = "do_{n}"
kind = "plc_channel"
ports = [{{ name = "{n}", role = "generic" }}]

[function.plc_channel]
signal = "do"
channel = {n}
"""
    for n in (1, 2, 3)
)


def test_a_three_channel_module_with_one_wired_channel_is_one_box_holding_all_three_pins(
    tmp_path,
) -> None:
    """D5/D6, V1: a 3-channel module with 1 wired and 2 unwired channels is ONE box holding all
    three channels' pins; the wired channel is not a column end of its own."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (rule C2, gone with layout-0099)
    root = tmp_path / "demo_parts"
    with as_file(files("demo_parts")) as demo_parts:
        shutil.copytree(demo_parts, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (root / "parts" / "plc-do-3ch.toml").write_text(_THREE_CHANNEL_PART, encoding="utf-8")
    parts = fransys_parts.load_path(root)
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    do = d.item("DEMO-PLC-DO-3", tag="DO1", name="do", at=c1, group=plc)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=plc)
    d.wiring(colour="BU", gauge="0.5")(do.fn("do_1")["1"], k1.fn("coil")["A1"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    box = _box(model, "do")
    assert box.symbol == _GENERIC_BOX
    assert set(_marking_labels(model, box, "do")) == {"1", "2", "3"}
    assert _channel_pin_y(model, "do", "do_1") == box.y + _HALF_BODY
