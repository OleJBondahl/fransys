"""Field case: a split unit group whose second page holds only no-line pin replicas.

The engineering shape: a board unit has one header with a harness line (a plug on it) and three
headers with none, wired straight to outside headers. The wide one's ten wires make its column so
tall that the page splits and that column stands alone on page 2.

The bug: the group's outline part on page 2 (layout-0153: one outline part per page) draws
only the interfaces its columns reach, and the line interface reaches page 1 only. `_shape` took
its lead from the first line box and raised IndexError on page 2, so the build crashed.
The fix (decision layout-0164): the part's lead is the first no-line interface that has a replica
on the page, so the outline part draws there holding the replicas.

Per decision layout-0165, on that replica-only page the J4 replicas and the far device's
pins ran 1, 10, 2 ... (string order), and two wires ran inside the outline. The three tests at the
end of the module hold both.

layout-0167: contact tables now count in a group's height, so the original input, a contactor
on a lead housing at the line's far end, is cut and builds with no replica-only page. Its test is
`test_the_original_input_with_a_contactor_is_cut_and_builds`. The replica-only page is still held
by the same input with the contactor swapped for a plain 4-pin header end; the other tests use it.
A landed field case's input never changes silently: the premise moved to a second input.
layout-0175: the content was grown (J2 and J4 to ten and fourteen pins) so the group splits again.
"""

import tempfile
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages

from fransys_model.kernel import merge

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnOutline

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


def _part(mpn: str, n: int, gender: str) -> str:
    ports = ", ".join(
        f'{{ name = "{i}", role = "generic", symbol_port = "{"in" if i % 2 else "out"}" }}'
        for i in range(1, n + 1)
    )
    return _PART.format(mpn=mpn, ports=ports, style=f"{mpn.lower()}-{n}p", n=n, gender=gender)


