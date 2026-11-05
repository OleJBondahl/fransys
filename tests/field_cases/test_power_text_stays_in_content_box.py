"""Field case: a supply bar prints its rail's potential in its fixed slot, clear of the frame and of its neighbours.
The bug (KI-524, R1368 S6): the bar printed no text, so a 24 V and a 5 V rail drew the same symbol. Fixed by el-0113 (R1554, R1557):
`power_marks` passes `derive.port_power_text` in the symbol's `marking.supply` slot, a 2.5-module box above the bar."""

import re
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _core_boxes import overlaps
from _drawn_extent import body_g, page_ink
from _drawn_pages import drawn_pages, markers_in
from _model_build_cover import unit_document
from fransys.colours import BU
from symdef import Orientation, Weight, measure, orient, to_fragment_mm
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS

from electrical_symbols import LIBRARY
from fransys_model.layout import PowerSymbol, layout_of

if TYPE_CHECKING:
    from pathlib import Path

_MM = 2.5 / LIBRARY.grid.divisions_per_module  # one G in mm
_SLOT = "marking.supply"
_EPS = 1e-6  # ink and slot are the same float in mm up to rounding


def _build():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        loads = [(d.device(f"K{i}", "DEMO-PLC-DI-2"), d.device(f"P{i}", "DEMO-LAMP-24")) for i in range(5)]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    for di, lamp in loads:
        d.series(psu.output["+"], di.di_1["1"], wire=(BU, 0.5))
        d.series(psu.output["+"], lamp["1"], wire=(BU, 0.5))
        d.series(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _two_rails(tmp_path: Path, *, names: tuple[str, str] = ("5V", "GND5"), loads: int = 1):
    """The 24 V and the 5 V rail, each with `loads` lamps (R1368 S6)."""
    d = fr.design("demo_parts", place="CAB")
    with d.function("G0", "Supply"):
        p24 = d.terminal_strip("X10", "DEMO-TB-2.5", 4).run("P", 4, bridged=True, rail=True)
        p5 = d.terminal_strip("X12", "DEMO-TB-2.5", 4).run("V", 4, bridged=True, rail=True)
        g24 = d.terminal_strip("X11", "DEMO-TB-2.5", 4).run("M", 4, bridged=True, rail=True)
        g5 = d.terminal_strip("X13", "DEMO-TB-2.5", 4).run("N", 4, bridged=True, rail=True)
        d.dc_supply("S24", plus=p24[1], minus=g24[1], voltage=24)
        d.dc_supply("S5", plus=p5[1], minus=g5[1], voltage=5, names=names)
        for i in range(loads):
            d.series(p24, d.device(f"H{3 + 2 * i}", "DEMO-LAMP-24").lamp, g24, wire=(BU, 0.5))
            d.series(p5, d.device(f"H{4 + 2 * i}", "DEMO-LAMP-24").lamp, g5, wire=(BU, 0.5))
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, d.location("CAB", "Cabinet"), cover=tmp_path / "c.md"))


def _supplies(model):
    """Every drawn power symbol with its page's drawing: the slot strings are what the page prints for it."""
    return [(d, s) for d in drawn_pages(model).values() for s in d.symbols if s.key in ("power-supply", "ground", "protective-earth")]


def _slot_g(symbol) -> tuple[float, float, float, float]:
    """The declared `marking.supply` box of a drawn symbol on its page in G, after its turn."""
    box = measure(LIBRARY.get(symbol.key), Orientation(symbol.orient), LIBRARY, dict(symbol.slots), 1.0).slots[_SLOT]
    return (float(symbol.x + box.min.x), float(symbol.y + box.min.y), float(symbol.x + box.max.x), float(symbol.y + box.max.y))


def _texts(model) -> list[tuple[Any, Any, str]]:
    return [(d, s, t) for d, s in _supplies(model) if s.key == "power-supply" for slot, t in s.slots if slot == _SLOT]


def test_no_power_text_touches_the_content_box_edge() -> None:
    model = _build().model
    texts = _texts(model)
    assert texts
    for drawing, symbol, _ in texts:
        x0, y0, x1, y1 = _slot_g(symbol)
        assert x0 > 0
        assert x1 < drawing.area.w
        assert y0 > 0
        assert y1 < drawing.area.h


