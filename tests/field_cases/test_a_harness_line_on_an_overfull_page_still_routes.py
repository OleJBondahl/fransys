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
The second fix (decision layout-0167, TALL-PAGE): the unit group cuts at its outline's top edge, so
no page overflows and neither reports a finding. Longer lower columns (T-b) are held (designer
R3: the fallback is its own order); a group with no lower band (T-c) is held too (R4). Both
overflow and keep the grown-box search.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts
import pytest

from fransys_model.kernel import merge
from fransys_model.layout import (
    ConnectorBox,
    HarnessLine,
    LinkMarker,
    Outline,
    Page,
    Side,
    SymbolPlacement,
    layout_of,
)

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
                u.wire(end, lead["1"], wire=WIRE)
            else:
                u.wire(plug[str(4 * i + pin)], lead[str(pin)], wire=WIRE)


def _looms(u: Any, board: _Board, chain: int) -> None:
    sensor_loom = u.harness("S1")
    sensor_plug = u.device("J1", "FLD-PLG-4", parent=sensor_loom, name="sp")
    u.mate(sensor_plug, board.j2)
    sensor = u.device("B1", "FLD-SNR4", parent=sensor_loom)
    for pin in "1234":
        u.wire(sensor_plug[pin], sensor[pin], wire=WIRE)
    pair_loom = u.harness("M1")
    pair_plug = u.device("J1", "FLD-PLG-2", parent=pair_loom, name="mp")
    u.mate(pair_plug, u.device("E1", "FLD-HDR-2"))
    pair = u.device("B2", "FLD-SNR2", parent=pair_loom)
    for pin in "12":
        u.wire(pair[pin], pair_plug[pin], wire=WIRE)
    strip_loom = u.harness("T1")
    strip_plug = u.device("J1", "FLD-PLG-10", parent=strip_loom, name="tp")
    u.mate(strip_plug, board.j6)
    for k, name in enumerate("ABC"):
        far = u.device(f"X{name}", "FLD-HDR-2")
        u.wire(strip_plug[str(2 * k + 1)], far["1"], wire=WIRE)
        u.wire(strip_plug[str(2 * k + 2)], far["2"], wire=WIRE)
        if name == "A":
            _tail(u, far["2"], chain)


def _tail(u: Any, start: Any, count: int, tag: str = "K") -> Any:
    """`count` contactor coils in series after `start`: one tall column; the last coil's X2."""
    for i in range(count):
        coil = u.device(f"{tag}{i + 1}", "FLD-CTR").coil
        u.wire(start, coil["X1"], wire=WIRE)
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
    assert len({line.harness for line in layout_of(built.model, HarnessLine).values()}) == 4


def test_the_cut_group_leaves_no_page_overfull() -> None:
    codes = {f.code for f in _built(2).findings}
    assert not codes & {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"}


def _numbers(built: fr.BuildResult) -> dict[Any, int]:
    return {page.id: page.number for page in layout_of(built.model, Page).values()}


def _page_of_symbol(built: fr.BuildResult, designation: str) -> int:
    """The page of the one placed symbol whose key names `designation`."""
    numbers = _numbers(built)
    found = {
        numbers[one.page]
        for one in layout_of(built.model, SymbolPlacement).values()
        if designation in one.key
    }
    assert len(found) == 1, (designation, found)
    return found.pop()


def _outline_page(built: fr.BuildResult) -> int:
    (outline,) = layout_of(built.model, Outline).values()
    return _numbers(built)[outline.page]


def _w1_line_pages(built: fr.BuildResult) -> set[int]:
    numbers = _numbers(built)
    return {
        numbers[one.page] for one in layout_of(built.model, HarnessLine).values() if "W1" in one.key
    }


def _w1_stub_pages(built: fr.BuildResult) -> list[int]:
    numbers = _numbers(built)
    return [
        numbers[one.page]
        for one in layout_of(built.model, LinkMarker).values()
        if "line_stub" in one.key and "W1" in one.key
    ]


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


_HELD = "TALL-PAGE T4 held (designer R3)"


@pytest.mark.xfail(strict=True, reason=_HELD)
def test_t_b_lower_ends_that_pass_the_bottom_stand_beside_the_outline() -> None:
    built = _built(2, 3)
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in built.findings}
    (outline,) = layout_of(built.model, Outline).values()
    tail = [one for one in layout_of(built.model, SymbolPlacement).values() if "K1" in one.key]
    assert {one.page for one in tail} == {outline.page}
    assert all(one.x >= outline.x + outline.width for one in tail)


def test_t_c_a_page_that_still_overflows_reports_page_overfull_and_builds() -> None:
    built = _built(2, 0, 2, looms=False)
    assert _errors(built) == []
    assert "PAGE_OVERFULL" in {f.code for f in built.findings}


