"""EXACT-SIZES A1, A2 and A4 over the content of compiled PDFs.

One small invented document carries a marked word in every text role (`HEKone` is a heading 1,
`HEKtable` a revision-table cell, ...). The PDF is compiled
"""
# CONNECTION_NOT_DRAWN 4 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import fransys as fr
import fransys_parts
import fransys_render
import pytest
import typst
from _model_build_cover import system_document
from _pdf_lists import source
from _pdf_measure import capital_boxes, font_names, stroke_widths, text_objects
from root_library import freeze, role_height_mm
from symdef import Weight
from test_nested_unit_lists import _unit_id
from test_units_worked_example import _system_design

from electrical_symbols import LIBRARY, font_dir
from fransys_model.derive import document_sheets_of
from fransys_model.derive.print_sizes import TextRole
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.layout import (
    DrawingSet,
    Page,
    PageRole,
    SheetFormat,
    default_sheet_format,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Document,
    DocumentPreset,
    Project,
    Revision,
)

pytestmark = pytest.mark.wp("pdf")

_ORIGIN = Origin(file="tests/test_exact_sizes_pdf.py", line=1, note="invented")
_TOLERANCE_MM = 0.02  # the ink cross-check; the roles are 0.7 mm apart
_OBJECT_TOLERANCE_MM = 0.02  # a text object's font size times the ratio is exact to rounding


def _role(role: TextRole) -> float:
    return float(role_height_mm(role))


# Marked word -> the capital height (mm) its role prints at (EXACT-SIZES E3).
_ROLE_OF_WORD = {
    "HEKone": _role(TextRole.HEADING_1),
    "HEKtwo": _role(TextRole.HEADING_2),
    "HEKthree": _role(TextRole.BODY),
    "HEKbody": _role(TextRole.BODY),
    "HEKnotes": _role(TextRole.BODY),
    "HEKtitle": _role(TextRole.BODY),
    "HEKtable": _role(TextRole.LABEL),
}
_SIZES_MM = {_role(role) for role in TextRole}


def _model(*, module_mm: str = "2.5"):
    draft = Draft()
    location = AspectNode(
        id=make_id(AspectNode, ("location", "c1")),
        key=("location", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="Demo cabinet",
    )
    project = Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="HEKtitle",
        number="DEMO-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    revision = Revision(
        id=make_id(Revision, ("revision", "r1")),
        key=("revision", "r1"),
        release=None,
        version=1,
        revision=1,
        date="2026-09-22",
        text="HEKtable",
        created="XX",
    )
    sheet = replace(default_sheet_format(), key=("sheet", "s1"), module_mm=Decimal(module_mm))
    sheet = replace(sheet, id=make_id(SheetFormat, sheet.key))
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", "ds1")),
        key=("drawing_set", "ds1"),
        location=location.id,
        number=1,
        produced_by="test",
    )
    page = Page(
        id=make_id(Page, ("page", "p1")),
        key=("page", "p1"),
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=sheet.id,
        groups=(),
        produced_by="test",
    )
    document = Document(
        id=make_id(Document, ("document", "d1")),
        key=("document", "d1"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=location.id,
        item=None,
        cover="# HEKone\n\n## HEKtwo\n\n### HEKthree\n\nHEKbody",
        notes="HEKnotes",
    )
    records = [
        location,
        project,
        revision,
        drawing_set,
        page,
        document,
        sheet,
    ]
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft), document


def _compile(*, module_mm: str = "2.5") -> bytes:
    model, document = _model(module_mm=module_mm)
    text = source(
        model,
        document.id,
        {},
        fransys_render.sheets(document_sheets_of(model, ()), LIBRARY),
    )
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    pdf = compiler.compile(input=text.encode("utf-8"), format="pdf")
    assert isinstance(pdf, bytes)
    return pdf


@pytest.fixture(scope="module")
def built_pdf() -> bytes:
    return _compile()


@pytest.fixture(scope="module")
def capitals(built_pdf):
    return capital_boxes(built_pdf)


def test_every_marked_word_was_found_and_set_in_dejavu(capitals):
    assert {box.word for box in capitals} >= set(_ROLE_OF_WORD)
    assert {box.font.split("+")[-1] for box in capitals} == {"DejaVuSansCondensed"} or all("DejaVu" in box.font for box in capitals)


@pytest.mark.parametrize("word", sorted(_ROLE_OF_WORD))
def test_a_word_prints_its_roles_capital_height(capitals, word):
    """A1: each H, E, K of the word is as tall as its role says, to the measuring scale."""
    mine = [box for box in capitals if box.word == word]
    assert mine, word
    expected = _ROLE_OF_WORD[word]
    for box in mine:
        assert box.ink_mm == pytest.approx(expected, abs=_TOLERANCE_MM), (word, box)


