"""FD acceptance 7 (`docs/archive/specs/2026-09-26-fixed-designations.md`):
a unit at version 2, revision 1 prints `2.1` in each place a revision is printed.

One shared facade build: a cabinet unit (version 1, revision 2) with a nested `demo-io-board` unit
at version 2, revision 1, whose history holds two entries (`1.1` and `2.1`). One test per place;
each asserts the literal text first and then that the old bare or padded forms are not printed.
"""

import csv
import functools
import io

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document
from fransys_pdf import source
from fransys_pdf._lists import bom_page
from fransys_reports import bom_csv

from fransys_model.derive import bom_lines, unit_release, units
from fransys_model.derive.drawing_text import label_text
from fransys_model.kernel import Origin, Severity, evolve, make_id
from fransys_model.layout import Label, Outline, layout_of
from fransys_model.vocab import Document, DocumentPreset, PageKind, documents

_ORIGIN = Origin(file="tests/test_revision_print_form.py", line=1, note="FD acceptance 7")
_BOARD = "demo-io-board"
_CABINET = "demo-pump-cabinet"


def _io_board(s):
    """A board unit at version 2, revision 1, with a two-entry history (`1.1`, then `2.1`)."""
    u = s.unit(_BOARD, version=2, revision=1, interface="1")
    u.revision(1, date="2025-06-01", text="Version one release", created="XX", version=1)
    u.revision(1, date="2026-01-01", text="Version two release", created="XX")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.net("internal", k1.fn("co_1")["11"], k1.fn("co_2")["21"])
    u.boundary(x1)
    return x1


def _pump_cabinet(s):
    """A cabinet unit at version 1, revision 2 that nests the board unit."""
    u = s.unit(_CABINET, revision=2, interface="1")
    u.revision(2, date="2026-02-01", text="Cabinet release", created="XX")
    c = u.location("C1", "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
    board_x1 = _io_board(u.scope("io", at=c))
    w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
    p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
    cable.core(1, field[0].outer, p1["1"])
    cable.core(2, field[1].outer, p1["2"])
    u.mate(p1, board_x1)
    for t in field:
        u.boundary(t)
        u.unused(t)  # nothing crosses it: declared, so no BOUNDARY_UNCONNECTED


@functools.cache
def _build():
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(
        title="Pump station", number="P-1001", customer="Example Co", revision=1, author="OJB"
    )
    d.revision(1, date="2026-01-01", text="First issue", created="XX")
    _pump_cabinet(d.scope("pump", at=d.location("ER", "Engine room")))
    result = fr.build(parts, d.draft(), system_document())
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    return result.model


def _unit_id(model, name):
    (found,) = [u for u in sorted(units(model)) if unit_release(model, u).name == name]
    return found


def _with_document(model, unit_id, *, remove):
    doc = Document(
        id=make_id(Document, ("probe-doc", str(unit_id))),
        key=("probe-doc", str(unit_id)),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        unit=unit_id,
        add=(),
        remove=remove,
        cover="# Cover",
        notes=None,
    )
    return evolve(model, put=[doc], origin=_ORIGIN), doc


def test_the_build_has_the_board_at_version_2_revision_1():
    """The fixture itself: the unit under test is at version 2, revision 1, not `1.x`."""
    release = unit_release(_build(), _unit_id(_build(), _BOARD))
    assert (release.version, release.revision) == (2, 1)


def test_the_unit_documents_title_block_revision_cell_prints_2_1():
    """(a) The unit's own document: the title block's Revision cell."""
    model, doc = _with_document(
        _build(),
        _unit_id(_build(), _BOARD),
        remove=(PageKind.SCHEMATIC, PageKind.CONNECTOR_LIST, PageKind.BOM),
    )
    text = source(model, doc.id, {})
    assert 'text(size: 8pt, "Revision"), text(size: 10pt, text("2.1"))' in text
    for old in ("2", "1", "01", "1.1"):
        assert f'text(size: 8pt, "Revision"), text(size: 10pt, text("{old}"))' not in text


def test_the_cover_lists_both_history_rows_as_1_1_and_2_1():
    """(b) The cover's revision history: two entries, `1.1` and `2.1`, in date order."""
    model, doc = _with_document(
        _build(),
        _unit_id(_build(), _BOARD),
        remove=(PageKind.SCHEMATIC, PageKind.CONNECTOR_LIST, PageKind.BOM),
    )
    text = source(model, doc.id, {})
    first = 'text("1.1"), text("2025-06-01"), text("Version one release")'
    second = 'text("2.1"), text("2026-01-01"), text("Version two release")'
    assert first in text
    assert second in text
    assert text.index(first) < text.index(second)
    for old in ("01", "1", "2"):
        assert f'text("{old}"), text("2026-01-01")' not in text
    assert 'text("01"), text("2025-06-01")' not in text
    assert 'text("1"), text("2025-06-01")' not in text


def test_the_parents_bom_unit_line_prints_2_1():
    """(c) The cabinet's BOM: the `BomLine.revision` and the BOM page's source."""
    model = _build()
    cabinet = _unit_id(model, _CABINET)
    (line,) = [ln for ln in bom_lines(model, scope=cabinet) if ln.mpn == _BOARD]
    assert line.revision == "2.1"
    assert line.revision not in {"2", "1", "01"}

    model, doc = _with_document(model, cabinet, remove=(PageKind.SCHEMATIC,))
    text = bom_page(model, documents(model)[doc.id])
    assert '"Revision"' in text
    assert 'text("2.1")' in text
    assert 'text("01")' not in text  # the padded form; a bare `2` or `1` is also a count cell


def test_the_bom_csv_unit_row_prints_2_1():
    """(d) `bom.csv` of the cabinet: the board's unit row."""
    model = _build()
    rows = list(csv.DictReader(io.StringIO(bom_csv(model, scope=_unit_id(model, _CABINET)))))
    (row,) = [r for r in rows if r["mpn"] == _BOARD]
    assert row["revision"] == "2.1"
    assert row["revision"] not in {"2", "1", "01"}


def test_the_black_box_title_prints_rev_2_1():
    """(e) The board unit's outline on its parent's page: the outline title label."""
    model = _build()
    board = _unit_id(model, _BOARD)
    (outline,) = [o for o in layout_of(model, Outline).values() if o.unit == board]
    titles = [
        label_text(model, lb)
        for lb in layout_of(model, Label).values()
        if lb.page == outline.page and lb.slot == "outline_title"
    ]
    assert f"{_BOARD} rev 2.1" in titles
    for old in ("2", "1", "01"):
        assert f"{_BOARD} rev {old}" not in titles


def test_the_cabinet_cover_lists_its_own_history_not_the_nested_boards():
    """O3: a unit document's cover lists that unit's own history only (pdf README, owner
    2026-09-23). The nested board's revision shows in the parent's BOM, never on its cover.
    """
    model = _build()
    cabinet = _unit_id(model, _CABINET)
    model, doc = _with_document(
        model, cabinet, remove=(PageKind.SCHEMATIC, PageKind.CONNECTOR_LIST, PageKind.BOM)
    )
    text = source(model, doc.id, {})
    assert 'text("1.2"), text("2026-02-01"), text("Cabinet release")' in text
    for board_entry in ("Version one release", "Version two release", "2025-06-01", '"2.1"'):
        assert board_entry not in text
