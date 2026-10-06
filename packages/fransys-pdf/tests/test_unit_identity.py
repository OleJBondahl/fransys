"""UNIT-ID Part 2 (I2, I3, I4 heading): a unit's own set names only the unit.

Title block and PDF metadata read the unit's own title, number and revision date; a unit with no
title or number is reported; the connector and terminal list headings drop a unit's own root.
"""

from _build import (
    connector,
    document,
    item,
    location,
    model,
    part,
    pcb_facet,
    place,
    project,
    revision_entry,
    terminal,
    unit,
)
from fransys_pdf import check, source
from fransys_pdf._geometry import document_facts, document_metadata

from fransys_model.kernel import Severity
from fransys_model.vocab import DocumentPreset, PageKind, documents

K = PageKind
_CODE = "TITLE_BLOCK_UNIT_IDENTITY_MISSING"
_UNIT_DOCUMENT_REMOVE = (K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)


def _identity_model():
    """One project, one titled unit with its document, and the SYSTEM document of the project."""
    p = project(
        title="Two-pump station",
        number="EX-1",
        customer="Example works",
        revision=1,
        author="demo",
    )
    u = unit(
        "u1",
        name="relay-board",
        revision=1,
        title="Relay interface board",
        number="SKX-RIB-2",
    )
    entry = revision_entry("r1", unit=u, revision=1, date="2026-09-01")
    unit_doc = document(
        "d-unit",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        remove=_UNIT_DOCUMENT_REMOVE,
    )
    system_doc = document(
        "d-system",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        remove=(K.HARNESS_DRAWING, K.BOM),  # the system BOM's unit line prints the unit's title
    )
    project_entry = revision_entry("rp", unit=None, revision=1, date="2020-01-01")
    return model(p, u, entry, project_entry, unit_doc, system_doc), unit_doc, system_doc


def test_unit_document_facts_are_the_units_own_and_the_system_document_keeps_the_projects():
    """Acceptance 1 (facts). Can-fail: `document_facts` returning `project_facts` for a unit
    document gives `Two-pump station`, `EX-1`, `Example works`."""
    m, unit_doc, system_doc = _identity_model()
    assert document_facts(m, documents(m)[unit_doc.id]) == (
        "Relay interface board",
        "SKX-RIB-2",
        "",
        "1.1",
        "2026-09-01",
        "demo",
    )
    assert document_facts(m, documents(m)[system_doc.id]) == (
        "Two-pump station",
        "EX-1",
        "Example works",
        "1.1",
        "2020-01-01",
        "demo",
    )


def test_unit_document_title_block_prints_the_unit_and_none_of_the_project():
    """Acceptance 1 (Typst source): the unit's title and number are printed, the project's
    title, number and customer are not; the system document still prints the project's."""
    m, unit_doc, system_doc = _identity_model()
    unit_text = source(m, unit_doc.id, {})
    body = unit_text.split("\n", 1)[1]  # everything after the metadata line: the title-block cells
    assert '"Relay interface board"' in body
    assert '"SKX-RIB-2"' in body
    for project_text in ("Two-pump station", "EX-1", "Example works"):
        assert project_text not in unit_text
    system_text = source(m, system_doc.id, {})
    for project_text in ('"Two-pump station"', '"EX-1"', '"Example works"'):
        assert project_text in system_text
    for unit_only in ("Relay interface board", "SKX-RIB-2"):
        assert unit_only not in system_text


def test_unit_document_metadata_takes_the_units_title_and_revision_date():
    """Acceptance 2. Can-fail: `document_metadata` reading `project_facts` again puts
    `Two-pump station` and the project's 2020 date in the unit PDF's metadata."""
    m, unit_doc, system_doc = _identity_model()
    unit_text = source(m, unit_doc.id, {})
    assert unit_text.startswith('#set document(title: "Relay interface board"')
    assert "datetime(year: 2026, month: 9, day: 1)" in unit_text.split("\n", 1)[0]
    assert "2020" not in unit_text.split("\n", 1)[0]
    system_text = source(m, system_doc.id, {})
    assert system_text.startswith('#set document(title: "Two-pump station"')
    assert "datetime(year: 2020, month: 1, day: 1)" in system_text.split("\n", 1)[0]


def test_unit_whose_current_revision_has_no_history_entry_gives_date_none_in_the_metadata():
    """A unit revision with no `Revision` entry has an empty date: `date: none`, never the
    project's date. Can-fail: `document_metadata` reading `project_facts` gives 2020."""
    p = project()
    project_entry = revision_entry("rp", unit=None, revision=1, date="2020-01-01")
    u = unit("u1", name="board", revision=3, title="Relay board", number="X")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        remove=_UNIT_DOCUMENT_REMOVE,
    )
    m = model(p, project_entry, u, doc)
    metadata = document_metadata(m, documents(m)[doc.id])
    assert "date: none" in metadata
    assert "2020" not in metadata


def _identity_findings(*units):
    """The `TITLE_BLOCK_UNIT_IDENTITY_MISSING` findings of one unit document per `units`."""
    docs = tuple(
        document(
            f"d-{u.key[1]}",
            preset=DocumentPreset.CABINET_SCHEMATIC,
            subject=u,
            cover="# Cover",
            remove=_UNIT_DOCUMENT_REMOVE,
        )
        for u in units
    )
    m = model(project(), *units, *docs)
    return tuple(found for found in check(m, {}) if found.code == _CODE), docs