def test_every_capital_is_one_of_the_four_sizes(capitals):
    """A1: the frame letters and the title-block cells too, whatever their word."""
    for box in capitals:
        assert any(box.ink_mm == pytest.approx(size, abs=_TOLERANCE_MM) for size in _SIZES_MM), box


def test_each_of_the_four_sizes_is_present(capitals):
    printed = {round(box.ink_mm, 1) for box in capitals}
    assert {1.8, 2.5, 3.5, 5.0} <= printed


def test_every_stroke_is_one_of_the_line_widths(built_pdf):
    """A2: stroke widths, composed through every matrix, are the three line roles."""
    widths = stroke_widths(built_pdf)
    allowed = {round(float(w), 3) for w in LIBRARY.lines.values()}
    assert set(widths) <= allowed, widths
    assert round(float(LIBRARY.lines[Weight.THICK]), 3) in widths  # the frame border
    assert round(float(LIBRARY.lines[Weight.NORMAL]), 3) in widths  # the frame ticks
    assert round(float(LIBRARY.lines[Weight.RULE]), 3) in widths  # the revision table's rules


def _faces(pdf: bytes) -> set[str]:
    return {name.split("+")[-1] for name in font_names(pdf)}


def test_every_embedded_font_is_dejavu_sans_condensed(built_pdf):
    """A4, non-symbol half: every character is set in a DejaVu Sans Condensed face."""
    assert _faces(built_pdf) == {"DejaVuSansCondensed", "DejaVuSansCondensed-Bold"}


def _on_a_role(cap_mm: float) -> bool:
    return any(abs(cap_mm - size) <= _OBJECT_TOLERANCE_MM for size in _SIZES_MM)


def test_every_text_object_of_the_invented_document_is_a_role_size(built_pdf):
    """A1: every text object, not only the marked words, prints a role size (font size x ratio)."""
    objects = text_objects(built_pdf)
    assert objects
    assert [o for o in objects if not _on_a_role(o.cap_mm)] == []
    assert {round(o.cap_mm, 1) for o in objects} == {1.8, 2.5, 3.5, 5.0}


@pytest.fixture(scope="module")
def units_pdfs(tmp_path_factory) -> list[bytes]:
    """The units worked example written through the public API: its PDFs carry turned texts."""
    parts = fransys_parts.load("demo_parts")
    design, _, _ = _system_design(parts, tags=("P1", "P2"))
    draft = design.draft()
    probe = fr.build(parts, draft, system_document()).model
    covers = tmp_path_factory.mktemp("covers")
    for name in ("cabinet", "board", "system"):
        (covers / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    result = fr.build(
        parts,
        draft,
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            _unit_id(probe, name="demo-pump-cabinet", prefix="pump1"),
            cover=covers / "cabinet.md",
        ),
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            _unit_id(probe, name="demo-io-board", prefix="pump1"),
            cover=covers / "board.md",
        ),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=covers / "system.md"),
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            _unit_id(probe, name="demo-pump-cabinet", prefix="pump2"),
            cover=covers / "cabinet.md",
        ),
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            _unit_id(probe, name="demo-io-board", prefix="pump2"),
            cover=covers / "board.md",
        ),
    )
    written = fr.write(result, tmp_path_factory.mktemp("out"))
    return [path.read_bytes() for path in written if path.suffix == ".pdf"]


def test_every_text_object_of_a_multi_unit_set_is_a_role_size_turned_ones_too(units_pdfs):
    """A1 over five real documents: a turned text (a vertical reference, a cable core label)
    measures through its matrices like an upright one, because a matrix's scale is the length of
    its vertical column vector."""
    assert len(units_pdfs) == 5
    objects = [o for pdf in units_pdfs for o in text_objects(pdf)]
    assert any(o.turned for o in objects)
    assert [o for o in objects if not _on_a_role(o.cap_mm)] == []


def test_a_multi_unit_set_prints_only_the_line_widths_and_the_one_face(units_pdfs):
    """A2 and A4 over the same five documents, their symbols included."""
    allowed = {float(w) for w in LIBRARY.lines.values()}
    for pdf in units_pdfs:
        widths = stroke_widths(pdf)
        assert [w for w in widths if all(abs(w - one) > 0.005 for one in allowed)] == []
        assert _faces(pdf) <= {"DejaVuSansCondensed", "DejaVuSansCondensed-Bold"}
