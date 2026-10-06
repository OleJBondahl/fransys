"""UNIT-ID I5 and acceptance 4 (files half) and 6: export names in a unit's folder.

A per-item export in a unit's folder is named from the item's designation printed for that unit
(`terminals-X2.csv`, no location path of the parent's); the unit's own root takes the bare kind
(`connectors.csv`, `terminals.csv`, `wago.xml`); `out/all/` keeps the full reference-designation
names; a stale export under either shape is removed by a rewrite.
"""

import csv
import io
import sys
import tempfile
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys import _subjects
from fransys.pipeline import BuildResult, ExportNameClash, _export_name

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by name.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design
from test_write_unit_worked_example import (
    _ALL_WRITE_FILES,
    _PUMP1_BOARD_WRITE_FILES,
    _PUMP1_WRITE_FILES,
    _unit_id,
)

from fransys_model.kernel import Draft, Origin, freeze, make_id, merge
from fransys_model.vocab import (
    Document,
    DocumentPreset,
    Item,
    PageKind,
    PartCategory,
    Unit,
    UnitRelease,
)
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.templates import Part

_BARE_NAMES = ("terminals.csv", "connectors.csv", "wago.xml")


@pytest.fixture(scope="module")
def worked():
    """The units worked example with its three documents: (result, pump1 cabinet, pump1 board)."""
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    draft = d.draft()
    probe = fr.build(parts, draft, system_document()).model
    cabinet = _unit_id(probe, name="demo-pump-cabinet", prefix="pump1")
    board = _unit_id(probe, name="demo-io-board", prefix="pump1")
    covers = Path(tempfile.mkdtemp())
    for stem in ("cabinet", "board", "system"):
        (covers / f"{stem}.md").write_text(f"# {stem}\n", encoding="utf-8")
    documents = (
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=covers / "cabinet.md"),
        fr.document(fr.DocumentPreset.PCB_SCHEMATIC, board, cover=covers / "board.md"),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=covers / "system.md"),
    )
    return fr.build(parts, draft, *documents), cabinet, board


@pytest.fixture(scope="module")
def board_write(worked, tmp_path_factory):
    """The worked example's board unit, written once and shared by every test that reads it."""
    result, _cabinet, board = worked
    return fr.write(result, tmp_path_factory.mktemp("board"), unit=board)


@pytest.fixture(scope="module")
def cabinet_write(worked, tmp_path_factory):
    """The worked example's cabinet unit, written once and shared by every test that reads it."""
    result, cabinet, _board = worked
    return fr.write(result, tmp_path_factory.mktemp("cabinet"), unit=cabinet)


def _names(paths):
    return {p.name for p in paths}


def _rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


# -- the worked example's folders -------------------------------------------------------------


def test_the_boards_own_root_connector_list_is_the_bare_kind(board_write):
    names = _names(board_write)
    assert "demo-io-board-v1.3-connectors.csv" in names
    assert not any("connectors-" in name for name in names)


def test_the_cabinets_strip_list_is_named_relative_to_the_unit(cabinet_write):
    names = _names(cabinet_write)
    assert {n for n in names if "terminals" in n} == {"demo-pump-cabinet-v1.2-terminals-X2.csv"}
    assert "terminals.csv" not in names, "the strip is not the unit's sole root, so not bare"


def test_no_name_in_a_unit_folder_carries_the_location_path(cabinet_write, board_write):
    expected = {"cabinet": _PUMP1_WRITE_FILES, "board": _PUMP1_BOARD_WRITE_FILES}
    for label, written in (("cabinet", cabinet_write), ("board", board_write)):
        names = _names(written)
        assert names == expected[label], label
        assert not any("ER-C1" in name or "BRD" in name for name in names), (label, names)


def test_out_all_keeps_the_full_reference_designation_names(worked, tmp_path):
    result, _cabinet, _board = worked
    names = _names(fr.write(result, tmp_path, unit=None))
    assert names == _ALL_WRITE_FILES
    assert "P-1001-v1.1-terminals-ER-C1-X2.csv" in names
    assert not names & {"terminals-X2.csv", *_BARE_NAMES}


# -- acceptance 4, files half -----------------------------------------------------------------


