"""Each CSV of a unit's write prints what the PDF list beside it prints (model-0054 section 4).

Designer ruling (a), 2026-09-24: a unit's `terminals-*.csv`, `connectors-*.csv` and
`wires.csv` get the SAME document context as the unit document's PDF lists, so their end
cells are equal cell for cell; `out/all/` (`unit=None`) has no document, so it prints the full
location path of every located end. The invented model: strip `X3` (terminal `T:1`) and board
`JB1`, both of unit `u1` and placed at `C1`; the terminal is wired inside to `B12` (at `C1`) and
outside to `M1` (at `EXT`); connector `J1` of the board is mated to housing `H1` at `EXT`, `J2`
to `H2` at `C1`.
"""

import csv
import importlib.util
import io
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fransys.pipeline import _exports
from fransys_pdf._lists import (
    _ends_without_jumpers,
    connector_rows_for,
    terminal_rows_for,
    wire_rows_for,
)

from fransys_model.derive import cell_text, pin_lines
from fransys_model.kernel import make_id
from fransys_model.vocab import DocumentPreset, Mate

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`, and
# ty cannot resolve a `sys.path` insert; `fransys_pdf`'s own hand-built model helpers are
# reused rather than copied, loaded from their file by path.
_BUILD_PATH = (
    Path(__file__).resolve().parent.parent / "packages" / "fransys-pdf" / "tests" / "_build.py"
)
_build_spec = importlib.util.spec_from_file_location("_pdf_tests_build", _BUILD_PATH)
assert _build_spec is not None
assert _build_spec.loader is not None
_build = importlib.util.module_from_spec(_build_spec)
sys.modules["_pdf_tests_build"] = _build
_build_spec.loader.exec_module(_build)
bridged_terminal = _build.bridged_terminal
conductor = _build.conductor
connector = _build.connector
document = _build.document
external_port = _build.external_port
item = _build.item
location = _build.location
model = _build.model
part = _build.part
pcb_facet = _build.pcb_facet
pin = _build.pin
place = _build.place
unit = _build.unit
wire_facet = _build.wire_facet


@pytest.fixture(scope="module")
def built():
    """(model, unit id, the unit's document, strip id, board id), exports not yet written."""
    c1 = location("C1", "Demo cabinet")
    ext = location("EXT", "Outside the cabinet")
    u = unit("u1", name="pump-cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    strip = item("x3", description="Strip three", unit=u.id)
    child, facet, fn, internal = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    child = replace(child, unit=u.id)  # a conductor belongs to the lowest unit holding both ends
    external = external_port("t1")
    b12, b12_fn, b12_port = pin("b12", "B12", unit=u.id)
    m1, m1_fn, m1_port = pin("m1", "M1", unit=u.id)
    b12_port = replace(b12_port, name="2/T1")
    m1_port = replace(m1_port, name="U1")
    w1 = conductor("w1", a=internal.id, b=b12_port.id)
    w2 = conductor("w2", a=external.id, b=m1_port.id)
    labels = (
        wire_facet("w1", subject=w1.id, label="W1"),
        wire_facet("w2", subject=w2.id, label="W2"),
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id, unit=u.id)
    h1 = item("h1", description="Housing outside")
    h2 = item("h2", description="Housing inside")
    j1 = connector("j1", item=board.id, name="J1", markings=("1",))
    j2 = connector("j2", item=board.id, name="J2", markings=("1",))
    p1 = connector("p1", item=h1.id, name="P1", markings=("1",))
    p2 = connector("p2", item=h2.id, name="P2", markings=("1",))
    mates = tuple(
        Mate(id=make_id(Mate, (key,)), key=(key,), a=a[2].id, b=b[2].id)
        for key, a, b in (("m1", j1, p1), ("m2", j2, p2))
    )
    connectors = [rec for group in (j1, j2, p1, p2) for rec in (*group[:4], *group[4])]
    places = (
        place("p-strip", item=strip.id, node=c1.id),
        place("p-b12", item=b12.id, node=c1.id),
        place("p-m1", item=m1.id, node=ext.id),
        place("p-jb1", item=board.id, node=c1.id),
        place("p-h1", item=h1.id, node=ext.id),
        place("p-h2", item=h2.id, node=c1.id),
    )
    records = (c1, ext, u, strip, child, facet, fn, internal, external)
    records += (b12, b12_fn, b12_port, m1, m1_fn, m1_port, w1, w2, *labels)
    records += (board_part, board, pcb_facet("board1", subject=board_part.id), h1, h2)
    m = model(*records, *connectors, *mates, *places)
    return m, u.id, doc, strip.id, board.id


def _read(exports, prefix):
    """The one export whose name contains `prefix` as a substring, parsed to a list of dicts."""
    (name,) = [n for n in exports if prefix in n and n.endswith(".csv")]
    return list(csv.DictReader(io.StringIO(exports[name].decode("utf-8"))))


def _unit_exports(built):
    m, unit_id, *_ = built
    return _exports(m, {}, unit=unit_id)


def _all_exports(built):
    m, *_ = built
    return _exports(m, {})


def _pdf_terminal_cells(built):
    """The (designation, Side A, Side B) cells the PDF terminal list of the unit document prints."""
    m, _unit_id, doc, strip, _board = built
    cells = []
    for row in terminal_rows_for(m, doc, strip):
        side_a, side_b = _ends_without_jumpers(m, row)
        cells.append((row.designation, cell_text(side_a), cell_text(side_b)))
    return cells


def test_a_units_terminal_csv_ends_equal_the_pdf_terminal_list_cell_for_cell(built):
    """Both lists, same strip: the same `side_a` and `side_b` cells, and not vacuously empty.
    Can-fail: dropping `context=` in the facade's per-strip CSV makes the inside end
    `+C1-B12:2/T1`, not the PDF's `-B12:2/T1`."""
    rows = _read(_unit_exports(built), "terminals-")
    csv_cells = [(row["designation"], row["side_a"], row["side_b"]) for row in rows]
    assert csv_cells == _pdf_terminal_cells(built)
    assert csv_cells == [("-X3:T:1", "-B12:2/T1", "+EXT-M1:U1")]


def test_out_all_terminal_csv_prints_the_full_text_of_the_no_unit_context(built):
    """`unit=None`: no document, no context: the inside end carries `+C1` too.
    Can-fail: passing the strip's context there makes the inside end short."""
    (row,) = _read(_all_exports(built), "terminals-")
    assert (row["side_a"], row["side_b"]) == ("+C1-B12:2/T1", "+EXT-M1:U1")


def test_a_units_wire_label_csv_equals_the_pdf_wire_label_list_row_for_row(built):
    """A unit document has no location, so both lists use no context: full paths.
    Can-fail: passing the strip's context to the unit's `wires.csv` shortens `+C1-B12:2/T1`.
    """
    m, _unit_id, doc, _strip, _board = built
    rows = _read(_unit_exports(built), "wires")
    csv_cells = [(r["from"], r["to"], r["label"]) for r in rows]
    pdf_cells = [(r.from_, r.to, r.label) for r in wire_rows_for(m, doc)]
    assert csv_cells == pdf_cells
    assert ("+C1-X3:T:1", "+EXT-M1:U1", "-X3:T:1 -M1:U1") in csv_cells  # the fixed end order (V8)


def test_a_units_connector_csv_mate_pins_equal_the_pdf_connector_list_cell_for_cell(built):
    """Both mate pins are outside the board: each prints its whole path (FAR-END-ONE-HOME A2)."""
    m, _unit_id, doc, _strip, board = built
    rows = _read(_unit_exports(built), "connectors-")
    csv_cells = [(r["designation"], r["marking"], r["mate_port_designation"]) for r in rows]
    pdf_cells = [
        (line[0], line[5], line[7]) for line in pin_lines(connector_rows_for(m, doc, board))
    ]
    assert csv_cells == pdf_cells
    assert {cell[2] for cell in csv_cells} == {"+EXT-H1:1", "+C1-H2:1"}


def test_out_all_connector_csv_prints_every_mate_pin_with_its_full_path(built):
    """Can-fail: passing the board's context there makes `+C1-H2:1` short."""
    rows = _read(_all_exports(built), "connectors-")
    assert {r["mate_port_designation"] for r in rows} == {"+EXT-H1:1", "+C1-H2:1"}
