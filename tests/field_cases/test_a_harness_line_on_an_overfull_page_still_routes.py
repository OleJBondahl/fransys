"""Field case: a harness line whose far end stands below the content box on an overfull page.

The engineering shape: a board unit offers six headers. Four harnesses share one drawing page:
a loom with a plug on the first header and plugs on two contactors' lead housings, a loom whose
plug on a second header runs to a four-pin sensor, a loom to a two-pin device, and a loom whose
plug on the last header runs to three two-pin headers.

The bug: the page grows taller than the content box and the sensor stands below it. The line to
the sensor was searched inside the content box, so its fan-out split had no path and the build
raised "no orthogonal path for harness line branch 1". One contactor, or any one loom left out,
kept the page inside the box and built.
The first fix (decision layout-0166): a line that no path in the content box can draw is searched
over the box grown to hold its ends, so the build succeeds. The page then reported
OUT_OF_CONTENT_BOX (not PAGE_OVERFULL: that check misses a fold-made overflow, layout-0166 D2).
The second fix (decision layout-0167): the unit group cuts at its outline's top edge, so
no page overflows and neither reports a finding. Longer lower columns (T-b) are held (R3: the
fallback is its own order). A group with no lower band (T-c) hands its shortest upper column
down to carry the outline (decision layout-0234); one whose upper band alone is taller than
the page stays held (T4). Held shapes overflow and keep the grown-box search.
"""

import re
import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_parts
from _drawn_extent import body_g
from _drawn_pages import drawn_pages

from fransys_model.kernel import merge
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnWire

_PART = """schema = 1

[part]
mpn = "{mpn}"
manufacturer = "Demo"
description = "{mpn}"
category = "connector"
class_code = "J"

[[function]]
name = "x"
kind = "connector"
symbol = "connector-fixed"
ports = [{ports}]

[function.connector]
style = "{style}"
pincount = {n}
gender = "{gender}"
"""
_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_SENSOR = """schema = 1

[part]
mpn = "FLD-SNR4"
manufacturer = "Demo"
description = "Sensor with four pins"
category = "generic"
class_code = "B"

[[function]]
name = "s"
kind = "sensor"
ports = [
    { name = "1", role = "generic" },
    { name = "2", role = "generic" },
    { name = "3", role = "generic" },
    { name = "4", role = "generic" },
]
"""
_SENSOR2 = (
    _SENSOR.replace("SNR4", "SNR2")
    .replace("four", "two")
    .replace(', { name = "3", role = "generic" }, { name = "4", role = "generic" }', "")
)
_CONTACTOR = """schema = 1

[part]
mpn = "FLD-CTR"
manufacturer = "Demo"
description = "Contactor with coil and auxiliary contact"
category = "electromechanical"
class_code = "Q"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "X1", role = "generic", symbol_port = "in" },
    { name = "X2", role = "generic", symbol_port = "out" },
]

[[function]]
name = "aux"
kind = "contact_no"
symbol = "make-contact"
ports = [
    { name = "T1", role = "generic", symbol_port = "in" },
    { name = "T2", role = "generic", symbol_port = "out" },
]
links = [{ a = "T1", b = "T2", kind = "switched" }]
"""
_HEADERS = ("FLD-HDR-14", "FLD-HDR-4", "FLD-HDR-2", "FLD-HDR-10", "FLD-HDR-6", "FLD-HDR-10")
WIRE = ("WH", 0.5)


def _part(mpn: str, n: int, gender: str) -> str:
    ports = ", ".join(
        f'{{ name = "{i}", role = "generic", symbol_port = "{"in" if i % 2 else "out"}" }}'
        for i in range(1, n + 1)
    )
    return _PART.format(mpn=mpn, ports=ports, style=f"{mpn.lower()}-{n}p", n=n, gender=gender)


def _library(root: Path) -> Path:
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    for n in (2, 4, 6, 10, 14):
        (root / "parts" / f"hdr-{n}.toml").write_text(_part(f"FLD-HDR-{n}", n, "male"))
    for n in (2, 4, 10, 14):
        (root / "parts" / f"plg-{n}.toml").write_text(_part(f"FLD-PLG-{n}", n, "female"))
    housing = _part("FLD-HSG-4M", 4, "male")
    (root / "parts" / "hsg.toml").write_text(
        housing.replace('gender = "male"', 'gender = "male"\nmates = ["FLD-PLG-4"]')
    )
    (root / "parts" / "ctr.toml").write_text(_CONTACTOR)
    (root / "parts" / "snr.toml").write_text(_SENSOR)
    (root / "parts" / "snr2.toml").write_text(_SENSOR2)
    return root


