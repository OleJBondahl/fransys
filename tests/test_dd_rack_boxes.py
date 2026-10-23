"""One undo test per ruling for rack order and page packing, item views and generic boxes, and
PLC channels, built through the `fransys` facade from
`examples/demo-parts` and read from the core path's page Drawings only.

Not covered: "the rack's supply is drawn as rails in their own band" and "an item
whose functions all choose one named symbol is one view" (the PSU). Both need a multi-function
part whose functions are not PLC channels and whose ports fit one symbol; the only such demo parts
are the relay (8 ports) and the contactor (10), and no library symbol has more than 5.

A Drawing carries no model id, so an item's box is the generic box nearest, in x, its TAG text.
"""

import shutil
from importlib.resources import as_file, files
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _dd_core import designation_of
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_layout.geometry import generic_box_geometry
from fransys_model.layout import Page, layout_of

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


def _tag_at(model, name):
    """(Drawing, TAG text) of the one TAG text printing item `name`'s designation."""
    text = f"-{designation_of(model, name)}"
    (found,) = [
        (d, t)
        for d in drawn_pages(model).values()
        for t in d.texts
        if t.kind == "TAG" and t.text == text
    ]
    return found


def _nearest(drawing, tag, key):
    """The symbol of library key `key` on the page whose x is nearest the tag's box."""
    return min((s for s in drawing.symbols if s.key == key), key=lambda s: abs(s.x - tag.box.x))


def _box(model, item):
    """(Drawing, generic box) drawn for the item authored as `item`: a PLC module is one box."""
    drawing, tag = _tag_at(model, item)
    return drawing, _nearest(drawing, tag, _GENERIC_BOX)


def _marks(box):
    """The marking strings of a box, by port name."""
    return {s.split(".", 1)[1]: v for s, v in box.slots if s.startswith("marking.")}


def _pin(box, port):
    """(x, y, side) of box port `port`: its offset along the stretch axis,."""
    side = dict(box.sides)[port]
    y = box.y - _HALF_BODY if side == "n" else box.y + _HALF_BODY
    return box.x + dict(box.offsets)[port], y, side


def _wire_ends_at(drawing, x, y):
    return any((x, y) in (w.points[0], w.points[-1]) for w in drawing.wires)


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
    """Modules run in position order, each with the columns attached to it beside it."""
    # UNDO: fransys_layout/stages/arrange.py:rack_order
    #     returns `columns` unchanged (modules then stand a, m, z)
    model = _rack_of_three_modules()
    boxes = [_box(model, module) for module in ("z", "a", "m")]
    coils = [_nearest(*_tag_at(model, relay), "operating-device") for relay in ("k3", "k2", "k1")]
    chan = [box for _, box in boxes]
    assert chan[0].x < chan[1].x < chan[2].x
    for at, (module, relay) in enumerate(zip(chan, coils, strict=True)):
        assert module.x <= relay.x
        if at + 1 < len(chan):
            assert relay.x < chan[at + 1].x


def test_several_groups_share_one_page() -> None:
    """Groups pack onto pages by measured width, so small groups stand together."""
    # UNDO: fransys_layout/stages/_packing.py:pack
    #     `used + run.width > content_width` becomes `True`
    parts, d = _design()
    c1, wire = d.location("C1", "Cabinet"), d.wiring(colour="BU", gauge="0.5")
    lamps = [
        d.item(
            "DEMO-LAMP-24", tag=f"P{name[-1]}", name=name.lower(), at=c1, group=d.group(name, name)
        )
        for name in ("G1", "G2", "G3")
    ]
    # layout-0218: a loose lamp draws no page, so the three lamps are wired in a chain
    wire(lamps[0].fn("lamp")["2"], lamps[1].fn("lamp")["1"])
    wire(lamps[1].fn("lamp")["2"], lamps[2].fn("lamp")["1"])
    pages = layout_of(fr.build(parts, d.draft(), layout_trigger_document()).model, Page).values()
    assert len(pages) < 3
    assert max(len(page.groups) for page in pages) >= 2


