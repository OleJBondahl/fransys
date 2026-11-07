"""Field case: a PLC input module with two wired channels, and two contactors whose contacts wire to channels in a second group.
The bug: chain discovery homed one contactor's contacts under its channel; the others stayed bundled and were missed.
Fixed by layout-0099 (a contact with one wire into another group homes under that pin); layout-0125 stops adjacent-channel overlap."""

from functools import cache
from hashlib import sha256
from itertools import combinations, pairwise
from typing import Any

import fransys as fr
import pytest
from _drawn_facts import document_facts, pin_turn, symbol_subjects, text_subjects, wire_nets
from _model_build_cover import unit_document
from fransys.colours import BU

from electrical_symbols import GENERIC_BOX_KEY
from fransys_layout.geometry import WIRING_GRID
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _plant(d, *, split: bool = False) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group"):
        lamps = {n: d.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4)}
        contactors = {n: d.device(f"K{n}", "DEMO-CTR-3P-NC") for n in (2, 3, 4) if not split or n != 3}
    if split:
        with d.function("G2", "Second contactor group"):
            contactors[3] = d.device("K3", "DEMO-CTR-3P-NC")
    for number, contactor in contactors.items():
        d.series(contactor.coil["A1"], lamps[number].lamp["1"], wire=(BU, 0.5))
        d.series(contactor.main["1"], lamps[number].lamp["1"], wire=(BU, 0.5))  # layout-0112: wired
        channel = getattr(module, f"di_{number - 1}")[str(number - 1)]
        d.series(contactor.aux["14"], channel, wire=(BU, 0.5))
    d.series(contactors[4].aux["13"], lamps[4].lamp["2"], wire=(BU, 0.5))
    returns = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    for number in (2, 3):  # a single-wire contact: its 13 pin lands on its own return terminal
        d.series(contactors[number].aux["13"], returns[number - 1].outer, wire=(BU, 0.5))
    for number, contactor in contactors.items():  # each coil closes its loop through its lamp, K4's on a return terminal
        far = returns[3].outer if number == 4 else lamps[number].lamp["2"]
        d.series(contactor.coil["A2"], far, wire=(BU, 0.5))


@cache
def _staged(*, split: bool = False, sixteen: bool = False) -> tuple[Any, ...]:
    """The built model and its findings of one circuit, built once; read only."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    if sixteen:
        _plant_16(d)
    else:
        _plant(d, split=split)
    built = fr.build(d, unit_document(cab))
    return built.model, built.findings


def _built(*, split: bool = False):
    return _staged(split=split)[0]


def _placed(model, tag: str, name: str, symbol: str | None = None) -> list[Any]:
    """The drawn symbols of function `name` of item `tag`, optionally of one library symbol."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    wanted = {f.id.value for f in functions(model).values() if f.name == name and tag_of[f.item] == tag}
    return [s for s in symbol_subjects(model) if s.owner in wanted and symbol in (None, s.symbol)]


def _home(model, placed) -> tuple[Any, ...]:
    """The drawing set and the page a drawn symbol stands on."""
    return document_facts(model)[placed.page].drawing_set, placed.page


def _port_at(placed, port: str) -> tuple[Any, Any]:
    """The page position of port `port` of the drawn symbol `placed`."""
    if placed.symbol == GENERIC_BOX_KEY:
        return placed.x + placed.offsets[port], placed.y
    found = pin_turn(placed.symbol, port, poles=placed.poles, orient=placed.orient)
    return placed.x + found.dx, placed.y + found.dy


def _pin_x(placed, port: str) -> Any:
    return _port_at(placed, port)[0]


def _port_y(placed, port: str) -> Any:
    return _port_at(placed, port)[1]


def _channel_box(model):
    """The PLC module's box: the one generic box with channel (`di_`) ports."""
    (box,) = (s for s in symbol_subjects(model) if s.symbol == GENERIC_BOX_KEY and any("di_" in n for n in s.offsets))
    return box


def _fid(model, placed):
    """The id of the function a drawn symbol belongs to."""
    (found,) = (f.id for f in functions(model).values() if f.id.value == placed.owner)
    return found


