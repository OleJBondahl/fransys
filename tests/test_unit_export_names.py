"""UNIT-ID I5 and acceptance 4 (files half) and 6: export names in a unit's folder.

A per-item export in a unit's folder is named from the item's designation printed for that unit
(`terminals-X2.csv`, no location path of the parent's); the unit's own root takes the bare kind
"""
# CONNECTION_NOT_DRAWN 4 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

import csv
import io
import tempfile
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys._export_ledger import ExportNameClashError
from fransys.pipeline import BuildResult
from fransys_author.design import Design

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by name.
from root_library import freeze
from test_units_worked_example import _system_design
from test_write_unit_worked_example import (
    _ALL_WRITE_FILES,
    _PUMP1_BOARD_WRITE_FILES,
    _PUMP1_WRITE_FILES,
    _unit_id,
)

from fransys_model.derive import (
    export_form_of,
    export_name,
    export_path,
    export_prefix,
    export_set,
    export_set_name,
    stale_patterns,
)
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab import (
    Item,
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
    d, _field1, _field2 = _system_design(parts, tags=("P1", "P2"))
    draft = d.draft()
    probe = fr.build(parts, draft, system_document()).model
    cabinet = _unit_id(probe, name="demo-pump-cabinet", prefix="pump1")
    board = _unit_id(probe, name="demo-io-board", prefix="pump1")
    covers = Path(tempfile.mkdtemp())
    for stem in ("cabinet", "board", "system"):
        (covers / f"{stem}.md").write_text(f"# {stem}\n", encoding="utf-8")
    documents = (
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=covers / "cabinet.md"),
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, board, cover=covers / "board.md"),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=covers / "system.md"),
        *(
            fr.document(preset, _unit_id(probe, name=name, prefix="pump2"), cover=covers / cover)
            for preset, name, cover in (
                (fr.DocumentPreset.CABINET_SCHEMATIC, "demo-pump-cabinet", "cabinet.md"),
                (fr.DocumentPreset.CABINET_SCHEMATIC, "demo-io-board", "board.md"),
            )
        ),
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


# CONNECTION_NOT_DRAWN 4 on the worked build is KI-305 (cut_ledger.account): anchored in docs/KNOWN-ISSUES.toml (designer R1526 Q2).

# -- the worked example's folders -------------------------------------------------------------


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
    assert "P-1001-v1.1-terminals-ER-C1-P1-X2.csv" in names
    assert not names & {"terminals-X2.csv", *_BARE_NAMES}


# -- acceptance 4, files half -----------------------------------------------------------------


def test_the_boards_folder_never_names_the_boards_own_tag(board_write, cabinet_write):
    written = board_write
    assert not any("U1" in p.name for p in written)
    by_name = {p.name: p for p in written}
    text_files = {name for name in by_name if not name.endswith(".pdf")}
    assert text_files == {
        "demo-io-board-v1.3-bom.csv",
        "demo-io-board-v1.3-cables.csv",
        "demo-io-board-v1.3-connectors.csv",
        "demo-io-board-v1.3-cores.csv",
        "demo-io-board-v1.3-designations.csv",
        "demo-io-board-v1.3-plc.csv",
        "demo-io-board-v1.3-wires.csv",
    }, "the loop below reads every text file the board unit writes, not a subset"
    for name in sorted(text_files):
        assert "-U1" not in by_name[name].read_text(encoding="utf-8"), name

    designations = {row["designation"] for row in _rows(by_name["demo-io-board-v1.3-designations.csv"])}
    assert designations == {"-K1", "-X1"}, "no row for the root board"

    # the same board still prints as `-U1` where the parent lists it
    parent = cabinet_write
    parent_bom = next(p for p in parent if p.name == "demo-pump-cabinet-v1.2-bom.csv")
    (unit_line,) = (row for row in _rows(parent_bom) if row["mpn"] == "demo-io-board")
    assert unit_line["designations"] == "-U1"


# -- own-root strip and rack; relative names of a non-root strip and rack ---------------------