def _plc_modules():
    """DO1 with both channels wired to relay coils; DI1 with both channels unwired."""
    parts, d = _design()
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", at=c1, group=plc)
    di = d.item("DEMO-PLC-DI-2", tag="DI1", name="di", at=c1, group=plc)
    wire = d.wiring(colour="BU", gauge="0.5")
    for name, channel in (("k1", "do_1"), ("k2", "do_2")):
        k = d.item("DEMO-RLY-2CO-24", tag=name.upper(), name=name, at=c1, group=plc)
        wire(do.fn(channel)[channel[-1]], k.fn("coil")["A1"])
    # layout-0218: DI1 keeps di_2 unwired; one wired channel draws the module as a box
    wire(di.fn("di_1")["1"], k.fn("co_1")["14"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def test_an_item_of_generic_functions_is_one_box_showing_every_functions_ports() -> None:
    """Two or more generic functions of one item are one box carrying all their ports."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     never merges (`found.extend(group)` for every group)
    model = _plc_modules()
    _, box = _box(model, "di")
    assert box.key == _GENERIC_BOX
    assert set(_marks(box).values()) == {"1", "2"}


def test_a_wired_plc_channel_is_a_pin_on_the_south_side_of_its_modules_box() -> None:
    """Each wired channel is a pin of the module's one box; the wire leaves side S."""
    # UNDO: fransys_layout/engines/schematic/read/item_sides.py:item_sides
    #     returns `{}` for a box with a PLC channel (the old landing order): pins then take the
    #     default sides, not S
    model = _plc_modules()
    drawing, box = _box(model, "do")
    assert box.key == _GENERIC_BOX
    assert set(_marks(box).values()) == {"1", "2"}
    for channel in ("do_1.1", "do_2.2"):
        x, y, side = _pin(box, channel)
        assert side == "s"
        assert _wire_ends_at(drawing, x, y)


def test_no_plc_module_is_drawn_with_channel_symbols_wired_or_not() -> None:
    """Wired DO1 and unwired DI1 are each one generic box; no plc-channel end exists."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (gone with layout-0099)
    model = _plc_modules()
    symbols = [s for d in drawn_pages(model).values() for s in d.symbols]
    assert sum(s.key == _GENERIC_BOX for s in symbols) == 2
    assert _CHANNEL not in {s.key for s in symbols}


def test_a_module_tag_is_shown_once_on_its_box() -> None:
    """The two channels of one module print the module tag once, on the box."""
    # UNDO: fransys_layout/stages/tags.py:one_module_tag
    #     returns `requests` unchanged
    model = _plc_modules()
    drawing, box = _box(model, "do")
    tags = [t for t in drawing.texts if t.text == f"-{designation_of(model, 'do')}"]
    assert len(tags) == 1
    assert box.x <= tags[0].box.x <= box.x + 48


def test_a_boxs_port_pitch_comes_from_its_longest_port_name_in_whole_modules() -> None:
    """Pitch = ceil(text_width / 8 + 0.5) M, at least 2 M, by the name after its dot."""

    # UNDO: layout geometry/symbols.py:_generic measures the whole name (drop
    # `box_port_marking`), or generic_box.py:box_pitch drops the `math.ceil`
    def pitch(*names):
        ports = generic_box_geometry(names).ports
        return (ports[2].at.x - ports[0].at.x) / 8

    assert pitch("1", "2", "3", "4") == 2
    assert pitch("do_1.1", "do_2.2", "do_3.3", "do_4.4") == 2
    assert pitch("ABC", "D", "E", "F") == 3
    assert pitch("internal", "x", "y", "z") == 4


def test_the_engines_box_keeps_two_modules_between_ports_on_one_side() -> None:
    """The star-delta motor's end ports on one side stand 2 M (16 G) apart."""
    # UNDO: electrical_symbols/generic_box.py:_pitch returns 1.0
    parts, d = _design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    m1 = d.item("DEMO-MOTOR-11KW-YD", tag="M1", name="m1", at=c1, group=grp)
    # layout-0218: a relay coil on V2 keeps the box drawn; the pins keep their places
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    d.wiring(colour="BU", gauge="0.5")(k1.fn("coil")["A2"], m1.fn("end")["V2"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    _, motor = _box(model, "m1")
    (ux, uy, _), (vx, vy, _), (wx, wy, _) = (_pin(motor, port) for port in ("U2", "V2", "W2"))
    assert uy == vy == wy
    assert vx - ux == 16
    assert wx - vx == 16


def _motor_with_partner(relay_function, relay_port, motor_port):
    parts, d = _design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=grp)
    m1 = d.item("DEMO-MOTOR-11KW-YD", tag="M1", name="m1", at=c1, group=grp)
    d.wiring(colour="BU", gauge="0.5")(k1.fn(relay_function)[relay_port], m1[motor_port])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


@pytest.mark.parametrize(
    ("relay_function", "relay_port", "motor_port", "partner_above"),
    [("coil", "A2", "U2", True), ("co_1", "11", "V2", False)],
    ids=["partner above turns U2 north", "partner below turns V2 south"],
)
def test_box_ports_face_their_placed_partners(
    relay_function, relay_port, motor_port, partner_above
) -> None:
    """A wired box port stands on the side that faces its partner."""
    # UNDO: fransys_layout/stages/pagerun.py:place_pages
    #     skips `stages.boxes.box_sides` (`turned = drawn`)
    model = _motor_with_partner(relay_function, relay_port, motor_port)
    drawing, box = _box(model, "m1")
    x, y, _ = _pin(box, motor_port)
    (wire,) = drawing.wires
    end = wire.points[0] if (x, y) == wire.points[0] else wire.points[-1]
    assert (end[1] < box.y) is partner_above
    assert end == (x, y)
    assert y == box.y + (-_HALF_BODY if partner_above else _HALF_BODY)


def test_an_unwired_channel_of_a_half_wired_module_is_a_port_on_the_modules_box() -> None:
    """With one channel wired and one not, both are pins of the module's one box."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (gone with layout-0099)
    parts, d = _design()
    c1, plc = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", at=c1, group=plc)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", name="k1", at=c1, group=plc)
    d.wiring(colour="BU", gauge="0.5")(do.fn("do_1")["1"], k1.fn("coil")["A1"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    drawing, box = _box(model, "do")
    assert box.key == _GENERIC_BOX
    assert set(_marks(box).values()) == {"1", "2"}
    x, y, _ = _pin(box, "do_1.1")
    assert y == box.y + _HALF_BODY
    assert _wire_ends_at(drawing, x, y)


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
    """A 3-channel module with 1 wired and 2 unwired channels is ONE box holding all
    three channels' pins; the wired channel is not a column end of its own."""
    # UNDO: fransys_layout/engines/schematic/read/views.py:item_views
    #     keeps a wired one-port channel as its own view (gone with layout-0099)
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
    drawing, box = _box(model, "do")
    assert box.key == _GENERIC_BOX
    assert set(_marks(box).values()) == {"1", "2", "3"}
    x, y, _ = _pin(box, "do_1.1")
    assert y == box.y + _HALF_BODY
    assert _wire_ends_at(drawing, x, y)