def test_the_boards_folder_never_names_the_boards_own_tag(board_write, cabinet_write):
    written = board_write
    assert not any("U1" in p.name for p in written)
    by_name = {p.name: p for p in written}
    text_files = {name for name in by_name if not name.endswith(".pdf")}
    assert text_files == {
        "demo-io-board-v1.3-bom.csv",
        "demo-io-board-v1.3-connectors.csv",
        "demo-io-board-v1.3-designations.csv",
        "demo-io-board-v1.3-plc.csv",
        "demo-io-board-v1.3-wires.csv",
    }, "the loop below reads every text file the board unit writes, not a subset"
    for name in sorted(text_files):
        assert "-U1" not in by_name[name].read_text(encoding="utf-8"), name

    designations = {
        row["designation"] for row in _rows(by_name["demo-io-board-v1.3-designations.csv"])
    }
    assert designations == {"-K1", "-X1"}, "no row for the root board"

    (board_line,) = (
        row for row in _rows(by_name["demo-io-board-v1.3-bom.csv"]) if row["mpn"] == "DEMO-PCB-IO"
    )
    assert board_line["count"] == "1"
    assert board_line["designations"] == "", "the bare board's line stays, its cell empty"

    # the same board still prints as `-U1` where the parent lists it
    parent = cabinet_write
    parent_bom = next(p for p in parent if p.name == "demo-pump-cabinet-v1.2-bom.csv")
    (unit_line,) = (row for row in _rows(parent_bom) if row["mpn"] == "demo-io-board")
    assert unit_line["designations"] == "-U1"


# -- own-root strip and rack; relative names of a non-root strip and rack ---------------------


