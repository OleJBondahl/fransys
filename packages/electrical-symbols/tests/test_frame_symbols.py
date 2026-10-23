"""Markers, frames, the dot and the wire styles (SYMDEF-SLOTS SS5 c, SS7, SS8)."""

import json
from pathlib import Path

import pytest
from symdef import Polyline, Style, Weight, body_box, load_bundle, stretch, wire

from electrical_symbols import LIBRARY

BUNDLE = Path(__file__).parent.parent / "src" / "electrical_symbols" / "bundle.json"
FRAMES = ["unit-outline", "harness-frame", "group-frame"]
POINTS = [(0, 0), (4, 0), (4, 6)]


@pytest.mark.parametrize("key", FRAMES)
def test_a_frame_stretched_by_two_calls_keeps_its_label_at_the_top_left(key):
    """Spec acceptance 8 on the real files: 120 by 80, label slot at the top-left corner."""
    frame = stretch(stretch(LIBRARY.get(key), "x", 120), "y", 80)
    box = body_box(frame)
    assert (box.max.x - box.min.x, box.max.y - box.min.y) == (120, 80)
    label = next(s for s in frame.slots if s.id == "label")
    assert (label.position.x, label.position.y) == (box.min.x + 0.25, box.min.y + 0.75)


@pytest.mark.parametrize("key", FRAMES)
def test_a_frame_has_one_stretch_per_axis_and_no_ports(key):
    frame = LIBRARY.get(key)
    assert sorted(s.axis for s in frame.stretch) == ["x", "y"]
    assert frame.ports == ()


@pytest.mark.parametrize(
    ("style_id", "weight", "style"),
    [
        ("wire", Weight.NORMAL, Style.SOLID),
        ("trunk", Weight.THICK, Style.SOLID),
        ("link", Weight.NORMAL, Style.DASHED),
        ("by_others", Weight.NORMAL, Style.DASHED),
    ],
)
def test_wire_draws_one_polyline_in_the_named_style(style_id, weight, style):
    drawn = wire(LIBRARY, style_id, POINTS)
    (line,) = drawn.elements
    assert isinstance(line, Polyline)
    assert (line.weight, line.style) == (weight, style)
    assert [(p.x, p.y) for p in line.points] == POINTS


def test_the_library_has_exactly_the_seven_wire_styles():
    assert sorted(w.id for w in LIBRARY.wires) == [
        "by_others",
        "core",
        "diagram_line",
        "link",
        "marker",
        "trunk",
        "wire",
    ]


def test_the_bundle_carries_the_wires_and_round_trips():
    data = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert sorted(w["id"] for w in data["wires"]) == [
        "by_others",
        "core",
        "diagram_line",
        "link",
        "marker",
        "trunk",
        "wire",
    ]
    assert load_bundle(BUNDLE).wires == LIBRARY.wires


@pytest.mark.parametrize(
    ("key", "slot"),
    [("reference-marker", "ref"), ("cut-marker", "partner"), ("wire-label-frame", "label")],
)
def test_marker_and_label_frame_have_one_slot(key, slot):
    assert [s.id for s in LIBRARY.get(key).slots] == [slot]


def test_the_dot_is_one_filled_circle_with_no_ports_or_slots():
    dot = LIBRARY.get("junction-dot")
    assert len(dot.elements) == 1
    assert dot.ports == ()
    assert dot.slots == ()


@pytest.mark.parametrize(
    ("key", "style", "weight"),
    [
        ("unit-outline", Style.DASH_DOT, Weight.NORMAL),
        ("harness-frame", Style.SOLID, Weight.THICK),
        ("group-frame", Style.SOLID, Weight.NORMAL),
    ],
)
def test_frame_outline_styles(key, style, weight):
    outline = next(e for e in LIBRARY.get(key).elements if isinstance(e, Polyline))
    assert (outline.style, outline.weight) == (style, weight)
