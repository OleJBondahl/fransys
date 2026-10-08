"""Field case: a contact table under the lowest contactor of a tall board group leaves the page.

The engineering shape: a board unit with three interface headers (14, 4 and 14 pins). In one
function a harness runs from the last header down to two contactors (each coil and auxiliary contact
on a lead housing), and two more harnesses leave the other headers on the board's top edge. The
contactors' main poles are drawn on another page. Each coil gets a contact table of two rows
(A1-A2, T1-T2) under it.

The bug: the group's height (T1 of TALL-PAGE) counted the outline, its boxes and the lower columns,
not the tables hung under the contactors, so a group whose columns ended within one table height of
the content box was not cut and the tables ran across the title block (OUT_OF_CONTENT_BOX).
The fix (decision layout-0167, R8): the column reserve that holds the table's room sits on the
column's lowest cell and is the table's size, so the column's hull counts the table.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts
lazy import pytest

from fransys_layout.engines.schematic import engine
from fransys_layout.stages import pagerun
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.kernel import merge
from fransys_model.layout import (
    ConnectorBox,
    Label,
    LabelKind,
    LinkMarker,
    Outline,
    Page,
    Side,
    SymbolPlacement,
    layout_of,
)

WIRE = ("WH", 0.5)
_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
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
_POLES = "".join(
    f"""
[[function]]
name = "main{k}"
kind = "contact_no"
symbol = "make-contact"
ports = [
    {{ name = "A{k}", role = "generic", symbol_port = "in" }},
    {{ name = "B{k}", role = "generic", symbol_port = "out" }},
]
links = [{{ a = "A{k}", b = "B{k}", kind = "switched" }}]
"""
    for k in "123"
)
_CTR3 = (
    """schema = 1

[part]
mpn = "FLD-CTR3"
manufacturer = "Demo"
description = "Contactor with coil, three main poles and auxiliary contact"
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
"""
    + _POLES
    + """
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


def _library(root: Path) -> Path:
    """A library of headers, plugs, one lead housing and the contactor, all invented."""
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    parts = [("HDR", n, "male") for n in (1, 2, 4, 14)] + [("PLG", n, "female") for n in (1, 4, 14)]
    parts.append(("HSG", 4, "male"))
    for kind, n, gender in parts:
        mpn = f"FLD-{kind}-{n}" if kind != "HSG" else "FLD-HSG-4M"
        ports = ", ".join(
            f'{{ name = "{i}", role = "generic", symbol_port = "{"in" if i % 2 else "out"}" }}'
            for i in range(1, n + 1)
        )
        text = _PART.format(mpn=mpn, ports=ports, style=f"{mpn.lower()}-{n}p", n=n, gender=gender)
        if kind == "HSG":
            text = text.replace('gender = "male"', 'gender = "male"\nmates = ["FLD-PLG-4"]')
        (root / "parts" / f"{mpn.lower()}.toml").write_text(text)
    (root / "parts" / "ctr3.toml").write_text(_CTR3)
    return root


class _Board(NamedTuple):
    j7: fr.Device
    j3: fr.Device
    j4: fr.Device


@fr.unit("fld-board", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _board(u: Any) -> _Board:
    j3 = u.device("J3", "FLD-HDR-14", interface=True)
    j4 = u.device("J4", "FLD-HDR-4", interface=True)
    j7 = u.device("J7", "FLD-HDR-14", interface=True)
    return _Board(j7, j3, j4)


class _Top(NamedTuple):
    pass


def _link(u: Any, name: str, ends: tuple[Any, Any], n: int, plug: str) -> None:
    loom = u.harness(name)
    x = u.device("J1", plug, parent=loom, name=name + "a")
    u.mate(x, ends[0])
    y = u.device("J2", plug, parent=loom, name=name + "b")
    u.mate(y, ends[1])
    for k in range(1, n + 1):
        u.wire(x[str(k)], y[str(k)], wire=WIRE)


@fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _top(u: Any) -> _Top:
    contactors = []
    with u.function("S1", "String 1"):
        board = u.add(_board, "A1")
        loom = u.harness("W1")
        plug = u.device("J1", "FLD-PLG-14", parent=loom, name="p1")
        u.mate(plug, board.j7)
        for i in range(2):
            q = u.device(f"Q{i + 1}", "FLD-CTR3")
            contactors.append((i, q))
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
                u.wire(plug[str(4 * i + pin)], lead[str(pin)], wire=WIRE)
    with u.function("OTH", "Other"):
        _link(u, "T1", (board.j3, u.device("H1", "FLD-HDR-14")), 14, "FLD-PLG-14")
        _link(u, "U1", (board.j4, u.device("G1", "FLD-HDR-4")), 4, "FLD-PLG-4")
    with u.function("PWR", "Power"):
        for i, q in contactors:
            far = u.device(f"X{i + 1}", "FLD-HDR-2")
            for k in "123":
                u.wire(far["1"], getattr(q, f"main{k}")[f"A{k}"], wire=WIRE)
    return _Top()


def _built() -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    library = _library(root / "lib")
    d = fr.Design(merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(library)))
    d.add(_top, "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    )


def test_the_contact_tables_under_the_contactors_stay_in_the_content_box() -> None:
    built = _built()
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in built.findings}