def _unit_design(*, strip, rack):
    """A one-unit design whose roots are the requested strip and/or PLC rack."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    if strip:
        # a lone unwired terminal draws nothing (LAYOUT_MISSING); wire it out across the
        # unit's boundary to a top-level motor, as the worked example's field terminals are
        terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
        u.boundary(terminal)
        fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
        motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
        d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    if rack:
        rack_item = u.item(None, tag="U1", at=c1, group=grp)
        u.item(
            "DEMO-PLC-DO-2", tag="DO1", name="do", parent=rack_item, position=1, at=c1, group=grp
        )
    return fr.build(parts, d.draft(), system_document()), u


def _unit_names(tmp_path, *, strip, rack):
    result, unit = _unit_design(strip=strip, rack=rack)
    return _names(fr.write(result, tmp_path, unit=unit))


def test_a_strip_that_is_the_sole_root_of_its_unit_is_the_bare_terminals_csv(tmp_path):
    names = _unit_names(tmp_path, strip=True, rack=False)
    assert "demo-unit-v1.1-terminals.csv" in names
    assert not any(("terminals-" in name) or ("wago" in name) for name in names)


def test_a_rack_that_is_the_sole_root_of_its_unit_is_the_bare_wago_xml(tmp_path):
    names = _unit_names(tmp_path, strip=False, rack=True)
    assert "demo-unit-v1.1-wago.xml" in names
    assert not any(("wago-" in name) or ("terminals" in name) for name in names)


def test_a_strip_and_a_rack_beside_each_other_take_unit_relative_names(tmp_path):
    names = _unit_names(tmp_path, strip=True, rack=True)
    assert {"demo-unit-v1.1-terminals-X1.csv", "demo-unit-v1.1-wago-U1.xml"} <= names
    assert not names & set(_BARE_NAMES)
    assert not any("C1" in name for name in names)


# -- stale cleanup ----------------------------------------------------------------------------


def test_a_rewrite_removes_stale_bare_and_dashed_exports_and_keeps_other_files(worked, tmp_path):
    result, cabinet, _board = worked
    stale = ("connectors-PLC-C1-U2.csv", "connectors.csv", "terminals.csv", "wago.xml")
    for name in stale:
        (tmp_path / name).write_text("stale", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")

    written = _names(fr.write(result, tmp_path, unit=cabinet))

    assert not written & set(stale)
    remaining = {p.name for p in tmp_path.iterdir()}
    assert not remaining & set(stale)
    assert "demo-pump-cabinet-v1.2-terminals-X2.csv" in remaining
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "keep me"


# -- name clash -------------------------------------------------------------------------------

_ORIGIN = Origin(file="test_unit_export_names.py", line=1, note="deliberate clash")


def _two_boards_in_one_unit(tags):
    """Two roots of one unit, each a board with its own tag: no sole root, so both unit-relative."""
    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", "u", "1", "1")),
        key=("unit_release", "u", "1", "1"),
        name="u",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(id=make_id(Unit, ("u",)), key=("u",), release=release.id, parent=None)
    records = [release, unit]
    for suffix, tag in zip("ab", tags, strict=True):
        part = Part(
            id=make_id(Part, (f"board-{suffix}",)),
            key=(f"board-{suffix}",),
            mpn=f"SIM-BOARD-{suffix}",
            manufacturer="Example Co",
            description="Invented board",
            category=PartCategory.BOARD,
            class_code="A",
        )
        pcb = PcbFacet(
            id=make_id(PcbFacet, (f"board-{suffix}", "pcb")),
            key=(f"board-{suffix}", "pcb"),
            subject=part.id,
            revision="A",
        )
        item = Item(
            id=make_id(Item, (f"board-item-{suffix}",)),
            key=(f"board-item-{suffix}",),
            part=part.id,
            parent=None,
            position=None,
            tag=tag,
            description="Invented board",
            unit=unit.id,
        )
        records.extend([part, pcb, item])
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft), unit.id


def test_two_boards_with_one_relative_name_in_one_unit_folder_raise(tmp_path):
    model, unit = _two_boards_in_one_unit(("X1", "X1"))
    with pytest.raises(ExportNameClash, match=r"connectors-X1\.csv"):
        fr.write(BuildResult(model=model, findings=()), tmp_path, unit=unit)


def test_two_boards_with_distinct_relative_names_in_one_unit_folder_do_not_clash(tmp_path):
    model, unit = _two_boards_in_one_unit(("X1", "X2"))
    written = fr.write(BuildResult(model=model, findings=()), tmp_path, unit=unit)
    assert {"u-v1.1-connectors-X1.csv", "u-v1.1-connectors-X2.csv"} <= _names(written)


# -- EXPORT-NAMES Part 1: export_set_name, export_prefix, _export_name's join -----------------


def test_export_set_name_and_prefix_are_empty_with_no_project_and_no_unit():
    """EN1: a system write of a model with no `Project` at all has no prefix."""
    model = freeze(Draft())
    assert _subjects.export_set_name(model, None) == ""
    assert _subjects.export_prefix(model, None) == ""


def test_export_set_name_and_prefix_for_the_system_use_the_projects_number_and_revision(worked):
    """EN1's system case, the spec's own worked numbers: `Project` number `P-1001`, version 1
    (defaulted, `_PROJECT` gives none), revision 1."""
    result, _cabinet, _board = worked
    assert _subjects.export_set_name(result.model, None) == "P-1001"
    assert _subjects.export_prefix(result.model, None) == "P-1001-v1.1"


def test_export_set_name_and_prefix_for_a_unit_use_its_own_release_not_the_project(worked):
    """EN1's unit case: the release's own name, version and revision, never the `Project`'s,
    even though this fixture's model has a `Project` (`P-1001-v1.1`) too."""
    result, cabinet, board = worked
    assert _subjects.export_set_name(result.model, cabinet) == "demo-pump-cabinet"
    assert _subjects.export_prefix(result.model, cabinet) == "demo-pump-cabinet-v1.2"
    assert _subjects.export_set_name(result.model, board) == "demo-io-board"
    assert _subjects.export_prefix(result.model, board) == "demo-io-board-v1.3"


def test_export_prefix_reads_the_projects_actual_version():
    """Every other fixture's `Project` defaults `version` to 1, which would let a bug that
    always read `.version` as 1 slip through unnoticed; this one overrides it to 2."""
    d = fransys_author.Design(fr.parts())
    d.project(
        title="Pump station",
        number="P-1001",
        customer="Example Co",
        revision=1,
        author="OJB",
        version=2,
    )
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    assert _subjects.export_prefix(result.model, None) == "P-1001-v2.1"


