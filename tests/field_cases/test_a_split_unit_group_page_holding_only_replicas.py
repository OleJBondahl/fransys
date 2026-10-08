"""Field case: a split unit group whose second page holds only no-line pin replicas.

The engineering shape: a board unit has one header with a harness line (a plug on it) and three
headers with none, wired straight to outside headers. The wide one's ten wires make its column so
tall that the page splits and that column stands alone on page 2.

The bug: the group's outline part on page 2 (layout-0153, HL21: one outline part per page) draws
only the interfaces its columns reach, and the line interface reaches page 1 only. `_shape` took
its lead from the first line box and raised IndexError on page 2, so the build crashed.
The fix (decision layout-0164): the part's lead is the first no-line interface that has a replica
on the page, so the outline part draws there holding the replicas.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts

from fransys_model import derive
from fransys_model.kernel import merge
from fransys_model.layout import ConnectorBox, Outline, layout_of

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
        b=u.device("J2", "FLD-HDR-4", interface=True),
        c=u.device("J3", "FLD-HDR-2", interface=True),
        d=u.device("J4", "FLD-HDR-10", interface=True),
    )


class _Top(NamedTuple):
    pass


@fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _top(u: Any) -> _Top:
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
    for pin in range(1, 5):
        u.wire(p[str(pin)], lp[str(pin)], wire=("WH", 0.5))
    for tag, part, board_pin, count in (
        ("Y1", "FLD-HDR-4", b.b, 4),
        ("Z1", "FLD-HDR-10", b.c, 2),
        ("Z2", "FLD-HDR-14", b.d, 10),
    ):
        far = u.device(tag, part)
        for pin in range(1, count + 1):
            u.wire(board_pin[str(pin)], far[str(pin)], wire=("WH", 0.5))
    return _Top()


@cache
def _built() -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(_top, "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    return fr.build(d, doc)


def test_the_build_finishes_with_no_error() -> None:
    built = _built()
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []


def test_the_boards_outline_draws_on_both_pages_with_its_plug() -> None:
    model = _built().model
    board = next(
        u for u in derive.units(model) if derive.unit_release(model, u).name == "fld-board"
    )
    pages = {o.page for o in layout_of(model, Outline).values() if o.unit == board}
    assert len(pages) == 2
    plug_pages = {b.page for b in layout_of(model, ConnectorBox).values()}
    assert pages & plug_pages