def _wire_field_terminal(d, u, c1, grp, n=1):
    """A unit strip terminal on the boundary, wired to a top-level field motor; returns the field location.

    `n` numbers every tag when a design holds several such units (1 keeps the plain tags).
    """
    sfx = "" if n == 1 else str(n)
    terminal = u.strip(f"X{n}", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location(f"FLD{sfx}", "Field"), d.group(f"FLD{sfx}", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag=f"M{n}", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag=f"WM{n}", length_mm=15000).core(1, terminal.outer, motor["U"])
    return fld


def _unit_design(*, strip, rack):
    """A one-unit design whose roots are the requested strip and/or PLC rack."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    if strip:
        # a lone unwired terminal draws nothing (SET_WITHOUT_PAGE); wire it out across the
        # unit's boundary to a top-level motor, as the worked example's field terminals are
        _wire_field_terminal(d, u, c1, grp)
    if rack:
        rack_item = u.item(None, tag="U1", at=c1, group=grp)
        u.item("DEMO-PLC-DO-2", tag="DO1", name="do", parent=rack_item, position=1, at=c1, group=grp)
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
    (tmp_path / "data").mkdir()
    for name in stale:
        (tmp_path / name).write_text("stale", encoding="utf-8")
        (tmp_path / "data" / name).write_text("stale", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")

    written = _names(fr.write(result, tmp_path, unit=cabinet))

    assert not written & set(stale)
    remaining = {p.name for p in tmp_path.iterdir()}
    assert not remaining & set(stale)
    in_data = {p.name for p in (tmp_path / "data").iterdir()}
    assert not in_data & set(stale)
    assert "demo-pump-cabinet-v1.2-terminals-X2.csv" in in_data
    assert not [name for name in remaining if name.endswith((".csv", ".xml"))]
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
    with pytest.raises(ExportNameClashError, match=r"connectors-X1\.csv"):
        fr.write(BuildResult(model=model, findings=()), tmp_path, unit=unit)


def test_two_boards_with_distinct_relative_names_in_one_unit_folder_do_not_clash(tmp_path):
    model, unit = _two_boards_in_one_unit(("X1", "X2"))
    written = fr.write(BuildResult(model=model, findings=()), tmp_path, unit=unit)
    assert {"u-v1.1-connectors-X1.csv", "u-v1.1-connectors-X2.csv"} <= _names(written)


# -- EXPORT-NAMES Part 1: export_set_name, export_prefix, export_name's join -----------------


def test_export_set_name_and_prefix_are_empty_with_no_project_and_no_unit():
    """EN1: a system write of a model with no `Project` at all has no prefix."""
    model = freeze(Draft())
    assert export_set_name(model, None) == ""
    assert export_prefix(model, None) == ""


def test_export_set_name_and_prefix_for_the_system_use_the_projects_number_and_revision(worked):
    """EN1's system case, the spec's own worked numbers: `Project` number `P-1001`, version 1
    (defaulted, `_PROJECT` gives none), revision 1."""
    result, _cabinet, _board = worked
    assert export_set_name(result.model, None) == "P-1001"
    assert export_prefix(result.model, None) == "P-1001-v1.1"


def test_export_set_name_and_prefix_for_a_unit_use_its_own_release_not_the_project(worked):
    """EN1's unit case: the release's own name, version and revision, never the `Project`'s,
    even though this fixture's model has a `Project` (`P-1001-v1.1`) too."""
    result, cabinet, board = worked
    assert export_set_name(result.model, cabinet) == "demo-pump-cabinet"
    assert export_prefix(result.model, cabinet) == "demo-pump-cabinet-v1.2"
    assert export_set_name(result.model, board) == "demo-io-board"
    assert export_prefix(result.model, board) == "demo-io-board-v1.3"


def test_export_prefix_reads_the_projects_actual_version():
    """Every other fixture's `Project` defaults `version` to 1, which would let a bug that
    always read `.version` as 1 slip through unnoticed; this one overrides it to 2."""
    d = Design(fr.parts())
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
    assert export_prefix(result.model, None) == "P-1001-v2.1"


def test_export_prefix_for_a_unit_is_unaffected_by_a_missing_project():
    """EN1: 'a unit's document still takes its unit's prefix' -- a unit's prefix comes from
    its own release whether or not the model has a `Project` at all, unlike
    `test_export_set_name_and_prefix_for_a_unit_use_its_own_release_not_the_project`'s model,
    which does have one."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    u = d.scope("cab").unit("demo-unit", version=3, revision=4, interface="1")
    u.revision(4, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    _wire_field_terminal(d, u, c1, grp)
    result = fr.build(parts, d.draft(), system_document())
    assert export_set_name(result.model, u.unit_id) == "demo-unit"
    assert export_prefix(result.model, u.unit_id) == "demo-unit-v3.4"


def test_export_name_joins_prefix_kind_and_fragment(worked):
    """EN2: `export_name` joins whichever of prefix/kind/fragment is non-empty with `-`."""
    result, _cabinet, _board = worked
    model = result.model
    assert export_name(model, None, "pdf") == "P-1001-v1.1.pdf"
    assert export_name(model, None, "csv", kind="bom") == "P-1001-v1.1-bom.csv"
    assert export_name(model, None, "csv", kind="terminals", fragment="X2") == ("P-1001-v1.1-terminals-X2.csv")


def test_export_name_with_no_project_gives_todays_bare_names():
    """EN1's own escape hatch: an empty prefix leaves `export_name` at today's bare names."""
    model = freeze(Draft())
    assert export_name(model, None, "csv", kind="bom") == "bom.csv"
    assert export_name(model, None, "csv", kind="terminals", fragment="X1") == "terminals-X1.csv"


# -- EXPORT-NAMES Part 1, acceptance 2: stale exports removed by prefix (EN4) -----------------


def test_a_unit_write_removes_its_own_stale_export_and_keeps_the_current_revision(tmp_path):
    """Acceptance 2, unit-folder case (EN4's glob 1). The stale file is a CSV, not a PDF: the
    pre-EN `*.pdf` entry of `_STALE_EXPORT_PATTERNS` deletes every PDF regardless of glob 1,
    so a PDF-only assertion would pass even with glob 1 broken, proving nothing. The release
    is built at version 2, revision 1 (`2.1`), numerically *higher* than the stale file's
    """
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    u = d.scope("cab").unit("demo-unit", version=2, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    _wire_field_terminal(d, u, c1, grp)
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
    """
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
    d = Design(parts)
    d.project(title="t", number="EN3-1", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    fld = _wire_field_terminal(d, u, c1, grp)
    docs = tuple(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover) for cover in covers)
    kind = fr.DocumentPreset.CABINET_SCHEMATIC
    rest = (
        fr.document(kind, fld, cover=covers[0]),
        fr.document(kind, "demo-unit", cover=covers[0]),
    )
    return fr.build(parts, d.draft(), *docs, *rest)


def test_two_documents_with_one_location_subject_and_preset_raise(tmp_path):
    """Acceptance 3, first half: two documents that share one location subject and one preset
    compute the same name and raise, the message naming both cover stems (not merely raising)."""
    cover_a = tmp_path / "cover-a.md"
    cover_a.write_text("# A\n", encoding="utf-8")
    cover_b = tmp_path / "cover-b.md"
    cover_b.write_text("# B\n", encoding="utf-8")
    result = _location_document_design((cover_a, cover_b))
    with pytest.raises(ExportNameClashError) as excinfo:
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
    assert "EN3-1-v1.1-C1.pdf" in pdf_a, "the location document, plus the two sets' own"


def _no_project_unit_and_system_design(tmp_path):
    """A model with no `Project` at all, holding both a unit with its own `CABINET_SCHEMATIC`
    document and a top-level `SYSTEM` document (export-names EN1/EN3, acceptance 4)."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    u = d.scope("cab").unit("demo-unit", version=2, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    _wire_field_terminal(d, u, c1, grp)
    cabinet_cover = tmp_path / "cabinet.md"
    cabinet_cover.write_text("# Cabinet\n", encoding="utf-8")
    system_cover = tmp_path / "system.md"
    system_cover.write_text("# System\n", encoding="utf-8")
    docs = (
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, u, cover=cabinet_cover),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover),
    )
    return fr.build(parts, d.draft(), *docs)


def test_a_system_write_with_no_project_keeps_the_bare_cover_stem_and_names_the_units_document_by_its_release(tmp_path):
    """Acceptance 4a/4b: with no `Project`, the system's own document keeps today's bare `<cover-stem>.pdf` (through
    `export_name`'s own fallback), while the unit document is never bare: it takes its own release's prefix."""
    result = _no_project_unit_and_system_design(tmp_path)
    names = _names(fr.write(result, tmp_path / "out", unit=None))
    assert "system.pdf" in names
    assert "demo-unit-v2.1.pdf" in names
    assert "cabinet.pdf" not in names


# -- EXPORT-NAMES Part 2, acceptance 5: a unit document's name follows its unit's release -----


def _released_units_with_documents(tmp_path, releases, *, system_cover=None, project_number=None):
    """Build a design of one wired unit per `(scope, name, version, revision)` in `releases`, each the
    subject of its own `CABINET_SCHEMATIC` document, plus a `SYSTEM` document when `system_cover` is a stem."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    if project_number is not None:
        d.project(title="Coincidence", number=project_number, customer="C", revision=1, author="a")
        d.revision(1, date="2026-09-26", text="First issue", created="XX")
    documents = []
    units = []
    for n, (scope, name, version, revision) in enumerate(releases, start=1):
        u = d.scope(scope).unit(name, version=version, revision=revision, interface="1")
        u.revision(revision, date="2026-01-01", text="First release", created="XX")
        _wire_field_terminal(d, u, u.location(f"C{n}", "Cabinet"), u.group("PLC", "PLC"), n)
        cover = tmp_path / f"unit-{n}.md"
        cover.write_text(f"# {name} {n}\n", encoding="utf-8")
        documents.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, u, cover=cover))
        units.append(u)
    if system_cover is not None:
        cover = tmp_path / f"{system_cover}.md"
        cover.write_text("# System\n", encoding="utf-8")
        documents.append(fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    return fr.build(parts, d.draft(), *documents), tuple(units)


def test_a_units_document_names_the_same_from_its_own_write_and_a_system_write(tmp_path):
    """Acceptance 5a: the same document, written from inside its own unit's write and from a
    system write, gives byte-identical NAMES (the bytes themselves are Part 3/4's own diff)."""
    result, (unit,) = _released_units_with_documents(tmp_path, (("cab", "solo-cabinet", 1, 1),))
    own = {n for n in _names(fr.write(result, tmp_path / "own", unit=unit)) if n.endswith(".pdf")}
    system = {n for n in _names(fr.write(result, tmp_path / "system", unit=None)) if n.endswith(".pdf")}
    assert own == system == {"solo-cabinet-v1.1.pdf"}


def test_two_units_of_one_release_each_with_a_document_raise_with_the_keep_one_hint(tmp_path):
    """Acceptance 5b: two `Unit` instances of one `UnitRelease`, each the subject of its own
    document, land on one name and raise, the message carrying the "keep one document per
    release" hint with the release's own name."""
    result, _units = _released_units_with_documents(tmp_path, (("a", "shared-cabinet", 1, 1), ("b", "shared-cabinet", 1, 1)))
    with pytest.raises(ExportNameClashError) as excinfo:
        fr.write(result, tmp_path / "out", unit=None)
    message = str(excinfo.value)
    assert "EXPORT_NAME_CLASH (error): two units, both instances of release 'shared-cabinet', both export the file" in message
    assert "keep one document per release." in message


def test_two_releases_of_one_name_at_different_revisions_do_not_clash(tmp_path):
    """Acceptance 5c: two releases that share one NAME but differ in `(version, revision)`
    give two distinct names and both write."""
    result, _units = _released_units_with_documents(tmp_path, (("a", "cabinet", 2, 1), ("b", "cabinet", 1, 5)))
    names = _names(fr.write(result, tmp_path / "out", unit=None))
    assert {"cabinet-v2.1.pdf", "cabinet-v1.5.pdf"} <= names


def test_a_system_documents_bare_name_does_not_borrow_a_units_release_hint(tmp_path):
    """A `SYSTEM` bare name equal to an unrelated unit's release prefix is an ordinary clash, with no "keep one document per release" hint."""
    result, _units = _released_units_with_documents(tmp_path, (("cab", "cab", 1, 1),), system_cover="s57", project_number="cab")
    with pytest.raises(ExportNameClashError) as excinfo:
        fr.write(result, tmp_path / "out", unit=None)
    message = str(excinfo.value)
    assert "cab-v1.1.pdf" in message
    assert "keep one document per release" not in message


def test_a_unit_name_subject_document_is_still_named_by_its_own_release(tmp_path):
    """Regression (main merged in UNIT-NAME after this part's first draft, model-0094): a
    document's unit subject can now be authored as a release NAME (`Document.unit_name`,
    resolved through `derive.document_unit`) instead of a unit `Id` (`Document.unit`).
    `_document_export_name` must read the subject through `document_unit`, not bare
    """
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    u = d.scope("cab").unit("demo-unit", version=1, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    _wire_field_terminal(d, u, c1, grp)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-unit", cover=cover)

    result = fr.build(parts, d.draft(), document_draft)
    names = _names(fr.write(result, tmp_path / "out", unit=None))

    assert "demo-unit-v1.1.pdf" in names
    assert "cabinet.pdf" not in names


# -- EXPORT-NAMES (root 0117): `fr.export_names` is the naming rule `fr.write` uses -------------


def test_write_paths_are_out_dir_joined_with_export_names_for_the_whole_build(worked, tmp_path):
    result, _cabinet, _board = worked
    names = fr.export_names(result)
    assert fr.write(result, tmp_path) == tuple(sorted(tmp_path / name for name in names.values()))
    assert names[("bom", None)] == "data/P-1001-v1.1-bom.csv"
    assert {kind for kind, _subject in names} >= {"bom", "terminals", "pdf", "overview", "cables"}


def test_write_paths_are_out_dir_joined_with_export_names_for_a_unit(worked, tmp_path):
    result, cabinet, _board = worked
    names = fr.export_names(result, unit=cabinet)
    assert fr.write(result, tmp_path, unit=cabinet) == tuple(sorted(tmp_path / name for name in names.values()))
    assert ("overview", None) not in names


def test_export_names_refuses_a_bad_unit_like_write(worked):
    result, _cabinet, _board = worked
    with pytest.raises(ValueError, match="no-such-unit"):
        fr.export_names(result, unit="no-such-unit")


# -- RO-8 (model-0283): `derive.export_set` is the one table behind write and the stale sweep


def test_the_stale_patterns_are_the_exports_a_write_owns():
    assert set(stale_patterns()) == {
        "*.pdf",
        "bom.csv",
        "plc.csv",
        "wire*.csv",
        "designations.csv",
        "cables.csv",
        "cores.csv",
        "terminals-*.csv",
        "connectors-*.csv",
        "wago-*.xml",
        "terminals.csv",
        "connectors.csv",
        "wago.xml",
        "overview.html",
    }


def test_export_set_rows_are_the_names_write_gives_and_the_overview_is_whole_model_only(worked):
    result, cabinet, _board = worked
    model = result.model
    for unit in (None, cabinet):
        rows = export_set(model, unit)
        names = fr.export_names(result, unit=unit)
        assert {(r.export_kind, r.subject): export_path(export_form_of(model), r.name) for r in rows} == names
    system = export_set(model, None)
    assert [r.export_kind for r in system[:7]] == [
        "bom",
        "plc",
        "wires",
        "designations",
        "cables",
        "cores",
        "overview",
    ]
    assert system[0].name == "P-1001-v1.1-bom.csv"
    assert "overview" not in {r.export_kind for r in export_set(model, cabinet)}


def test_two_units_of_one_release_give_the_second_document_the_keep_one_hint(tmp_path):
    result, _units = _released_units_with_documents(tmp_path, (("a", "shared-cabinet", 1, 1), ("b", "shared-cabinet", 1, 1)))
    rows = [r for r in export_set(result.model, None) if r.export_kind == "pdf"]
    assert [r.hint for r in rows] == [None, "shared-cabinet"]