def test_the_column_reserve_reaches_at_least_as_far_as_the_placed_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R8 drift: the reserve's bottom on a page is not above any table `contact_images` places.

    UNDO: `image_reserves` puts the room on a cell that is not the lowest, and a table passes it.
    """
    reserved: dict[tuple[int, int], int] = {}
    tables: list[tuple[tuple[int, int], int]] = []
    unreserve, images = pagerun.unreserve, engine.contact_images

    def keep(placed: Any, rooms: Any) -> Any:
        for one in placed:
            reach = placed_keepout(one)
            at = (one.drawing_set, one.page)
            reserved[at] = max(reserved.get(at, 0), reach.y + reach.height)
        return unreserve(placed, rooms)

    def note(*args: Any, **kwargs: Any) -> Any:
        found = images(*args, **kwargs)
        for _, labels in found[0]:
            tables.extend(
                ((one.drawing_set, one.page), one.box.y + one.box.height)
                for one in labels
                if one.slot == "contacts"
            )
        return found

    monkeypatch.setattr(pagerun, "unreserve", keep)
    monkeypatch.setattr(engine, "contact_images", note)
    _built()
    assert tables
    assert all(reserved[at] >= bottom for at, bottom in tables)


class _LugBoard(NamedTuple):
    lug_in: fr.Device
    lug_out: fr.Device
    lug_low: fr.Device | None
    j7: fr.Device
    j3: fr.Device
    j4: fr.Device


def _lug_board(*, low: bool) -> Any:
    """`_board` plus two one-pin headers that sort first, so they take the top edge; `low` adds a
    third that sorts last, which takes the bottom edge."""

    @fr.unit(
        f"fld-lug-board-{int(low)}",
        revision=1,
        interface_version=1,
        date="2026-10-08",
        text="t",
        by="X",
    )
    def build(u: Any) -> _LugBoard:
        lug_in = u.device("J1", "FLD-HDR-1", interface=True)
        lug_out = u.device("J2", "FLD-HDR-1", interface=True)
        lug_low = u.device("J9", "FLD-HDR-1", interface=True) if low else None
        j3 = u.device("J3", "FLD-HDR-14", interface=True)
        j4 = u.device("J4", "FLD-HDR-4", interface=True)
        j7 = u.device("J7", "FLD-HDR-14", interface=True)
        return _LugBoard(lug_in, lug_out, lug_low, j7, j3, j4)

    return build


def _lug_top(contactors: int, *, low: bool) -> Any:
    """R9: the board's input lug wires to a fuse of its function, its output lug to the unit's own
    two-pin connector, drawn on a later page. `low` mates a third lug to a second fuse: a plug
    wired without a harness at the bottom edge, which is where the harness ends are.
    """
    name = f"fld-lug-top-{contactors}-{int(low)}"

    @fr.unit(name, revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def build(u: Any) -> _Top:
        qs = []
        with u.function("S1", "String 1"):
            fuse = u.device("F1", "DEMO-FUSE-HOLDER-PCB")
            board = u.add(_lug_board(low=low), "A1")
            lug = u.device("P1", "FLD-PLG-1", name="lugin")
            u.mate(lug, board.lug_in)
            u.wire(lug["1"], fuse["2"], wire=("RD", 6))
            out = u.device("P2", "FLD-PLG-1", name="lugout")
            u.mate(out, board.lug_out)
            if low:
                low_plug = u.device("P3", "FLD-PLG-1", name="luglow")
                u.mate(low_plug, board.lug_low)
                u.wire(low_plug["1"], u.device("F2", "DEMO-FUSE-HOLDER-PCB")["1"], wire=("RD", 6))
            loom = u.harness("W1")
            plug = u.device("J1", "FLD-PLG-14", parent=loom, name="p1")
            u.mate(plug, board.j7)
            for i in range(contactors):
                q = u.device(f"Q{i + 1}", "FLD-CTR3")
                qs.append((i, q))
                housing = u.device(
                    "J1",
                    "FLD-HSG-4M",
                    parent=q,
                    name=f"h{i}",
                    joins={
                        "1": q.coil["X1"],
                        "2": q.coil["X2"],
                        "3": q.aux["T1"],
                        "4": q.aux["T2"],
                    },
                )
                lead = u.device(f"J{i + 2}", "FLD-PLG-4", parent=loom, name=f"lp{i}")
                u.mate(lead, housing)
                for pin in range(1, 5):
                    u.wire(plug[str(4 * i + pin)], lead[str(pin)], wire=WIRE)
        with u.function("OTH", "Other"):
            _link(u, "T1", (board.j3, u.device("H1", "FLD-HDR-14")), 14, "FLD-PLG-14")
            _link(u, "U1", (board.j4, u.device("G1", "FLD-HDR-4")), 4, "FLD-PLG-4")
        with u.function("PWR", "Power"):
            for i, q in qs:
                far = u.device(f"X{i + 1}", "FLD-HDR-2")
                for k in "123":
                    u.wire(far["1"], getattr(q, f"main{k}")[f"A{k}"], wire=WIRE)
        with u.function("OUT", "Output"):
            boundary = u.device("X9", "FLD-HDR-2", interface=True)
            u.wire(out["1"], boundary["1"], wire=("RD", 6))
        return _Top()

    return build


def _built_with_lugs(contactors: int = 2, *, low: bool = False) -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    library = _library(root / "lib")
    d = fr.Design(merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(library)))
    top = _lug_top(contactors, low=low)
    d.add(top, "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    name = f"fld-lug-top-{contactors}-{int(low)}"
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), name, cover=root / "cover.md")
    return fr.build(d, doc)


def _numbers(built: fr.BuildResult) -> dict[Any, int]:
    return {page.id: page.number for page in layout_of(built.model, Page).values()}


def _symbol_pages(built: fr.BuildResult, designation: str) -> set[int]:
    numbers = _numbers(built)
    return {
        numbers[one.page]
        for one in layout_of(built.model, SymbolPlacement).values()
        if designation in "/".join(map(str, one.key))
    }


def _board_outline_page(built: fr.BuildResult) -> int:
    numbers = _numbers(built)
    (page,) = {
        numbers[one.page]
        for one in layout_of(built.model, Outline).values()
        if "A1" in "/".join(map(str, one.key))
    }
    return page


def test_a_board_with_two_lug_plugs_on_its_top_edge_is_cut_at_its_bottom_edge() -> None:
    """R9 (A1): lugs on the top edge hold the top cut, so the group cuts at the bottom edge.

    The upper band and the outline stay on the board's page with the bottom-edge plug boxes; the
    contactors (the lower band) stand on the next page, their contact tables with them.
    """
    built = _built_with_lugs()
    codes = {f.code for f in built.findings}
    assert "OUT_OF_CONTENT_BOX" not in codes
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []
    board = _board_outline_page(built)
    assert _symbol_pages(built, "Q1/fn/coil") == _symbol_pages(built, "Q2/fn/coil") == {board + 1}
    numbers = _numbers(built)
    plug_pages = {
        numbers[one.page]
        for one in layout_of(built.model, ConnectorBox).values()
        if "S1/p1" in "/".join(str(part) for part in one.key)
    }
    assert plug_pages == {board}
    tables = [
        numbers[one.page]
        for one in layout_of(built.model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.slot == "contacts"
    ]
    assert sorted(tables) == [board + 1, board + 1]


def test_a_board_with_a_wireless_plug_on_each_edge_keeps_out_of_content_box() -> None:
    """R9 (A1): lugs on both edges leave no cut that works, so the page is held (layout-0167).

    This passes before the bottom cut is built (the group is held already); it pins the held
    shape against the bottom cut taking a group whose lower band holds a bottom-edge plug.
    """
    built = _built_with_lugs(1, low=True)
    assert "OUT_OF_CONTENT_BOX" in {f.code for f in built.findings}


def test_the_bottom_edge_line_ends_in_a_stub_on_each_page_the_second_facing_north() -> None:
    """R9 (A1): W1's root stands on the board's page, so its trunk runs out south to a stub; on the
    contactors' page the root is absent, so the trunk runs north, the way it enters the root's box.
    """
    built = _built_with_lugs()
    board = _board_outline_page(built)
    numbers = _numbers(built)
    stubs = {
        numbers[one.page]: one.facing
        for one in layout_of(built.model, LinkMarker).values()
        if "line_stub" in one.key and "S1/W1" in "/".join(str(part) for part in one.key)
    }
    assert stubs == {board: Side.S, board + 1: Side.N}