def _library(root: Path) -> Path:
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    for n in (2, 4, 10, 14):
        (root / "parts" / f"hdr-{n}.toml").write_text(_part(f"FLD-HDR-{n}", n, "male"))
    for n in (4, 14):
        (root / "parts" / f"plg-{n}.toml").write_text(_part(f"FLD-PLG-{n}", n, "female"))
    (root / "parts" / "hsg.toml").write_text(
        _part("FLD-HSG-4M", 4, "male").replace(
            'gender = "male"', 'gender = "male"\nmates = ["FLD-PLG-4"]'
        )
    )
    (root / "parts" / "ctr.toml").write_text(
        """schema = 1

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
    )
    return root


class _Board(NamedTuple):
    a: fr.Device
    b: fr.Device
    c: fr.Device
    d: fr.Device


@fr.unit("fld-board", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _board(u: Any) -> _Board:
    return _Board(
        a=u.device("J1", "FLD-HDR-14", interface=True),
        b=u.device("J2", "FLD-HDR-10", interface=True),
        c=u.device("J3", "FLD-HDR-2", interface=True),
        d=u.device("J4", "FLD-HDR-14", interface=True),
    )


class _Top(NamedTuple):
    pass


@fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _top(u: Any) -> _Top:
    b = u.add(_board, "B1")
    w = u.harness("W1")
    p = u.device("J1", "FLD-PLG-14", parent=w, name="p1")
    u.mate(p, b.a)
    end = u.device("E1", "FLD-HDR-4")
    lp = u.device("J2", "FLD-PLG-4", parent=w, name="p2")
    u.mate(lp, end)
    _wire_the_board(u, b, p, lp)
    return _Top()


def _wire_the_board(u: Any, b: Any, p: Any, lp: Any) -> None:
    for pin in range(1, 5):
        u.detail.wire(p[str(pin)], lp[str(pin)], wire=("WH", 0.5))
    for tag, part, board_pin, count in (
        ("Y1", "FLD-HDR-10", b.b, 10),
        ("Z1", "FLD-HDR-10", b.c, 2),
        ("Z2", "FLD-HDR-14", b.d, 14),
    ):
        far = u.device(tag, part)
        for pin in range(1, count + 1):
            u.detail.wire(board_pin[str(pin)], far[str(pin)], wire=("WH", 0.5))


@fr.unit("fld-top-ctr", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _top_ctr(u: Any) -> _Top:
    b = u.add(_board, "B1")
    w = u.harness("W1")
    p = u.device("J1", "FLD-PLG-14", parent=w, name="p1")
    u.mate(p, b.a)
    q = u.device("Q1", "FLD-CTR")
    housing = u.device(
        "J1",
        "FLD-HSG-4M",
        parent=q,
        name="h1",
        joins={"1": q.coil["X1"], "2": q.coil["X2"], "3": q.aux["T1"], "4": q.aux["T2"]},
    )
    lp = u.device("J2", "FLD-PLG-4", parent=w, name="p2")
    u.mate(lp, housing)
    _wire_the_board(u, b, p, lp)
    return _Top()


def _build(top: Any, name: str) -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(top, "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), name, cover=root / "cover.md")
    return fr.build(d, doc)


@cache
def _built() -> fr.BuildResult:
    return _build(_top, "fld-top")


@cache
def _built_ctr() -> fr.BuildResult:
    return _build(_top_ctr, "fld-top-ctr")


def _plug_pages(model: Any) -> set[Any]:
    """The pages that draw a harness line (a trunk wire): the pages that hold the plug."""
    return {
        page
        for page, drawing in drawn_pages(model).items()
        if any(wire.style == "trunk" for wire in drawing.wires)
    }


def _outlines(model: Any) -> list[tuple[Any, DrawnOutline]]:
    """Every drawn outline with its page; the board is the one unit that draws any."""
    return [(page, one) for page, drawing in drawn_pages(model).items() for one in drawing.outlines]


def test_the_original_input_with_a_contactor_is_cut_and_builds() -> None:
    built = _built_ctr()
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in built.findings}
    outlines = _outlines(built.model)
    assert len(outlines) == 2
    assert {min(y for _, y in one.points) for _, one in outlines} == {
        min(y for _, y in outlines[0][1].points)
    }
    assert {page for page, _ in outlines} <= _plug_pages(built.model)


def test_the_build_finishes_with_no_error() -> None:
    built = _built()
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []


def test_the_boards_outline_draws_on_both_pages_with_its_plug() -> None:
    model = _built().model
    pages = {page for page, _ in _outlines(model)}
    assert len(pages) == 2
    assert pages & _plug_pages(model)


def _replica_only_page() -> tuple[DrawnOutline, Drawing]:
    model = _built().model
    plug_pages = _plug_pages(model)
    page, outline = next((p, o) for p, o in _outlines(model) if p not in plug_pages)
    return outline, drawn_pages(model)[page]


def _pins_left_to_right(tag: str) -> list[str]:
    """The pin names of device `tag`'s tags on the replica-only page, by x."""
    _, drawing = _replica_only_page()
    found = [(t.box.x, t.text.rsplit(":", 1)[-1]) for t in drawing.texts if f"-{tag}:" in t.text]
    return [pin for _, pin in sorted(found)]


_NATURAL = [str(n) for n in range(1, 15)]


def test_the_replicas_run_in_pin_order() -> None:
    assert _pins_left_to_right("J4") == _NATURAL


def test_the_far_pins_run_in_pin_order() -> None:
    assert _pins_left_to_right("Z2") == _NATURAL


def _inside(a: tuple[int, int], b: tuple[int, int], box: DrawnOutline) -> bool:
    """Whether the segment a-b has a piece strictly inside the box's open rectangle."""
    (x0, y0), (x1, y1) = a, b
    left, right = min(x for x, _ in box.points), max(x for x, _ in box.points)
    top, bottom = min(y for _, y in box.points), max(y for _, y in box.points)
    if x0 == x1:
        return left < x0 < right and min(y0, y1) < bottom and max(y0, y1) > top
    return top < y0 < bottom and min(x0, x1) < right and max(x0, x1) > left


def _wires_inside_the_outline() -> list[tuple[Any, ...]]:
    """Each wire segment inside the outline other than the one stub down from its replica."""
    outline, drawing = _replica_only_page()
    bottom = max(y for _, y in outline.points)
    bad = []
    for wire in drawing.wires:
        pts = list(wire.points)
        ends = {0: (pts[0], pts[1]), len(pts) - 2: (pts[-1], pts[-2])}
        for i, (a, b) in enumerate(pairwise(pts)):
            if not _inside(a, b, outline):
                continue
            at_replica = i in ends and a[0] == b[0] and max(a[1], b[1]) >= bottom > min(a[1], b[1])
            if at_replica and ends[i][0][1] < bottom:
                continue
            bad.append((wire.id, a, b))
    return bad


def test_no_wire_runs_inside_the_outline_except_at_its_replica() -> None:
    assert _wires_inside_the_outline() == []