def _t1(model):
    """The PSU's page: its box, its supply slot box, in G."""
    ground = next(
        o for o in layout_of(model, PowerSymbol).values() if fr.derive.port_designation(model, o.port).startswith("-T1:") and o.symbol == "ground"
    )
    drawing = drawn_pages(model)[ground.page]
    # a drawn symbol names no subject: the PSU is the box under its printed tag
    tag = next(t for t in drawing.texts if t.text == "-T1")
    psu = min(
        (s for s in drawing.symbols if s.key == "generic-box"),
        key=lambda s: abs(s.x - tag.box.x) + abs(s.y - tag.box.y),
    )
    supply = [s for s in drawing.symbols if s.key == "power-supply" and (_SLOT, "24V") in s.slots]
    assert supply, "the PSU's page draws no supply bar with the text '24V'"
    return body_g(psu), _slot_g(supply[0]), drawing


def test_a_supply_text_has_room_past_its_bar_and_stays_clear_of_the_frame() -> None:
    built = _build()
    box, text, drawing = _t1(built.model)
    assert [f for f in built.findings if f.code == "ANNEX_UNPLACED"] == []
    assert text[0] > 0
    assert text[2] < drawing.area.w
    assert not overlaps(text, box)
    assert box[0] >= 0  # inside the content box; flush at the frame edge, as any first box (0114)


def test_two_flagged_rails_of_different_potential_print_their_potential(tmp_path: Path) -> None:
    """R1368 S6: a 24 V and a 5 V rail draw the same power symbol, so each prints its own potential in its slot (derive.port_power_text)."""
    model = _two_rails(tmp_path).model
    printed = [t for _, _, t in _texts(model)]
    assert {"24V", "5V"} <= set(printed), f"the supply bars of the 24 V and 5 V rails print no potential (slot texts: {sorted(printed)})"
    for _, symbol in _supplies(model):
        if symbol.key == "power-supply":
            ((slot, text),) = symbol.slots
            assert slot == _SLOT
            assert text == fr.derive.port_power_text(
                model, next(o.port for o in layout_of(model, PowerSymbol).values() if symbol.ports == (o.port.value,))
            )


def test_ground_and_pe_print_no_text(tmp_path: Path) -> None:
    """G08-POWER: only the supply bar prints; a ground or a protective earth carries no slot string."""
    model = _two_rails(tmp_path).model
    others = [s for _, s in _supplies(model) if s.key != "power-supply"]
    assert others
    assert all(s.slots == () for s in others)


@pytest.mark.rule("TEXT-BOX-MEASURED")
def test_a_supply_name_longer_than_the_bar_is_measured_not_refused(tmp_path: Path) -> None:
    """R1619: the box is the text's, so a long name draws whole, in its own box, meeting nothing, with no error (TEXT-BOX-MEASURED)."""
    built = _two_rails(tmp_path, names=("SUPPLY_FIVE_RAIL", "GND5"))
    assert [f for f in built.findings if f.severity is fr.Severity.ERROR] == []
    assert _assert_ink(built) >= 2
    wide = [s for _, s in _supplies(built.model) if (_SLOT, "SUPPLY_FIVE_RAIL") in s.slots]
    assert wide
    assert all(x1 - x0 > 2 * LIBRARY.grid.divisions_per_module for x0, _, x1, _ in map(_slot_g, wide))
    for s in wide:  # the obstacle OVERLAP reads is that same measured box, not the declared one
        ((slot, box),) = s.slot_ink
        x0, y0, x1, y1 = _slot_g(s)
        assert slot == _SLOT
        assert (box.x, box.y, box.x + box.w, box.y + box.h) == pytest.approx((x0, y0, x1, y1))