def test_export_prefix_for_a_unit_is_unaffected_by_a_missing_project():
    """EN1: 'a unit's document still takes its unit's prefix' -- a unit's prefix comes from
    its own release whether or not the model has a `Project` at all, unlike
    `test_export_set_name_and_prefix_for_a_unit_use_its_own_release_not_the_project`'s model,
    which does have one."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    u = d.scope("cab").unit("demo-unit", version=3, revision=4, interface="1")
    u.revision(4, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    result = fr.build(parts, d.draft(), system_document())
    assert _subjects.export_set_name(result.model, u.unit_id) == "demo-unit"
    assert _subjects.export_prefix(result.model, u.unit_id) == "demo-unit-v3.4"


def test_export_name_joins_prefix_kind_and_fragment(worked):
    """EN2: `_export_name` joins whichever of prefix/kind/fragment is non-empty with `-`."""
    result, _cabinet, _board = worked
    model = result.model
    assert _export_name(model, None, "pdf") == "P-1001-v1.1.pdf"
    assert _export_name(model, None, "csv", kind="bom") == "P-1001-v1.1-bom.csv"
    assert _export_name(model, None, "csv", kind="terminals", fragment="X2") == (
        "P-1001-v1.1-terminals-X2.csv"
    )


def test_export_name_with_no_project_gives_todays_bare_names():
    """EN1's own escape hatch: an empty prefix leaves `_export_name` at today's bare names."""
    model = freeze(Draft())
    assert _export_name(model, None, "csv", kind="bom") == "bom.csv"
    assert _export_name(model, None, "csv", kind="terminals", fragment="X1") == "terminals-X1.csv"


# -- EXPORT-NAMES Part 1, acceptance 2: stale exports removed by prefix (EN4) -----------------


def test_a_unit_write_removes_its_own_stale_export_and_keeps_the_current_revision(tmp_path):
    """Acceptance 2, unit-folder case (EN4's glob 1). The stale file is a CSV, not a PDF: the
    pre-EN `*.pdf` entry of `_STALE_EXPORT_PATTERNS` deletes every PDF regardless of glob 1,
    so a PDF-only assertion would pass even with glob 1 broken, proving nothing. The release
    is built at version 2, revision 1 (`2.1`), numerically *higher* than the stale file's
    `1.5` -- matching the spec's own `2.1`-vs-`1.5` shape (pairing it with a `1.2` release, as
    `worked`'s cabinet is, would invert which one looks stale)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    u = d.scope("cab").unit("demo-unit", version=2, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    result = fr.build(parts, d.draft(), system_document())

    (tmp_path / "demo-unit-v1.5-bom.csv").write_text("stale", encoding="utf-8")

    written = _names(fr.write(result, tmp_path, unit=u))

    remaining = {p.name for p in tmp_path.iterdir()}
    assert "demo-unit-v1.5-bom.csv" not in remaining
    assert "demo-unit-v2.1-bom.csv" in written


def test_a_system_write_removes_a_units_stale_export_by_its_own_release_name(worked, tmp_path):
    """Acceptance 2, system-write case (EN4's glob 2, the spec's own worked case). `worked`'s
    `Project` is `P-1001-v1.1`; its cabinet release is `demo-pump-cabinet` at `1.2`. A stale
    `demo-pump-cabinet-v1.1-bom.csv` (a lower revision, `1.1`) matches neither a bare
    `_STALE_EXPORT_PATTERNS` name nor the system's own `P-1001-v*` glob 1 -- only glob 2, which
    walks every unit release's name in the model, catches it: that CSV is what actually proves
    glob 2 runs. A same-revision stale `.pdf` is planted alongside it only to show that a
    PDF-only assertion would prove nothing (the bare `*.pdf` pattern already deletes every PDF
    whether or not glob 2 exists, decision 0027's precedent). An unrelated file survives,
    proving the clean-up is not a wipe of the whole folder."""
    result, _cabinet, _board = worked
    (tmp_path / "demo-pump-cabinet-v1.1-bom.csv").write_text("stale", encoding="utf-8")
    (tmp_path / "demo-pump-cabinet-v1.1.pdf").write_text("stale", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")

    fr.write(result, tmp_path, unit=None)

    remaining = {p.name for p in tmp_path.iterdir()}
    assert "demo-pump-cabinet-v1.1-bom.csv" not in remaining
    assert "demo-pump-cabinet-v1.1.pdf" not in remaining
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "keep me"


# -- EXPORT-NAMES Part 2: EN3, a document named by its own subject ----------------------------


def _location_document_design(covers):
    """A project, a unit's own cabinet location, one `CABINET_SCHEMATIC` document per cover
    given, all sharing that one location (export-names EN3, acceptance 3)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="t", number="EN3-1", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    docs = tuple(
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover) for cover in covers
    )
    return fr.build(parts, d.draft(), *docs)


def test_two_documents_with_one_location_subject_and_preset_raise(tmp_path):
    """Acceptance 3, first half: two documents that share one location subject and one preset
    compute the same name and raise, the message naming both cover stems (not merely raising)."""
    cover_a = tmp_path / "cover-a.md"
    cover_a.write_text("# A\n", encoding="utf-8")
    cover_b = tmp_path / "cover-b.md"
    cover_b.write_text("# B\n", encoding="utf-8")
    result = _location_document_design((cover_a, cover_b))
    with pytest.raises(ExportNameClash) as excinfo:
        fr.write(result, tmp_path / "out", unit=None)
    message = str(excinfo.value)
    assert "document/cover-a" in message
    assert "document/cover-b" in message


def test_a_document_renamed_through_its_cover_keeps_the_same_pdf_name(tmp_path):
    """Acceptance 3, second half: the PDF name is a pure function of the subject, not of the
    cover file -- two otherwise-identical documents differing only in cover stem write the
    same PDF name (built one at a time, so neither run raises the clash above)."""
    cover_a = tmp_path / "cover-a.md"
    cover_a.write_text("# A\n", encoding="utf-8")
    cover_b = tmp_path / "cover-b.md"
    cover_b.write_text("# B\n", encoding="utf-8")
    names_a = _names(fr.write(_location_document_design((cover_a,)), tmp_path / "out-a", unit=None))
    names_b = _names(fr.write(_location_document_design((cover_b,)), tmp_path / "out-b", unit=None))
    pdf_a = {n for n in names_a if n.endswith(".pdf")}
    pdf_b = {n for n in names_b if n.endswith(".pdf")}
    assert pdf_a == pdf_b
    assert len(pdf_a) == 1


def _no_project_unit_and_system_design(tmp_path):
    """A model with no `Project` at all, holding both a unit with its own `CABINET_SCHEMATIC`
    document and a top-level `SYSTEM` document (export-names EN1/EN3, acceptance 4)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    u = d.scope("cab").unit("demo-unit", version=2, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    cabinet_cover = tmp_path / "cabinet.md"
    cabinet_cover.write_text("# Cabinet\n", encoding="utf-8")
    system_cover = tmp_path / "system.md"
    system_cover.write_text("# System\n", encoding="utf-8")
    docs = (
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, u, cover=cabinet_cover),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover),
    )
    return fr.build(parts, d.draft(), *docs)


def test_a_system_write_with_no_project_writes_the_bare_cover_stem_for_the_system_document(
    tmp_path,
):
    """Acceptance 4a: with no `Project`, the system's own document keeps today's bare
    `<cover-stem>.pdf`, through `_export_name`'s own fallback, not a separate f-string."""
    result = _no_project_unit_and_system_design(tmp_path)
    names = _names(fr.write(result, tmp_path / "out", unit=None))
    assert "system.pdf" in names


def test_a_system_write_with_no_project_still_names_the_units_document_by_its_release(tmp_path):
    """Acceptance 4b: the SAME no-`Project` model's unit document is never bare -- it always
    takes its own release's prefix, even from the system write's own unprefixed scope."""
    result = _no_project_unit_and_system_design(tmp_path)
    names = _names(fr.write(result, tmp_path / "out", unit=None))
    assert "demo-unit-v2.1.pdf" in names
    assert "cabinet.pdf" not in names


# -- EXPORT-NAMES Part 2, acceptance 5: a unit document's name follows its unit's release -----

# Leaves only the `COVER` page (`NOTES` is dropped automatically, no notes text): a hand-built
# unit with no items, board or wiring of its own has nothing for `SCHEMATIC`/`PLC_LIST`/
# `TERMINAL_LIST`/`BOM` to read, so removing them keeps `_compile_pdf` cheap and avoids a
# `DOCUMENT_NO_DRAWINGS` finding a `SCHEMATIC` page with no drawing set would otherwise raise.
_MINIMAL_UNIT_DOCUMENT_REMOVE = (
    PageKind.SCHEMATIC,
    PageKind.PLC_LIST,
    PageKind.TERMINAL_LIST,
    PageKind.BOM,
)


def _unit_document(unit_id, cover_stem):
    """A minimal `CABINET_SCHEMATIC` document whose subject is `unit_id` (export-names EN3)."""
    return Document(
        id=make_id(Document, ("document", cover_stem)),
        key=("document", cover_stem),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        add=(),
        remove=_MINIMAL_UNIT_DOCUMENT_REMOVE,
        cover=f"# {cover_stem}\n",
        notes=None,
        unit=unit_id,
    )


def _one_unit_with_document(*, name="solo-cabinet", version=1, revision=1):
    """One `Unit` instance of one `UnitRelease`, with its own document (acceptance 5a)."""
    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", name, str(version), str(revision))),
        key=("unit_release", name, str(version), str(revision)),
        name=name,
        version=version,
        revision=revision,
        interface="1",
    )
    unit = Unit(id=make_id(Unit, (name,)), key=(name,), release=release.id, parent=None)
    document = _unit_document(unit.id, f"{name}-cover")
    draft = Draft()
    draft.extend([release, unit, document], origin=_ORIGIN)
    return freeze(draft), unit.id