def test_missing_unit_number_gives_one_warning_naming_number_only():
    """Acceptance 3. Can-fail: removing the finding from `check` gives no finding."""
    findings, (doc,) = _identity_findings(unit("u1", name="board", title="Relay board"))
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert findings[0].subjects == (doc.id,)
    assert "number" in findings[0].message
    assert "title" not in findings[0].message


def test_missing_unit_title_gives_one_warning_naming_title_only():
    findings, _docs = _identity_findings(unit("u1", name="board", number="SKX-1"))
    assert len(findings) == 1
    assert "title" in findings[0].message
    assert "number" not in findings[0].message


def test_missing_title_and_number_give_one_warning_naming_both():
    findings, _docs = _identity_findings(unit("u1", name="board"))
    assert len(findings) == 1
    assert "title and number" in findings[0].message


def test_a_unit_with_title_and_number_gives_no_identity_finding():
    findings, _docs = _identity_findings(unit("u1", name="board", title="Relay board", number="X"))
    assert findings == ()


def test_a_system_document_gives_no_identity_finding():
    m, _unit_doc, _system_doc = _identity_model()
    assert [found for found in check(m, {}) if found.code == _CODE] == []
    system_only = model(project(), document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover"))
    assert [found for found in check(system_only, {}) if found.code == _CODE] == []


def test_two_unit_documents_missing_identity_give_two_findings_one_per_document():
    findings, docs = _identity_findings(unit("u1", name="board-a"), unit("u2", name="board-b"))
    assert len(findings) == len(docs)
    assert {found.subjects for found in findings} == {(doc.id,) for doc in docs}


def _board_model(*, second_root: bool):
    """A board `-JB1` of unit `b`, listed by the unit's own document and by a location document.

    `second_root` adds another root item to the unit, so the board is no longer its sole root.
    """
    c1 = location("C1", "Demo cabinet")
    u = unit("b", name="board-unit")
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id, unit=u.id)
    pcb = pcb_facet("board1", subject=board_part.id)
    j1 = connector("j1", item=board.id, name="J1", markings=("1",))
    unit_doc = document(
        "d-unit",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=u,
        cover="# Cover",
        remove=(K.SCHEMATIC, K.BOM),
    )
    parent_doc = document(
        "d-loc",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        remove=(K.SCHEMATIC, K.BOM),
    )
    extra = [item("k1", description="Second root", unit=u.id)] if second_root else []
    m = model(
        c1,
        u,
        board_part,
        board,
        pcb,
        place("p-board", item=board.id, node=c1.id),
        *j1[:4],
        *j1[4],
        unit_doc,
        parent_doc,
        *extra,
    )
    return m, unit_doc, parent_doc


_BOARD_ROW = 'text("-JB1"), text("header")'
_BOARD_HEADING = '#heading(level: 2, text("-JB1"))'


def test_connector_list_of_a_units_own_sole_root_board_has_no_heading_but_its_rows():
    """Acceptance 4 (PDF half). Can-fail: dropping the predicate from `connector_list_page`
    brings the `-JB1` heading back."""
    m, unit_doc, parent_doc = _board_model(second_root=False)
    unit_text = source(m, unit_doc.id, {})
    assert "#heading(level: 2" not in unit_text
    assert _BOARD_ROW in unit_text
    # the same board where it is placed (no unit): its heading stays
    assert _BOARD_HEADING in source(m, parent_doc.id, {})


def test_connector_list_of_a_board_that_is_not_the_units_sole_root_keeps_its_heading():
    m, unit_doc, _parent_doc = _board_model(second_root=True)
    unit_text = source(m, unit_doc.id, {})
    assert _BOARD_HEADING in unit_text
    assert _BOARD_ROW in unit_text


def _strip_model(*, second_root: bool):
    """A terminal strip `-X1` of unit `s`, listed by the unit's own and by a location document."""
    c1 = location("C1", "Demo cabinet")
    u = unit("s", name="strip-unit")
    strip = item("x1", description="Strip one", unit=u.id)
    child, facet = terminal("t1", strip=strip.id, group="L", index=1)
    unit_doc = document(
        "d-unit",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM),
    )
    parent_doc = document(
        "d-loc",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM),
    )
    extra = [item("k1", description="Second root", unit=u.id)] if second_root else []
    m = model(
        c1,
        u,
        strip,
        child,
        facet,
        place("p-strip", item=strip.id, node=c1.id),
        unit_doc,
        parent_doc,
        *extra,
    )
    return m, unit_doc, parent_doc


_STRIP_HEADING = '#heading(level: 2, text("-X1"))'
_STRIP_ROW = 'text("-X1:L:1")'  # the terminal's own row cell; the heading is `-X1` alone


def test_terminal_list_of_a_units_own_sole_root_strip_has_no_heading_but_its_table():
    """Acceptance 4 (PDF half, terminal strip). Can-fail: dropping the predicate from
    `terminal_list_page` brings the `-X1` heading back."""
    m, unit_doc, parent_doc = _strip_model(second_root=False)
    unit_text = source(m, unit_doc.id, {})
    assert "#heading(level: 2" not in unit_text
    assert _STRIP_ROW in unit_text
    assert _STRIP_HEADING in source(m, parent_doc.id, {})


def test_terminal_list_of_a_strip_that_is_not_the_units_sole_root_keeps_its_heading():
    m, unit_doc, _parent_doc = _strip_model(second_root=True)
    unit_text = source(m, unit_doc.id, {})
    assert _STRIP_HEADING in unit_text
    assert _STRIP_ROW in unit_text
