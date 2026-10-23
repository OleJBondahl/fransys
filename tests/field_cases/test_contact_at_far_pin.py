"""Field case: a contact wired to a PLC input channel stands under that channel (V5, 2026-10-02).

The engineering shape: a PLC input module K1 with two wired channels in one group, and in a second
group two contactors K2 and K3, each with its coil wired to a lamp and its auxiliary contact wired
to one channel. A third contactor K4 has an auxiliary contact with a wire to channel 3 and a wire
to a lamp, so it has no single far pin.

The bug: chain discovery homed one contactor's contacts under its channel; the other contactors'
contacts stayed in their own group, bundled with the device's other contacts, so the move of a
lone contact column did not reach them. The module also holds power pins, so it is no all-channel
box: the channel pins are flagged per port. The main contact has one wire, so it is drawn.

The rule (decision layout-0099): a contact whose one wire goes to a pin in
another group is homed under that pin, once, and references its coil; a contact with a second
wire stays home.

layout-0125: a keep-out holds the ink drawn, so contacts under adjacent channel pins (33 wide on a
48 pitch) raise no SYMBOL_OVERLAP; the drawing itself is unchanged.
"""

import tempfile
from functools import cache
from hashlib import sha256
from itertools import combinations, pairwise
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_layout.geometry import GENERIC_BOX_KEY, WIRING_GRID, symbol_geometry
from fransys_layout.geometry.symbols import channel_pitch
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _plant(d, *, split: bool = False) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group") as g1:
        lamps = {n: d.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4)}
        contactors = {
            n: d.device(f"K{n}", "DEMO-CTR-3P-NC") for n in (2, 3, 4) if not split or n != 3
        }
    d.layout.break_before(g1)
    if split:
        with d.function("G2", "Second contactor group") as g2:
            contactors[3] = d.device("K3", "DEMO-CTR-3P-NC")
        d.layout.break_before(g2)
    for number, contactor in contactors.items():
        d.detail.wire(contactor.coil["A1"], lamps[number].lamp["1"], wire=(BU, 0.5))
        d.detail.wire(
            contactor.main["1"], lamps[number].lamp["1"], wire=(BU, 0.5)
        )  # layout-0112: wired
        channel = getattr(module, f"di_{number - 1}")[str(number - 1)]
        d.detail.wire(contactor.aux["14"], channel, wire=(BU, 0.5))
    d.detail.wire(contactors[4].aux["13"], lamps[4].lamp["2"], wire=(BU, 0.5))


@cache
def _staged(*, split: bool = False, sixteen: bool = False) -> tuple:
    """The built model and its findings of one circuit, built once; read only."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    if sixteen:
        _plant_16(d)
    else:
        _plant(d, split=split)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    built = fr.build(d, doc)
    return built.model, built.findings


def _built(*, split: bool = False):
    return _staged(split=split)[0]


def _placed(model, tag: str, name: str, symbol: str | None = None) -> list:
    """The drawn symbols of function `name` of item `tag`, optionally of one library symbol."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    wanted = {
        f.id.value for f in functions(model).values() if f.name == name and tag_of[f.item] == tag
    }
    return [
        s
        for s in _gap(model, "symbol subject").values()
        if s.owner and s.owner.split(":")[-1] in wanted and symbol in (None, s.symbol)
    ]


def _home(model, placed) -> tuple:
    """The drawing set and the page a drawn symbol stands on."""
    return _gap(model, "document fact")[placed.page].drawing_set, placed.page


def _port_at(placed, port: str) -> tuple[int, int]:
    """The page position of port `port` of the drawn symbol `placed`."""
    if placed.symbol == GENERIC_BOX_KEY:
        return placed.x + placed.offsets[port], placed.y
    geometry = symbol_geometry(placed.symbol, poles=placed.poles, orientation=placed.orient)
    (found,) = (g for g in geometry.ports if g.name == port)
    return placed.x + found.at.x, placed.y + found.at.y


def _pin_x(placed, port: str) -> int:
    return _port_at(placed, port)[0]


def _port_y(placed, port: str) -> int:
    return _port_at(placed, port)[1]


def _channel_box(model):
    """The PLC module's box: the one generic box with channel (`di_`) ports."""
    (box,) = (
        s
        for s in _gap(model, "symbol subject").values()
        if s.symbol == GENERIC_BOX_KEY and any("di_" in n for n in s.offsets)
    )
    return box


def _fid(model, placed):
    """The id of the function a drawn symbol belongs to."""
    (found,) = (
        f.id for f in functions(model).values() if f.id.value == placed.owner.split(":")[-1]
    )
    return found


def _cross_references(model) -> list:
    return [x for x in _gap(model, "text subject").values() if x.kind.name == "CROSS_REFERENCE"]


