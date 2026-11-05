"""Field case (R1396, R1397, R1571): a terminal in several drawing sets draws one line per other placement under each tag; the checker joins on it."""

import itertools
import re
from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import cabinet_document, unit_document
from fransys_el.drawn_where import where_text

from electrical_symbols import LIBRARY
from fransys_layout.drawing import port_points
from fransys_model.derive import function_placements
from fransys_model.derive.order import placement_key
from fransys_model.kernel import Id
from fransys_model.layout import Page


class _Io(NamedTuple):
    feed: fr.TerminalStrip


@fr.unit("demo-where", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _unit(u: fr.Design) -> _Io:
    feed = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2, interface=True)
    with u.function("R", "Relay"):
        coil = u.device("K1", "DEMO-RLY-2CO-24").coil
        u.series(feed[1].inner, coil["A1"], wire=("WH", 0.75))
        u.series(feed[2].inner, coil["A2"], wire=("BU", 0.75))
    return _Io(feed)


def _build(*, extra: int = 0) -> fr.BuildResult:
    """The unit and cabinet `EXT`, and `extra` more locations cabled to the feed (the second on its inner side: a point takes two per side)."""
    d = fr.design("demo_parts")
    unit = d.add(_unit, "U1")
    field = d.location("EXT", "External")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2, place="EXT")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, x0[1], unit.feed[1])
    cable.core(2, x0[2], unit.feed[2])
    docs = [unit_document(unit), cabinet_document(field)]
    for i in range(extra):
        second = d.location(f"EX{i + 2}", "Another")
        strip = d.terminal_strip(f"X{9 - i}", "DEMO-TB-2.5", 2, place=f"EX{i + 2}")
        other = d.cable(f"W{i + 2}", "DEMO-CBL-4G1.5", length_m=1)
        ends = (unit.feed[1], unit.feed[2]) if i == 0 else (unit.feed[1].inner, unit.feed[2].inner)
        other.core(1, strip[1], ends[0])
        other.core(2, strip[2], ends[1])
        docs.append(cabinet_document(second))
    return fr.build(d, *docs)


_built = cache(_build)
_built3 = cache(lambda: _build(extra=1))
_built4 = cache(lambda: _build(extra=2))


def _not_drawn(result: fr.BuildResult) -> list[Any]:
    return [f for f in result.findings if f.code == "CONNECTION_NOT_DRAWN"]


def test_no_connection_is_left_undrawn() -> None:
    assert not _not_drawn(_built())


def _origin(svg: str, text: str) -> tuple[float, float]:
    """The (x, y) of the `<text>` element that prints `text` in a page SVG."""
    found = re.search(rf'<text x="([\d.]+)" y="([\d.]+)"[^>]*>{re.escape(text)}<', svg)
    assert found is not None
    return float(found.group(1)), float(found.group(2))


def _groups(result: fr.BuildResult, page: Any) -> list[tuple[str, ...]]:
    """The WHERE lines of `page` per tag, each group top to bottom."""
    by_owner: dict[Any, list[Any]] = {}
    for t in sorted((t for t in result.drawings[page].texts if t.kind == "WHERE"), key=lambda t: t.box.y):
        by_owner.setdefault(t.owner, []).append(t)
    return [tuple(t.text for t in group) for group in by_owner.values()]


def _named(result: fr.BuildResult) -> tuple[int, int]:
    """(placements checked, most lines under one tag): each placement's tag carries one line per other placement, in `function_placements` order."""
    checked, most = 0, 0
    for rows in (r for r in function_placements(result.model).values() if len(r) > 1):
        assert all(placement_key(result.model, *a) < placement_key(result.model, *b) for a, b in itertools.pairwise(rows))
        for here in rows:
            want = tuple(where_text(result.model, here, there) for there in rows if there[0] != here[0])
            assert want in _groups(result, here[0])
            checked, most = checked + 1, max(most, len(want))
    return checked, most


def test_each_placement_of_a_terminal_names_the_other() -> None:
    checked, most = _named(_built())
    assert (checked, most) == (4, 1)


def test_each_placement_of_a_terminal_in_three_sets_names_both_others() -> None:
    checked, most = _named(_built3())
    assert (checked, most) == (6, 2)


def test_where_lines_stand_in_their_boxes_in_the_compiled_page_without_overlap() -> None:
    """The ink of each WHERE line (its <text> origin and baseline in the page SVG) lies in its box, and no two boxes overlap."""
    result = _built3()
    for page, svg in result.page_svgs.items():
        texts = [t for t in result.drawings[Id[Page](kind="layout.page", value=page.split(":")[1])].texts if t.kind == "WHERE"]
        scale = None
        for t in texts:
            x, y = _origin(svg, t.text)
            scale = scale or x / t.box.x
            assert t.box.x * scale - 0.01 <= x <= (t.box.x + t.box.w) * scale
            assert t.box.y * scale <= y <= (t.box.y + t.box.h) * scale + 0.01
        boxes = [t.box for t in texts]
        for i, a in enumerate(boxes):
            assert not any(a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h for b in boxes[i + 1 :])


def _terminals(result: fr.BuildResult) -> Any:
    """Each drawn terminal symbol that prints where lines, with its page's drawing, its WHERE texts and its tag text."""
    for drawing in result.drawings.values():
        for symbol in (s for s in drawing.symbols if s.key == "terminal"):
            where = sorted((t for t in drawing.texts if t.owner == symbol.id and t.kind == "WHERE"), key=lambda t: t.box.y)
            tag = next((t for t in drawing.texts if t.owner == symbol.id and t.kind == "TAG"), None)
            if where:
                yield drawing, symbol, where, tag


def _overlaps(a: Any, b: Any) -> bool:
    return bool(a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h)


def test_a_terminal_in_four_sets_stands_under_its_tag_and_its_where_lines_without_overlap() -> None:
    """KI-610: each placement of a terminal in four sets prints three where lines under its tag, clear of the body and its leads."""
    seen = 0
    for _, symbol, where, tag in _terminals(_built4()):
        seen += 1
        assert len(where) == 3
        assert tag is not None
        assert tag.box.y + tag.box.h <= where[0].box.y
        assert not any(_overlaps(t.box, symbol.outline) for t in where)
    assert seen == 8


def test_a_terminal_in_four_sets_keeps_every_wire_end_on_a_port() -> None:
    """KI-610: a wire that ends at a terminal ends on one of its ports, as the symbol is drawn."""
    for drawing, symbol, _, _ in _terminals(_built4()):
        ports = {at for at, _ in port_points(symbol, LIBRARY)}
        near = symbol.outline
        ends = [
            e
            for w in drawing.wires
            for e in (w.points[0], w.points[-1])
            if near.x - 1 <= e[0] <= near.x + near.w + 1 and near.y - 1 <= e[1] <= near.y + near.h + 1
        ]
        assert ends, symbol
        assert all(end in ports for end in ends), (ends, ports)