def test_t_c_a_line_end_below_the_box_of_a_page_no_cut_helps_still_routes() -> None:
    """layout-0166's extent, moved here by layout-0167: a group with no lower band is not cut.

    Its upper band is so tall that the outline and the plug box stand below the content box,
    and the line is searched over the box grown to hold its ends, so the build still succeeds.
    """
    built = _built(2, 0, 6, looms=False)
    assert _errors(built) == []
    assert {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"} <= {f.code for f in built.findings}


def _crossings(built: fr.BuildResult, page: Any) -> list[tuple[Any, Any]]:
    """Harness-line segments of `page` that enter the inside of a connector box of `page`."""
    boxes = [b for b in layout_of(built.model, ConnectorBox).values() if b.page == page]
    found = []
    for line in (h for h in layout_of(built.model, HarnessLine).values() if h.page == page):
        for a, b in zip(line.points, line.points[1:], strict=False):
            x0, x1, y0, y1 = min(a.x, b.x), max(a.x, b.x), min(a.y, b.y), max(a.y, b.y)
            found += [
                (line.key, box.key)
                for box in boxes
                if x0 < box.x + box.width and x1 > box.x and y0 < box.y + box.height and y1 > box.y
            ]
    return found


def test_t_a_no_line_of_the_outline_page_crosses_a_box_and_its_lower_band_keeps_the_fold_s_x() -> (
    None
):
    """R2: the frame stands as the uncut fold has it from the lower columns (no trunk on a box)."""
    built = _built(2)
    (outline,) = layout_of(built.model, Outline).values()
    assert _crossings(built, outline.page) == []


def test_t_a_the_cut_line_ends_in_a_stub_south_of_its_bar_and_no_line_crosses_a_box() -> None:
    """R1: on the upper band's page W1's trunk leaves the bar south and ends in its stub.

    UNDO: `line_pieces` gets no `trunk`: the stub stands at the root end's tip, facing north;
    `_branches` keeps the bar one polyline and W1.3 has no line to carry its label.
    """
    built = _built(2)
    (page,) = {
        one.page for one in layout_of(built.model, SymbolPlacement).values() if "Q1" in one.key
    }
    (stub,) = (
        one
        for one in layout_of(built.model, LinkMarker).values()
        if "line_stub" in one.key and "W1" in one.key and one.page == page
    )
    lines = [h for h in layout_of(built.model, HarnessLine).values() if h.page == page]
    bar_y = min(point.y for h in lines if "W1" in h.key for point in h.points)
    assert {h.branch for h in lines if "W1" in h.key} == {1, 2, 3}  # each end its own branch
    assert stub.facing is Side.S
    assert stub.y > bar_y
    assert _crossings(built, page) == []


def _segments(built: fr.BuildResult, page: Any) -> list[tuple[Any, Any, Any]]:
    """Each harness segment of `page` as (harness, first point, second point), a run at a time."""
    return [
        (line.harness, a, b)
        for line in layout_of(built.model, HarnessLine).values()
        if line.page == page
        for a, b in zip(line.points, line.points[1:], strict=False)
    ]


def _along_or_tee(one: Any, other: Any) -> bool:
    """Whether segment `one` runs along `other`, or ends strictly inside it (a T)."""
    (_, a, b), (_, c, d) = one, other
    horizontal = a.y == b.y == c.y == d.y
    vertical = a.x == b.x == c.x == d.x
    if horizontal and min(max(a.x, b.x), max(c.x, d.x)) > max(min(a.x, b.x), min(c.x, d.x)):
        return True
    if vertical and min(max(a.y, b.y), max(c.y, d.y)) > max(min(a.y, b.y), min(c.y, d.y)):
        return True
    return any(
        (c.x == d.x and p.x == c.x and min(c.y, d.y) < p.y < max(c.y, d.y))
        or (c.y == d.y and p.y == c.y and min(c.x, d.x) < p.x < max(c.x, d.x))
        for p in (a, b)
    )


def test_t_a_two_harness_lines_never_run_along_each_other_or_meet_in_a_t() -> None:
    """R7: lines may cross; on the outline's page -S1 and -T1 neither share a row nor tee.

    UNDO: `draw_lines` hands each line an empty `busy`, and -S1 runs on -T1's row.
    """
    built = _built(2)
    (outline,) = layout_of(built.model, Outline).values()
    found = _segments(built, outline.page)
    bad = [
        (one[0], other[0])
        for n, one in enumerate(found)
        for other in found[n + 1 :]
        if one[0] != other[0] and (_along_or_tee(one, other) or _along_or_tee(other, one))
    ]
    assert bad == []