def _pages(model, partners) -> list:
    return [(_gap(model, "document fact")[p.page].drawing_set, p.page) for p in partners]


def test_each_single_wire_contact_stands_once_under_its_channel() -> None:
    model = _built()
    box = _channel_box(model)
    for number in (2, 3):
        (contact,) = _placed(model, f"K{number}", "aux")
        assert _home(model, contact) == _home(model, box)
        assert contact.y > box.y
        assert _pin_x(contact, "out") == _pin_x(box, f"di_{number - 1}.{number - 1}")


def test_each_moved_contact_references_its_coil_and_the_coil_lists_it() -> None:
    model = _built()
    for number in (2, 3):
        (contact,) = _placed(model, f"K{number}", "aux")
        (coil,) = _placed(model, f"K{number}", "coil", "operating-device")
        refs = _cross_references(model)
        (home,) = (r for r in refs if r.function == _fid(model, contact))
        assert _pages(model, home.partners) == [_home(model, coil)]
        table = [r for r in refs if r.function == _fid(model, coil)]
        assert any(_home(model, contact) in _pages(model, [p]) for r in table for p in r.partners)


def test_a_contact_with_a_second_wire_stays_in_its_own_group() -> None:
    model = _built()
    (contact,) = _placed(model, "K4", "aux")
    (coil,) = _placed(model, "K4", "coil", "operating-device")
    assert _home(model, contact) == _home(model, coil)


def test_a_box_stays_on_its_group_page_when_its_contacts_come_from_two_groups() -> None:
    """layout-0103: the contacts of two groups under one box never home the box on the last page."""
    model = _built(split=True)
    box = _channel_box(model)
    coils = [_placed(model, f"K{n}", "coil", "operating-device")[0] for n in (2, 3)]
    assert all(_home(model, box) != _home(model, c) for c in coils)
    pages = _gap(model, "document fact")
    same_set = [
        pages[p.page].number
        for p in _gap(model, "symbol subject").values()
        if _home(model, p)[0] == _home(model, box)[0]
    ]
    assert pages[box.page].number == min(same_set)
    for number in (2, 3):
        (contact,) = _placed(model, f"K{number}", "aux")
        assert (contact.drawing_set, contact.page) == (box.drawing_set, box.page)


def _boxes(model) -> list:
    """The generic boxes the core path draws, all pages."""
    return [
        s
        for drawing in drawn_pages(model).values()
        for s in drawing.symbols
        if s.key == GENERIC_BOX_KEY
    ]


def test_channel_pins_stand_one_and_a_half_pole_pitches_apart_and_their_texts_keep_the_gap() -> (
    None
):
    """V5 pitch: pins 1.5 pole pitches apart (texts widen it only where needed), no text nearer."""
    model = _built()
    (box,) = (p for p in _boxes(model) if any("di_" in n for n, _ in p.offsets))
    sides = dict(box.sides)
    south = sorted(x for port, x in box.offsets if sides[port] == "s")
    assert [b - a for a, b in pairwise(south)] == [channel_pitch()] * (len(south) - 1)
    assert channel_pitch() * 2 == 3 * (symbol_geometry("circuit-breaker", poles=3).ports[2].at.x)
    placed = [_placed(model, f"K{n}", "aux")[0] for n in (2, 3)]
    x0, x1 = min(p.x for p in placed), max(p.x for p in placed)
    y0 = min(p.y for p in placed)
    under = [
        label
        for label in _gap(model, "text subject").values()
        if label.page == placed[0].page and x0 - 20 <= label.x <= x1 + 90 and label.y >= y0 - 40
    ]
    assert len(under) >= 6, "the contacts' texts were not found: the check would pass over nothing"
    pins = sorted(p.x for p in placed)
    owner = lambda box: max(x for x in pins if x <= box.x)  # noqa: E731 -- local, one use
    for one, other in combinations(under, 2):
        if owner(one) == owner(other):
            continue  # one contact's own texts sit by design
        dx = max(one.x, other.x) - min(one.x + one.width, other.x + other.width)
        dy = max(one.y, other.y) - min(one.y + one.height, other.y + other.height)
        assert max(dx, dy) >= WIRING_GRID, (one, other)


def _rail_plant(d) -> None:
    """One contactor K2 whose aux 14 goes to a DI channel and whose aux 13 goes to a 24 V rail."""
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group") as g1:
        zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("R", 2, bridged=True)
        d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
        contactor = d.device("K2", "DEMO-CTR-3P-NC")
    d.layout.break_before(g1)
    d.detail.wire(contactor.aux["14"], module.di_1["1"], wire=(BU, 0.5))
    d.detail.wire(contactor.aux["13"], rail[1].outer, wire=(BU, 0.5))


