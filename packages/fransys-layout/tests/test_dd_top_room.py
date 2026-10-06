"""S16, S20 M1: the room above the first row holds a first-row reference, with no lane at all.

`place`'s C14 lift is raised by S16's Room call to hold each first-row reference one line high at
its own `out`; a terminal's star reference on the first row stands one C15 push (`2 *
text_height`, 16 G) out along its stub. M1 makes the box of a reference at an N port a vertical
one. The first row therefore stands low enough that the box is inside the content box
(`OUT_OF_CONTENT_BOX`), without `TOP_HEADROOM_LANES`. (The D2 stagger and its tiers are gone, S20
M5: a marker has one place, straight out along its wire.)

The real layout gives the first row's port y and the reference. The model is two terminals of one
strip, each a star reference.
"""

from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document
from samples import SHEET

from fransys_layout.engines.schematic import engine, run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import OUT_OF_CONTENT_BOX
from fransys_layout.stages import Layout, LinkMarker

if TYPE_CHECKING:
    import pytest

_PROJECT: dict[str, Any] = {
    "title": "Top room",
    "number": "P-1010",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _first_row_reference() -> LinkMarker:
    """The real star reference of a first-row terminal on page 1, its C15 push applied.

    Strip `X1` has two terminals of group `G1`. Each is chained to a lamp of `G1` (the lamp stands
    below it in one column, so the wire between them is drawn on page 1) and wired to a second
    lamp of `G1` that stands apart: each terminal is the reference of a star, and its inner port
    carries a wire drawn on the page, so the marker leaves by the free outer N port (C22,
    layout-0053 amended: a wire drawn on another page does not count).
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    group = d.group("G1", "G1")
    wire = d.wiring(colour="BU", gauge="0.5")
    strip = d.strip("X1", at=cabinet)
    for k in range(2):
        terminal = strip.terminal("DEMO-TB-2.5", group=group)
        for n in range(2):
            lamp = d.item("DEMO-LAMP-24", tag=f"L{k}{n}", at=cabinet, group=group)
            wire(terminal.inner, lamp.fn("lamp")["1"])
            if n == 0:
                d.chain(terminal, lamp)
    model = fr.build(parts, d.draft(), system_document()).model
    layout, _, _ = run_stages(model, read_inputs(model))
    refs = [m for m in layout.markers if m.page == 1 and m.star == "ref"]
    assert refs, "premise: a first-row terminal carries a star reference"
    return min(refs, key=lambda m: m.at.y)


def _outside(marker: LinkMarker) -> set:
    """The ports whose marker box `lint_geometry` reports as `OUT_OF_CONTENT_BOX`."""
    layout = Layout(
        pages=(), placed=(), routes=(), decisions=(), markers=(marker,), labels=(), outlines=()
    )
    return {
        subject
        for finding in lint_geometry(layout, sheet=SHEET)
        if finding.code == OUT_OF_CONTENT_BOX
        for subject in finding.subjects
    }


def test_the_top_room_holds_a_first_row_reference_with_no_headroom_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S16 + M1: with no lane the first-row reference is a vertical box above its port, one C15
    push out, and stands inside the content box (top y >= 0)."""
    # UNDO: stages/place.py `_text_room`, first rows: drop `boxes += _owned(...)` (Room no longer
    #     holds the reference: with no lane the first row stands at the band alone, and the box
    #     top is y = -10, above the content box)
    monkeypatch.setattr(engine, "TOP_HEADROOM_LANES", 0)
    reference = _first_row_reference()
    assert reference.stub_extra == 16  # premise: the reference stands one C15 push out
    assert reference.box.width < reference.box.height  # M1: a vertical box at an N port
    assert reference.box.y + reference.box.height <= reference.at.y  # above its port
    assert reference.box.y >= 0
    assert _outside(reference) == set()
