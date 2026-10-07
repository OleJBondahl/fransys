"""CD8 at N1 (CT5-TURN, acceptance 25): core text no longer sets the pitch, the box holds it.

Hand-built facts, widths in G at the house text height. Each test names its probe.
"""

from dataclasses import replace

from cable_facts import block_facts

from electrical_symbols import text_width
from fransys_layout.engines.cable.place import block_pitch, place_block

_H = 8
_A3_BODY = (1280, 787)  # G, layout-0141's house sheet
_CORE = "12 WHOG"


def _facts(cores: int, pins: int, core_text: str = _CORE):
    """`cores` straight cores to a bottom end of `pins` pins (the extra ones free), real widths."""
    facts = block_facts([(0, 0)] * cores, label=60, text=text_width(core_text, height=_H))
    bottom = facts.bottom[0]
    free = tuple(
        replace(bottom.pins[0], landed=False, marking_width=text_width(str(n), height=_H))
        for n in range(cores + 1, pins + 1)
    )
    marked = tuple(
        replace(pin, marking_width=text_width(str(n), height=_H))
        for n, pin in enumerate(bottom.pins, 1)
    )
    top = tuple(
        replace(
            end,
            pins=tuple(
                replace(p, marking_width=text_width(str(n), height=_H))
                for n, p in enumerate(end.pins, 1)
            ),
        )
        for end in facts.top
    )
    return replace(
        facts,
        text_height=_H,
        pad=2,
        top=top,
        bottom=(replace(bottom, pins=(*marked, *free)),),
    )


def test_34_cores_to_a_37_pin_end_fit_the_a3_body():
    """Acceptance 25: the pitch is the pin marking's, so 37 cells fit the page body.

    Probe: `_widest` in place.py also takes the core text widths (the pitch by core text again).
    """
    block = place_block(_facts(34, 37))
    assert block is not None
    assert block.width <= _A3_BODY[0]
    assert block.height <= _A3_BODY[1]
    assert block.pitch == block_pitch(text_width("37", height=_H))


def test_the_box_holds_the_core_text_turned_under_the_heading():
    """N1: the box is taller than the longest core text, and every text centres below the heading.

    Probe: `box_room` in place_frame.py returning the least height whatever the core text.
    """
    block = place_block(_facts(3, 3, core_text="3 A VERY LONG CORE TEXT"))
    assert block is not None
    box = block.boxes[0].box
    length = text_width("3 A VERY LONG CORE TEXT", height=_H)
    assert box.height >= length + 2 * 2
    for wire in block.wires:
        assert wire.text_y - length / 2 >= box.y + 2 * 2 + _H  # clear of the heading
        assert wire.text_y + length / 2 <= box.y + box.height  # inside the box