def test_a_contact_hangs_straight_down_and_its_column_ends_in_a_downward_supply_bar() -> None:
    """V5, layout-0103: pin, 98/14, contact turned 180, 97/13, supply bar pointing down; no wire
    turns back (the round-3 U-turn put the contact beside the line and a horizontal wire to it)."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _rail_plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    box = _channel_box(model)
    (contact,) = _placed(model, "K2", "aux")
    line = _pin_x(box, "di_1.1")
    assert _pin_x(contact, "out") == line, "the contact stands in its channel pin's column"
    assert _port_y(contact, "out") < _port_y(contact, "in"), "98/14 above 97/13"
    (route,) = (r for r in _gap(model, "wire net").values() if {p.x for p in r.points} == {line})
    assert len({p.x for p in route.points}) == 1, "no horizontal wire, no turn back"
    port_of = {(p.function, p.name): pid for pid, p in ports(model).items()}
    (bar,) = (
        s
        for s in layout_of(model, PowerSymbol).values()
        if s.port == port_of[_fid(model, contact), "13"]
    )
    assert bar.symbol == "power-supply"
    assert bar.y > _port_y(contact, "in"), "the bar stands below the contact"
    assert bar.orientation.name == "R180", bar.orientation


def _plant_16(d) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-16")
    with d.function("G1", "Contactor group") as g1:
        contactors = [d.device(f"K{n + 1}", "DEMO-CTR-3P-NC") for n in range(1, 17)]
        lamps = [d.device(f"P{n}", "DEMO-LAMP-24") for n in range(1, 17)]
    d.layout.break_before(g1)
    for number, (contactor, lamp) in enumerate(zip(contactors, lamps, strict=True), start=1):
        d.detail.wire(contactor.coil["A1"], lamp.lamp["1"], wire=(BU, 0.5))
        channel = getattr(module, f"di_{number}")[str(number)]
        d.detail.wire(contactor.aux["14"], channel, wire=(BU, 0.5))


def _content_width(model, page) -> int:
    """The content width in G of the sheet a page is drawn on (the house sheet)."""
    return _gap(model, "document fact")[page]


def test_a_sixteen_channel_module_fits_one_page_with_a_contact_under_every_channel() -> None:
    """V5 (layout-0103): 16 channels at 1.5 pole pitches fit a page; none falls back to a reference.

    Engineering shape: a 16-channel DI module in its own group, every channel wired from the
    auxiliary contact of a contactor in a second group. The bug: at the house column spacing the
    module was 16 columns wide, so its widened slots could not fit and its contacts stayed home.
    """
    model = _staged(sixteen=True)[0]
    box = _channel_box(model)
    assert box.x + max(box.offsets.values()) <= _content_width(model, box.page)
    for number in range(1, 17):
        (contact,) = _placed(model, f"K{number + 1}", "aux")
        assert _home(model, contact) == _home(model, box), number
        assert _pin_x(contact, "out") == _pin_x(box, f"di_{number}.{number}"), number


def _drawing(model) -> str:
    """A digest of what is drawn: placements, label boxes and routes, no keep-out."""
    pages = _gap(model, "document fact")
    placed = sorted(
        (p.owner or "", p.symbol, pages[p.page].drawing_set.value, p.page.value, p.x, p.y)
        for p in _gap(model, "symbol subject").values()
    )
    texts = sorted(
        (o.function and o.function.value, o.slot, o.kind.value, o.page.value, o.x, o.y)
        for o in _gap(model, "text subject").values()
    )
    routes = sorted(
        (r.page.value, r.style, tuple((p.x, p.y) for p in r.points))
        for r in _gap(model, "wire net").values()
    )
    return sha256(repr((placed, texts, routes)).encode()).hexdigest()[:16]


# the digests of the core's drawing of each circuit (the old engine's digests cannot hold)
_DRAWING = {"plain": "68479d336d11ef21", "split": "7f46f7b04577fe03", "sixteen": "a2c5fc2659d765c5"}


@pytest.fixture(scope="module")
def builds() -> dict:
    """The three circuits, built once for the digest and overlap tests."""
    return {
        "plain": _staged(),
        "split": _staged(split=True),
        "sixteen": _staged(sixteen=True),
    }


@pytest.mark.parametrize("name", list(_DRAWING))
def test_the_contact_drawing_is_as_it_was_before_the_keep_out_fix(name: str, builds: dict) -> None:
    """layout-0125: the keep-out is cut after placing, so placements, texts and routes stay."""
    model, _ = builds[name]
    assert _drawing(model) == _DRAWING[name]


@pytest.mark.parametrize("name", list(_DRAWING))
def test_contacts_under_adjacent_channel_pins_overlap_nowhere(name: str, builds: dict) -> None:
    """layout-0125: a keep-out holds the ink drawn (33 wide), not the 74 of its slots."""
    _, findings = builds[name]
    assert [f for f in findings if f.code == "SYMBOL_OVERLAP"] == []
