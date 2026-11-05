"""Field case: a terminal strip feeding a relay bank draws with no reference on a strip terminal.
The bug: the old engine answered a conductor leaving a page with a reference marker, even on a strip terminal, where the terminal belongs.
Fixed by el-0008 (SW8, row P7.3), a terminal is drawn wherever a conductor ends (strict xfail until CORE-TEXTS)."""

import itertools
from typing import TYPE_CHECKING, Any

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.derive import function_item, item_tag_text, strip_of
from fransys_model.kernel import Severity
from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab import ports

if TYPE_CHECKING:
    from pathlib import Path

_RELAYS = 12
_TERMINALS = 4
_MEETING = 3
_DOTS = 16  # R1693: keep-outs whole cells, 18 before (R339: tables out of the footprint, pitch 96 moves two taps; was 16 before Ruling 89)

type _Point = tuple[int, int]
type _Segment = tuple[_Point, _Point]


def _leaves(point: _Point, segments: list[_Segment]) -> set[_Point]:
    """The unit directions in which rectilinear `segments` leave `point`."""
    x, y = point
    found: set[_Point] = set()
    for (x1, y1), (x2, y2) in segments:
        if x1 == x2 == x and y1 != y2 and min(y1, y2) <= y <= max(y1, y2):
            found |= {(0, d) for d in (1, -1) if (max(y1, y2) > y if d > 0 else min(y1, y2) < y)}
        if y1 == y2 == y and x1 != x2 and min(x1, x2) <= x <= max(x1, x2):
            found |= {(d, 0) for d in (1, -1) if (max(x1, x2) > x if d > 0 else min(x1, x2) < x)}
    return found


def meeting_points(result: fr.BuildResult) -> set[tuple[object, _Point]]:
    """Per page, the points where three or more drawn wire directions meet (not junctions.py).

    The wires carry no net here and no two buses of the case cross, so a page's wires are read as
    one net. A pin adds nothing the wire ends do not already show for this case.
    """
    segments: dict[object, list[_Segment]] = {}
    points: set[tuple[object, _Point]] = set()
    for page, drawing in drawn_pages(result.model).items():
        for wire in drawing.wires:
            segments.setdefault(page, []).extend(itertools.pairwise(wire.points))
            points |= {(page, end) for end in wire.points}
    return {(pg, p) for pg, p in points if len(_leaves(p, segments[pg])) >= _MEETING}


def strip_case_drafts(cover: Path) -> tuple[fr.Design, fr.Draft]:
    """The design and its schematic document: strip X1 feeding a chained bank of relays."""
    d = fr.design("demo_parts")
    room = d.location("C1", "Cabinet")
    feed = d.terminal_strip("X1", "DEMO-TB-2.5", _TERMINALS, place="C1")
    with d.function("R", "Relays"):
        bank = [d.device(f"K{i + 1}", "DEMO-RLY-2CO-24", place="C1") for i in range(_RELAYS)]
    ends: dict[int, Any] = {}  # a terminal point takes one conductor (R1266): each terminal's relays chain from coil pin to coil pin
    for i, relay in enumerate(bank):
        d.series(ends.get(i % _TERMINALS, feed[1 + i % _TERMINALS].inner), relay.coil["A1"], wire=("WH", 0.75))
        ends[i % _TERMINALS] = relay.coil["A1"]
    for a, b in itertools.pairwise(bank):
        d.series(a.coil["A2"], b.coil["A2"], wire=("BU", 0.75))
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover)


def strip_references(result: fr.BuildResult) -> int:
    """The reference markers that stand on a terminal of a strip (today's `layout.link_marker`)."""
    model = result.model
    table = ports(model)
    return sum(
        1 for marker in layout_of(model, LinkMarker).values() if strip_of(model, function_item(model, table[marker.port].function)) is not None
    )


def strip_tags_drawn(result: fr.BuildResult) -> bool:
    """True when the tag text of each strip is a drawn text (the row-group text, SW8)."""
    model = result.model
    texts = {one.text for drawing in drawn_pages(model).values() for one in drawing.texts}
    table = ports(model)
    strips = {strip for port in table.values() if (strip := strip_of(model, function_item(model, port.function))) is not None}
    return bool(strips) and all(item_tag_text(model, strip) in texts for strip in strips)


def test_a_strip_feeding_a_relay_bank_builds_on_the_core_path_with_no_failed_route(
    tmp_path: Path,
) -> None:
    result = fr.build(*strip_case_drafts(tmp_path / "cover.md"))
    codes = {f.code for f in result.findings}
    assert not codes & {"FUNCTION_NOT_DRAWN"}
    assert all(f.severity is not Severity.ERROR for f in result.findings)
    assert len(drawn_pages(result.model)) == 1
    # the strip's terminals and the relays
    symbols = [(page, s) for page, drawing in drawn_pages(result.model).items() for s in drawing.symbols]
    assert sum(1 for _, s in symbols if s.key not in ("junction-dot", "reference-marker")) == _TERMINALS + _RELAYS
    dots = {(page, (s.x, s.y)) for page, s in symbols if s.key == "junction-dot"}
    assert len(dots) == _DOTS
    assert dots == meeting_points(result)


def test_a_strip_feeding_a_relay_bank_draws_with_no_strip_reference(tmp_path: Path) -> None:
    result = fr.build(*strip_case_drafts(tmp_path / "cover.md"))
    assert strip_references(result) == 0
    assert strip_tags_drawn(result)