def _mm(box: tuple[float, float, float, float], origin: tuple[float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (x0 * _MM + origin[0], y0 * _MM + origin[1], x1 * _MM + origin[0], y1 * _MM + origin[1])


def _assert_ink(built) -> int:
    """Compiled pages of `built`: each supply ink stands in the content box and its slot and meets nothing; the count."""
    seen = 0
    for page, drawing in drawn_pages(built.model).items():
        svg = next(v for k, v in built.page_svgs.items() if k == f"{page.kind}:{page.value}")
        found = re.search(r"translate\(([-\d.]+) ([-\d.]+)\)", svg)
        assert found
        origin = (float(found.group(1)), float(found.group(2)))  # the content box's corner on the sheet
        inks = page_ink(svg)
        content = _mm((0, 0, drawing.area.w, drawing.area.h), origin)
        for symbol in (s for s in drawing.symbols if s.key == "power-supply"):
            ((_, text),) = symbol.slots
            here = (symbol.x * _MM + origin[0], symbol.y * _MM + origin[1])
            ink = next(i for i in inks if i.text == text and i.origin == pytest.approx(here))
            seen += 1
            assert content[0] < ink.box[0]
            assert ink.box[2] < content[2]
            assert content[1] < ink.box[1]
            assert ink.box[3] < content[3]
            slot = _mm(_slot_g(symbol), origin)
            assert slot[0] - _EPS <= ink.box[0]
            assert ink.box[2] <= slot[2] + _EPS
            assert slot[1] - _EPS <= ink.box[1]
            assert ink.box[3] <= slot[3] + _EPS
            others = [i.box for i in inks if i is not ink]
            others += [
                _mm((s.outline.x, s.outline.y, s.outline.x + s.outline.w, s.outline.y + s.outline.h), origin) for s in drawing.symbols if s.outline
            ]
            others += [
                _mm((m.outline.x, m.outline.y, m.outline.x + m.outline.w, m.outline.y + m.outline.h), origin)
                for m in markers_in(drawing)
                if m.outline
            ]
            for wire in drawing.wires:
                for (ax, ay), (bx, by) in zip(wire.points, wire.points[1:], strict=False):
                    others.append(_mm((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)), origin))
            for box in others:
                assert not (ink.box[0] < box[2] and box[0] < ink.box[2] and ink.box[1] < box[3] and box[1] < ink.box[3]), (text, ink.box, box)
    return seen


@pytest.mark.parametrize("loads", [0, 1, 3])
def test_the_ink_of_every_supply_text_stands_in_its_slot_and_meets_nothing(tmp_path: Path, loads: int) -> None:
    """The two-rail plant (1 or 3 loads each) and the five-load PSU plant (0)."""
    assert _assert_ink(_two_rails(tmp_path, loads=loads) if loads else _build()) >= 2


@pytest.mark.parametrize("name", CASE_PARAMS)
def test_the_ink_of_every_supply_text_in_the_corpus_stands_in_its_slot_and_meets_nothing(name: str) -> None:
    """Every placement corpus build and the skid: a supply text meets nothing, so the pose must hold its slot (R1605)."""
    _assert_ink(BUILDS[name]())


@pytest.mark.rule("TEXT-BOX-MEASURED")
@pytest.mark.parametrize("turn", list(Orientation))
def test_the_ink_of_the_longest_text_stands_in_the_slot_and_beyond_the_bar_in_every_turn(turn: Orientation) -> None:
    """R1557: in each of the eight turned views the ink of '-15V' lies in the declared slot box and clear of the body."""
    turned = orient(LIBRARY.get("power-supply"), turn)
    fragment = to_fragment_mm(
        turned,
        module_mm=2.5,
        weights_mm={Weight.NORMAL: 0.25, Weight.THICK: 0.5},
        dash_mm=(1, 1),
        dash_dot_mm=(1, 1, 1, 1),
        font_family="DejaVu Sans",
        font_mm=2.4691,
        cap_ratio=LIBRARY.font.cap_height / LIBRARY.font.units_per_em,
        texts={_SLOT: "-15V"},
    )
    (ink,) = page_ink(f'<svg xmlns="http://www.w3.org/2000/svg">{fragment}</svg>')
    found = measure(turned, Orientation.R0, LIBRARY, {_SLOT: "-15V"}, 1.0)
    slot, body = _mm_box(found.slots[_SLOT]), _mm_box(found.body)
    assert slot[0] - _EPS <= ink.box[0]
    assert ink.box[2] <= slot[2] + _EPS
    assert slot[1] - _EPS <= ink.box[1]
    assert ink.box[3] <= slot[3] + _EPS
    assert not (ink.box[0] < body[2] and body[0] < ink.box[2] and ink.box[1] < body[3] and body[1] < ink.box[3])


def _mm_box(box: Any) -> tuple[float, float, float, float]:
    return (float(box.min.x * _MM), float(box.min.y * _MM), float(box.max.x * _MM), float(box.max.y * _MM))