def _two_units_of_one_release(*, name="shared-cabinet", version=1, revision=1):
    """Two `Unit` instances of ONE `UnitRelease` id, each the subject of its own document
    (acceptance 5b): the author API mints a fresh release per `.unit(...)` call, never two
    instances of one, so this is hand-built via `Draft`/`freeze`, mirroring
    `_two_boards_in_one_unit`'s own style for a deliberately-clashing fixture."""
    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", name, str(version), str(revision))),
        key=("unit_release", name, str(version), str(revision)),
        name=name,
        version=version,
        revision=revision,
        interface="1",
    )
    records = [release]
    units = []
    for suffix in ("a", "b"):
        unit = Unit(
            id=make_id(Unit, (name, suffix)), key=(name, suffix), release=release.id, parent=None
        )
        document = _unit_document(unit.id, f"{name}-{suffix}-cover")
        records.extend([unit, document])
        units.append(unit.id)
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft), tuple(units), release.name


def _two_releases_of_one_name(*, name="cabinet"):
    """Two `UnitRelease` records sharing one NAME but at different `(version, revision)`, each
    with one `Unit` and one document (acceptance 5c): two names, no clash."""
    records = []
    for version, revision in ((2, 1), (1, 5)):
        release = UnitRelease(
            id=make_id(UnitRelease, ("unit_release", name, str(version), str(revision))),
            key=("unit_release", name, str(version), str(revision)),
            name=name,
            version=version,
            revision=revision,
            interface="1",
        )
        unit = Unit(
            id=make_id(Unit, (name, str(version), str(revision))),
            key=(name, str(version), str(revision)),
            release=release.id,
            parent=None,
        )
        document = _unit_document(unit.id, f"{name}-{version}-{revision}-cover")
        records.extend([release, unit, document])
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_a_units_document_names_the_same_from_its_own_write_and_a_system_write(tmp_path):
    """Acceptance 5a: the same document, written from inside its own unit's write and from a
    system write, gives byte-identical NAMES (the bytes themselves are Part 3/4's own diff)."""
    model, unit = _one_unit_with_document()
    result = BuildResult(model=model, findings=())
    own = {n for n in _names(fr.write(result, tmp_path / "own", unit=unit)) if n.endswith(".pdf")}
    system = {
        n for n in _names(fr.write(result, tmp_path / "system", unit=None)) if n.endswith(".pdf")
    }
    assert own == system == {"solo-cabinet-v1.1.pdf"}