def _cross_references(model) -> list[Any]:
    return [x for x in _gap(model, "text subject").values() if x.kind.name == "CROSS_REFERENCE"]


def _pages(model, partners) -> list[Any]:
    return [(document_facts(model)[p.page].drawing_set, p.page) for p in partners]


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


def _rail_plant(d) -> None:
    """One contactor K2 whose aux 14 goes to a DI channel and whose aux 13 goes to a 24 V rail."""
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
    with d.function("G1", "Contactor group"):
        zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("R", 2, bridged=True, rail=True)
        d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
        contactor = d.device("K2", "DEMO-CTR-3P-NC")
    d.series(contactor.aux["14"], module.di_1["1"], wire=(BU, 0.5))
    d.series(contactor.aux["13"], rail[1].outer, wire=(BU, 0.5))


def test_a_contact_hangs_straight_down_and_its_column_ends_in_a_downward_supply_bar() -> None:
    """V5, layout-0103: pin, 98/14, contact turned 180, 97/13, supply bar pointing down; no wire
    turns back (the round-3 U-turn put the contact beside the line and a horizontal wire to it)."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _rail_plant(d)
    model = fr.build(d, unit_document(cab)).model
    box = _channel_box(model)
    (contact,) = _placed(model, "K2", "aux")
    line = _pin_x(box, "di_1.1")
    assert _pin_x(contact, "out") == line, "the contact stands in its channel pin's column"
    assert _port_y(contact, "out") < _port_y(contact, "in"), "98/14 above 97/13"
    column = [w for _, w in wire_nets(model) if line in {p[0] for p in w.points}]
    assert len(column) == 2, "pin to contact and contact to supply bar: a straight column is two wires"
    assert all({p[0] for p in w.points} == {line} for w in column), "no horizontal wire, no turn back"
    port_of = {(p.function, p.name): pid for pid, p in ports(model).items()}
    (bar,) = (s for s in layout_of(model, PowerSymbol).values() if s.port == port_of[_fid(model, contact), "13"])
    assert bar.symbol == "power-supply"
    assert bar.y > _port_y(contact, "in"), "the bar stands below the contact"
    assert bar.orientation.name == "R180", bar.orientation


def _plant_16(d) -> None:
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-16")
    with d.function("G1", "Contactor group"):
        zero = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("R", 16, bridged=True, rail=True)
        d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
        contactors = [d.device(f"K{n + 1}", "DEMO-CTR-3P-NC") for n in range(1, 17)]
        lamps = [d.device(f"P{n}", "DEMO-LAMP-24") for n in range(1, 17)]
    for number, (contactor, lamp) in enumerate(zip(contactors, lamps, strict=True), start=1):
        d.series(contactor.coil["A1"], lamp.lamp["1"], wire=(BU, 0.5))
        channel = getattr(module, f"di_{number}")[str(number)]
        d.series(contactor.aux["14"], channel, wire=(BU, 0.5))
        d.series(contactor.aux["13"], rail[number].outer, wire=(BU, 0.5))
        d.series(contactor.coil["A2"], lamp.lamp["2"], wire=(BU, 0.5))


def _content_width(model, page) -> Any:
    """The content width in G of the sheet a page is drawn on (the house sheet)."""
    return _gap(model, "document fact")[page]


def test_a_sixteen_channel_module_fits_one_page_with_a_contact_under_every_channel() -> None:
    """V5 (layout-0103): 16 channels at 1.5 pole pitches fit a page; none falls back to a reference.

    Engineering shape: a 16-channel DI module in its own group, every channel wired from the
    auxiliary contact of a contactor in a second group. The bug: at the house column spacing the
    """
    model = _staged(sixteen=True)[0]
    box = _channel_box(model)
    assert box.x + max(box.offsets.values()) <= _content_width(model, box.page)
    for number in range(1, 17):
        (contact,) = _placed(model, f"K{number + 1}", "aux")
        assert _home(model, contact) == _home(model, box), number
        assert _pin_x(contact, "out") == _pin_x(box, f"di_{number}.{number}"), number


def test_channel_pins_stand_one_and_a_half_pole_pitches_apart_and_their_texts_keep_the_gap() -> None:
    """V5 pitch: pins 1.5 pole pitches apart (texts widen it only where needed), no text nearer."""
    model = _built()
    box = _channel_box(model)
    sides = dict(box.sides)
    south = sorted(x for port, x in dict(box.offsets).items() if sides[port] == "s")
    pole = pin_turn("circuit-breaker", "2.in", poles=3).dx - pin_turn("circuit-breaker", "1.in", poles=3).dx
    assert [b - a for a, b in pairwise(south)] == [pole * 3 // 2] * (len(south) - 1)
    placed = [_placed(model, f"K{n}", "aux")[0] for n in (2, 3)]
    x0, x1 = min(p.x for p in placed), max(p.x for p in placed)
    y0 = min(p.y for p in placed)
    under = [label for label in text_subjects(model) if label.page == placed[0].page and x0 - 20 <= label.box.x <= x1 + 90 and label.box.y >= y0 - 40]
    assert len(under) >= 6, "the contacts' texts were not found: the check would pass over nothing"
    pins = sorted(p.x for p in placed)
    for one, other in combinations(under, 2):
        if max(x for x in pins if x <= one.box.x) == max(x for x in pins if x <= other.box.x):
            continue  # one contact's own texts sit by design
        dx = max(one.box.x, other.box.x) - min(one.box.x + one.box.width, other.box.x + other.box.width)
        dy = max(one.box.y, other.box.y) - min(one.box.y + one.box.height, other.box.y + other.box.height)
        assert max(dx, dy) >= WIRING_GRID, (one, other)


def _drawing(model) -> str:
    """A digest of what is drawn: placements, label boxes and routes, no keep-out."""
    pages = document_facts(model)
    placed = sorted((p.owner or "", p.symbol, pages[p.page].drawing_set.value, p.page.value, p.x, p.y) for p in symbol_subjects(model))
    texts = sorted((o.function and o.function.value, o.slot, o.kind.value, o.page.value, o.x, o.y) for o in _gap(model, "text subject").values())
    routes = sorted((page.value, w.style, tuple(w.points)) for page, w in wire_nets(model))
    return sha256(repr((placed, texts, routes)).encode()).hexdigest()[:16]


# the digests of the core's drawing of each circuit (the old engine's digests cannot hold)
_DRAWING = {"plain": "68479d336d11ef21", "split": "7f46f7b04577fe03", "sixteen": "a2c5fc2659d765c5"}


@pytest.fixture(scope="module")
def builds() -> dict[str, Any]:
    """The three circuits, built once for the digest and overlap tests."""
    return {
        "plain": _staged(),
        "split": _staged(split=True),
        "sixteen": _staged(sixteen=True),
    }


@pytest.mark.parametrize("name", list(_DRAWING))
def test_the_contact_drawing_is_as_it_was_before_the_keep_out_fix(name: str, builds: dict[str, Any]) -> None:
    """layout-0125: the keep-out is cut after placing, so placements, texts and routes stay."""
    model, _ = builds[name]
    assert _drawing(model) == _DRAWING[name]


@pytest.mark.parametrize("name", list(_DRAWING))
def test_contacts_under_adjacent_channel_pins_overlap_nowhere(name: str, builds: dict[str, Any]) -> None:
    """layout-0125: a keep-out holds the ink drawn (33 wide), not the 74 of its slots."""
    _, findings = builds[name]
    assert [f for f in findings if f.code == "SYMBOL_OVERLAP"] == []


@pytest.mark.parametrize("name", list(_DRAWING))
def test_every_contact_wire_has_a_row_to_turn_on_and_is_drawn(name: str, builds: dict[str, Any]) -> None:
    """layout-0484: a folded member's head pin stands level with its join's pin, so no join jog lacks a row."""
    _, findings = builds[name]
    assert [f.code for f in findings if f.code == "CONNECTION_NOT_DRAWN"] == []