class _Board(NamedTuple):
    j1: fr.Device
    j2: fr.Device
    j3: fr.Device
    j4: fr.Device
    j5: fr.Device
    j6: fr.Device


@fr.unit("fld-board", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _board(u: Any) -> _Board:
    return _Board(*(u.device(f"J{i + 1}", h, interface=True) for i, h in enumerate(_HEADERS)))


class _Top(NamedTuple):
    pass


def _contactors(u: Any, board: _Board, count: int, deep: int) -> None:
    loom = u.harness("W1")
    plug = u.device("J1", "FLD-PLG-14", parent=loom, name="p1")
    u.mate(plug, board.j1)
    for i in range(count):
        q = u.device(f"Q{i + 1}", "FLD-CTR")
        housing = u.device(
            "J1",
            "FLD-HSG-4M",
            parent=q,
            name=f"h{i}",
            joins={"1": q.coil["X1"], "2": q.coil["X2"], "3": q.aux["T1"], "4": q.aux["T2"]},
        )
        lead = u.device(f"J{i + 2}", "FLD-PLG-4", parent=loom, name=f"lp{i}")
        u.mate(lead, housing)
        for pin in range(1, 5):
            if i == 0 and pin == 1 and deep:
                end = _tail(u, plug["1"], deep, "G")
                u.detail.wire(end, lead["1"], wire=WIRE)
            else:
                u.detail.wire(plug[str(4 * i + pin)], lead[str(pin)], wire=WIRE)


def _looms(u: Any, board: _Board, chain: int) -> None:
    sensor_loom = u.harness("S1")
    sensor_plug = u.device("J1", "FLD-PLG-4", parent=sensor_loom, name="sp")
    u.mate(sensor_plug, board.j2)
    sensor = u.device("B1", "FLD-SNR4", parent=sensor_loom)
    for pin in "1234":
        u.detail.wire(sensor_plug[pin], sensor[pin], wire=WIRE)
    pair_loom = u.harness("M1")
    pair_plug = u.device("J1", "FLD-PLG-2", parent=pair_loom, name="mp")
    u.mate(pair_plug, u.device("E1", "FLD-HDR-2"))
    pair = u.device("B2", "FLD-SNR2", parent=pair_loom)
    for pin in "12":
        u.detail.wire(pair[pin], pair_plug[pin], wire=WIRE)
    strip_loom = u.harness("T1")
    strip_plug = u.device("J1", "FLD-PLG-10", parent=strip_loom, name="tp")
    u.mate(strip_plug, board.j6)
    for k, name in enumerate("ABC"):
        far = u.device(f"X{name}", "FLD-HDR-2")
        u.detail.wire(strip_plug[str(2 * k + 1)], far["1"], wire=WIRE)
        u.detail.wire(strip_plug[str(2 * k + 2)], far["2"], wire=WIRE)
        if name == "A":
            _tail(u, far["2"], chain)


def _tail(u: Any, start: Any, count: int, tag: str = "K") -> Any:
    """`count` contactor coils in series after `start`: one tall column; the last coil's X2."""
    for i in range(count):
        coil = u.device(f"{tag}{i + 1}", "FLD-CTR").coil
        u.detail.wire(start, coil["X1"], wire=WIRE)
        start = coil["X2"]
    return start


def _top_with(contactors: int, chain: int, deep: int, *, looms: bool) -> Any:
    @fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def top(u: Any) -> _Top:
        unused = ("j3", "j4", "j5") if looms else ("j2", "j3", "j4", "j5", "j6")
        board = u.add(_board, "A1", unused=unused)
        _contactors(u, board, contactors, deep)
        if looms:
            _looms(u, board, chain)
        return _Top()

    return top


@cache
def _built(contactors: int, chain: int = 0, deep: int = 0, *, looms: bool = True) -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(_top_with(contactors, chain, deep, looms=looms), "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    return fr.build(d, doc)


def _errors(built: fr.BuildResult) -> list[str]:
    return [f.code for f in built.findings if f.severity.name == "ERROR"]


def test_one_contactor_builds() -> None:
    assert _errors(_built(1)) == []


def test_two_contactors_build_and_the_four_looms_each_draw_a_line() -> None:
    built = _built(2)
    assert _errors(built) == []
    harnesses = {w.label.text for _, d in _pages(built) for w in _lines(d) if w.label}
    assert len(harnesses) == 4


def test_the_cut_group_leaves_no_page_overfull() -> None:
    codes = {f.code for f in _built(2).findings}
    assert not codes & {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"}


def _pages(built: fr.BuildResult) -> list[tuple[int, Drawing]]:
    """Each drawn page with its page number, in page order."""
    numbers = {page.id: page.number for page in layout_of(built.model, Page).values()}
    pairs = ((numbers[pid], d) for pid, d in drawn_pages(built.model).items())
    return sorted(pairs, key=lambda p: p[0])


def _lines(drawing: Drawing) -> list[DrawnWire]:
    """The harness lines of a page: the wires drawn as a bundle (lanes above one)."""
    return [w for w in drawing.wires if w.lanes > 1]


def _w1(wire: DrawnWire) -> bool:
    return wire.label is not None and "W1" in wire.label.text


def _of_symbol(built: fr.BuildResult, designation: str) -> list[tuple[int, Drawing, DrawnSymbol]]:
    """Each page and symbol of `designation`: the symbol that stands nearest to its tag text."""
    found = []
    for number, d in _pages(built):
        for text in d.texts:
            if text.kind == "TAG" and text.text.endswith(f"-{designation}"):
                near = min(
                    (s for s in d.symbols if s.key != "junction-dot"),
                    key=lambda s: abs(s.x - text.box.x) + abs(s.y - text.box.y),
                )
                found.append((number, d, near))
    return found


def _page_of_symbol(built: fr.BuildResult, designation: str) -> int:
    """The page of the one placed symbol whose tag names `designation`."""
    found = {number for number, _, _ in _of_symbol(built, designation)}
    assert len(found) == 1, (designation, found)
    return found.pop()


def _rect(outline) -> tuple[int, int, int, int]:
    xs, ys = [p[0] for p in outline.points], [p[1] for p in outline.points]
    return (min(xs), min(ys), max(xs), max(ys))


def _outline(built: fr.BuildResult) -> tuple[int, Drawing]:
    """The page number and Drawing of the one page that draws an outline."""
    ((number, d),) = [(n, d) for n, d in _pages(built) if d.outlines]
    return number, d


def _outline_page(built: fr.BuildResult) -> int:
    return _outline(built)[0]


def _w1_line_pages(built: fr.BuildResult) -> set[int]:
    return {number for number, d in _pages(built) for w in _lines(d) if _w1(w)}


def _stubs(drawing: Drawing) -> list[DrawnSymbol]:
    """The reference markers on `drawing` that stand for the cable `-W1`."""
    return [
        s
        for s in drawing.symbols
        if s.key == "reference-marker" and any("W1" in v for _, v in s.slots)
    ]


def _w1_stub_pages(built: fr.BuildResult) -> list[int]:
    return [number for number, d in _pages(built) for _ in _stubs(d)]


def test_t_a_the_contactors_stand_on_one_page_and_the_board_with_its_lower_ends_on_the_next() -> (
    None
):
    built = _built(2)
    codes = {f.code for f in built.findings}
    assert "OUT_OF_CONTENT_BOX" not in codes
    assert "PAGE_OVERFULL" not in codes
    first = _page_of_symbol(built, "Q1")
    assert _page_of_symbol(built, "Q2") == first
    assert _outline_page(built) == first + 1
    assert _page_of_symbol(built, "B1") == first + 1
    assert _w1_line_pages(built) == {first, first + 1}
    assert sorted(_w1_stub_pages(built)) == [first, first + 1]


_HELD = "TALL-PAGE T4 held (R3)"


def test_t_b_lower_ends_that_pass_the_bottom_stand_beside_the_outline() -> None:
    built = _built(2, 3)
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in built.findings}
    number, page = _outline(built)
    (outline,) = page.outlines
    tail = _of_symbol(built, "K1")
    assert tail
    assert {n for n, _, _ in tail} == {number}
    assert all(s.x >= _rect(outline)[2] for _, _, s in tail)


def test_t_c_a_page_that_still_overflows_reports_page_overfull_and_builds() -> None:
    built = _built(2, 0, 6, looms=False)
    assert _errors(built) == []
    assert "PAGE_OVERFULL" in {f.code for f in built.findings}


def test_t_c_a_line_end_below_the_box_of_a_page_no_cut_helps_still_routes() -> None:
    """layout-0166's extent, moved here by layout-0167: an upper band taller than a page.

    The outline leaves for the next page (layout-0234), but the column of six coils or more
    stays past the bottom with its tables and the plug box's line ink, and the line is searched
    over the box grown to hold its ends, so the build still succeeds.
    """
    built = _built(2, 0, 8, looms=False)
    assert _errors(built) == []
    assert {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"} <= {f.code for f in built.findings}
    out = [f.message for f in built.findings if f.code == "OUT_OF_CONTENT_BOX"]
    assert any("harness line's ink" in m for m in out), out
    assert all(re.search(r" at \d+[A-Z] \((\+\w+)?p\d+(\.\d+)?\b", m, re.MULTILINE) for m in out), (
        out
    )


def _crossings(page: Drawing) -> list[tuple[str, str]]:
    """Harness-line segments of `page` that enter the inside of a box of `page`."""
    boxes = [(s.id, body_g(s)) for s in page.symbols if s.key == "generic-box"]
    found = []
    for line in _lines(page):
        for (ax, ay), (bx, by) in zip(line.points, line.points[1:], strict=False):
            x0, x1, y0, y1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
            found += [
                (line.id, key)
                for key, (bx0, by0, bx1, by1) in boxes
                if x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0
            ]
    return found


def test_t_a_no_line_of_the_outline_page_crosses_a_box_and_its_lower_band_keeps_the_fold_s_x() -> (
    None
):
    """R2: the frame stands as the uncut fold has it from the lower columns (no trunk on a box)."""
    page = _outline(_built(2))[1]
    assert _lines(page), "the outline page draws harness lines"
    assert _crossings(page) == []


def test_t_a_the_cut_line_ends_in_a_stub_south_of_its_bar_and_no_line_crosses_a_box() -> None:
    """R1: on the upper band's page W1's trunk leaves the bar south and ends in its stub.

    UNDO: `line_pieces` gets no `trunk`: the stub stands at the root end's tip, facing north;
    `_branches` keeps the bar one polyline and the rule has no line to carry its label.
    """
    built = _built(2)
    ((_, page, _),) = {id(d): (n, d, s) for n, d, s in _of_symbol(built, "Q1")}.values()
    (stub,) = _stubs(page)
    lines = [w for w in _lines(page) if _w1(w)]
    bar_y = min(y for w in lines for _, y in w.points)
    assert len(lines) == 3  # each end its own branch
    assert stub.orient == "R270"  # the marker hangs south of the wire that arrives from the north
    assert stub.y > bar_y
    assert _crossings(page) == []


Pt = tuple[int, int]
Segment = tuple[str, Pt, Pt]


def _segments(page: Drawing) -> list[Segment]:
    """Each harness segment of `page` as (harness, first point, second point), a run at a time."""
    return [
        (w.label.text if w.label else w.id, a, b)
        for w in _lines(page)
        for a, b in zip(w.points, w.points[1:], strict=False)
    ]


def _along_or_tee(one: Segment, other: Segment) -> bool:
    """Whether segment `one` runs along `other`, or ends strictly inside it (a T)."""
    (_, (ax, ay), (bx, by)), (_, (cx, cy), (dx, dy)) = one, other
    horizontal = ay == by == cy == dy
    vertical = ax == bx == cx == dx
    if horizontal and min(max(ax, bx), max(cx, dx)) > max(min(ax, bx), min(cx, dx)):
        return True
    if vertical and min(max(ay, by), max(cy, dy)) > max(min(ay, by), min(cy, dy)):
        return True
    return any(
        (cx == dx and px == cx and min(cy, dy) < py < max(cy, dy))
        or (cy == dy and py == cy and min(cx, dx) < px < max(cx, dx))
        for px, py in ((ax, ay), (bx, by))
    )


def test_t_a_two_harness_lines_never_run_along_each_other_or_meet_in_a_t() -> None:
    """R7: lines may cross; on the outline's page -S1 and -T1 neither share a row nor tee.

    UNDO: `draw_lines` hands each line an empty `busy`, and -S1 runs on -T1's row.
    """
    found = _segments(_outline(_built(2))[1])
    assert found, "the outline page draws harness lines"
    bad = [
        (one[0], other[0])
        for n, one in enumerate(found)
        for other in found[n + 1 :]
        if one[0] != other[0] and (_along_or_tee(one, other) or _along_or_tee(other, one))
    ]
    assert bad == []
