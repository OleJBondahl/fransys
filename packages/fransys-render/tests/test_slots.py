"""`draw_symbol`: a symdef symbol drawn from plain values, nothing computed (acceptance 9)."""

import dataclasses
import re
from decimal import Decimal
from pathlib import Path

import pytest
from fransys_render._slots import draw_symbol
from symdef import Fill, InvalidValueError, Polyline, UnknownNameError

from electrical_symbols import LIBRARY
from fransys_model.kernel import make_id
from fransys_model.layout import Orientation, SheetFormat

CHANNELS = {"c1": 64, "c2": 320, "c3": 512, "c4": 832}  # G: 8, 40, 64, 104 M
WIDTH_G = 896  # 112 M
MODULE = Decimal("2.5")


def sheet():
    key = ("sheet_format", "t")
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="t",
        width_mm=300,
        height_mm=200,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=280,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=MODULE,
    )


def draw(key="card", library=LIBRARY, **values):
    return draw_symbol(
        library, key, sheet=sheet(), at=(0, 0), font_mm=Decimal("2.5"),
        orientation=Orientation.R0, **values,
    )  # fmt: skip


def numbers(text):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]


def body_xs(text):
    match = re.search(r'<polygon points="([^"]+)"', text)
    assert match is not None
    return numbers(match.group(1))[::2]


def card():
    return draw(lengths={"x": WIDTH_G}, offsets={"x": {"c1": 64, "c2": 320, "c3": 512, "c4": 832}})


def test_stretched_card_body_width_is_the_passed_length():
    xs = body_xs(card())
    assert max(xs) - min(xs) == WIDTH_G / 8 * 2.5


def test_stretched_card_ports_stand_at_the_passed_offsets():
    leads = re.findall(r'<line x1="([^"]+)" y1="[^"]+" x2="([^"]+)"', card())
    assert sorted(float(a) for a, _ in leads) == [g / 8 * 2.5 for g in sorted(CHANNELS.values())]


def test_the_values_win_over_anything_derivable_from_the_ports():
    """Offsets that would imply a narrower body do not shrink the passed length."""
    text = draw(lengths={"x": WIDTH_G}, offsets={"x": {"c1": 64, "c2": 128, "c3": 192, "c4": 256}})
    xs = body_xs(text)
    assert max(xs) - min(xs) == 280


def test_link_wire_draws_dashed_and_wire_solid():
    points = [(0, 0), (80, 0), (80, 48)]
    assert "stroke-dasharray" in draw("link", points=points)
    assert "stroke-dasharray" not in draw("wire", points=points)


def test_a_table_is_drawn_from_n_and_its_head():
    text = draw("cable-column", n=3, axis="x", head="cable-head")
    assert text.count("<line") == 6


def test_a_slot_text_for_a_missing_slot_raises_symdefs_unknown_name_error():
    with pytest.raises(UnknownNameError, match="nope"):
        draw(lengths={"x": WIDTH_G}, texts={"nope": "x"})


def test_a_slot_text_is_drawn_by_symdef():
    text = draw("break-contact", texts={"tag": "-A1"})
    assert re.search(r"<text [^>]*>-A1</text>", text)


def test_a_missing_required_slot_raises():
    library = dataclasses.replace(LIBRARY, required_slots=("tag",))
    with pytest.raises(InvalidValueError, match="tag"):
        draw("break-contact", library=library, texts={})


def test_no_texts_draws_no_text():
    assert "<text" not in draw("break-contact")


def test_a_tint_reaches_the_fill():
    tinted = dataclasses.replace(
        LIBRARY.get("group-frame"),
        elements=(dataclasses.replace(LIBRARY.get("group-frame").elements[0], fill=Fill.TINT),),
    )
    assert isinstance(tinted.elements[0], Polyline)
    library = dataclasses.replace(LIBRARY, symbols={**LIBRARY.symbols, "tinted": tinted})
    assert 'fill="#ffe0e0"' in draw(
        "tinted", library=library, lengths={"x": 96, "y": 96}, tint="#ffe0e0"
    )
    assert 'fill="#ffe0e0"' not in draw("tinted", library=library, lengths={"x": 96, "y": 96})


def test_the_module_computes_no_length():
    source = Path(__file__).parent.parent / "src" / "fransys_render" / "_slots.py"
    text = source.read_text(encoding="utf-8")
    assert "body_box" not in text
    assert text.count("lengths[axis]") == 1