def test_two_units_of_one_release_each_with_a_document_raise_with_the_keep_one_hint(tmp_path):
    """Acceptance 5b: two `Unit` instances of one `UnitRelease`, each the subject of its own
    document, land on one name and raise, the message carrying the "keep one document per
    release" hint with the release's own name."""
    model, _units, release_name = _two_units_of_one_release()
    with pytest.raises(ExportNameClash) as excinfo:
        fr.write(BuildResult(model=model, findings=()), tmp_path, unit=None)
    message = str(excinfo.value)
    assert "keep one document per release" in message
    assert release_name in message


def test_two_releases_of_one_name_at_different_revisions_do_not_clash(tmp_path):
    """Acceptance 5c: two releases that share one NAME but differ in `(version, revision)`
    give two distinct names and both write."""
    model = _two_releases_of_one_name()
    names = _names(fr.write(BuildResult(model=model, findings=()), tmp_path, unit=None))
    assert {"cabinet-v2.1.pdf", "cabinet-v1.5.pdf"} <= names


def test_a_system_documents_bare_name_does_not_borrow_a_units_release_hint(tmp_path):
    """Regression (review caught, EXPORT-NAMES Part 2): a `SYSTEM` document's bare name can
    coincidentally equal an unrelated unit's own release prefix (a `Project.number` that
    happens to match a `UnitRelease.name`, at the same version/revision) -- the resulting
    clash is an ORDINARY one (two unrelated subjects, not two instances of one release), so
    its message must NOT carry EN3's "keep one document per release" hint. Can-fail: gating
    the hint on "the document being added is unit-subject" alone (dropping the check that the
    OTHER, already-held name also came from a unit of that same release) makes this test fail
    -- the hint would wrongly appear."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Coincidence", number="cab", customer="C", revision=1, author="a")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    # `_ExportLedger.add` raises on the SECOND `Document` its own computed name reaches, and
    # only a buggy version's hint depends on which SIDE that second one is; a frozen model's
    # table order is content-determined (by `Id.value`, empirically -- not by merge argument
    # order, which does NOT affect it), so this stem is chosen to put the `SYSTEM` document's
    # `Id` before the unit document's `Id` (`cab-unit`, cover `"unit-cover"`), making the
    # SYSTEM document the HELD side and the unit document the one whose `.add()` call raises
    # -- the exact shape that exposed the bug (a probe with an arbitrary stem passed by luck).
    system_cover = tmp_path / "s57.md"
    system_cover.write_text("# System\n", encoding="utf-8")
    system_doc = fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover)

    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", "cab", "1", "1")),
        key=("unit_release", "cab", "1", "1"),
        name="cab",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(id=make_id(Unit, ("cab-unit",)), key=("cab-unit",), release=release.id, parent=None)
    unit_document = _unit_document(unit.id, "unit-cover")
    unit_draft = Draft()
    unit_draft.extend([release, unit, unit_document], origin=_ORIGIN)

    # `fr.build` runs every validator (including `REVISION_CURRENT_MISSING`, which this bare
    # hand-built release has no `Revision` entry to satisfy); this test only needs a frozen
    # model, the same bypass `_two_units_of_one_release` and friends already use above.
    model = freeze(merge(d.draft(), system_doc, unit_draft))
    result = BuildResult(model=model, findings=())
    with pytest.raises(ExportNameClash) as excinfo:
        fr.write(result, tmp_path / "out", unit=None)
    message = str(excinfo.value)
    assert "cab-v1.1.pdf" in message
    assert "keep one document per release" not in message


def test_a_unit_name_subject_document_is_still_named_by_its_own_release(tmp_path):
    """Regression (main merged in UNIT-NAME after this part's first draft, model-0094): a
    document's unit subject can now be authored as a release NAME (`Document.unit_name`,
    resolved through `derive.document_unit`) instead of a unit `Id` (`Document.unit`).
    `_document_export_name` must read the subject through `document_unit`, not bare
    `record.unit`, or a `unit_name`-subject document would silently fall through to the
    write-scope branches -- undetectable when the write happens to be scoped to that same
    unit (UNIT-NAME's own worked-example test does exactly that, so it cannot catch this), so
    this test deliberately writes with `unit=None` (a SYSTEM write, a different scope from
    the document's own unit) to tell the two branches apart. Can-fail: reverting
    `_document_export_name`'s unit branch to `record.unit is not None` makes this document's
    PDF fall through to the bare-cover-stem fallback instead of its own release prefix."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    u = d.scope("cab").unit("demo-unit", version=1, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-unit", cover=cover)

    result = fr.build(parts, d.draft(), document_draft)
    names = _names(fr.write(result, tmp_path / "out", unit=None))

    assert "demo-unit-v1.1.pdf" in names
    assert "cabinet.pdf" not in names
