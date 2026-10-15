"""EXACT-SIZES A1, A2 and A4 over the content of compiled PDFs; the symbol measures sit in
`test_exact_sizes_symbols_pdf`.

One small invented document carries a marked word in every text role (`HEKone` is a heading 1,
`HEKlabel` an SVG drawing label, `HEKtable` a revision-table cell, ...). The PDF is compiled
once and measured with `_pdf_measure`: the capital heights of H, E and K, the stroke widths,
and the fonts.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import fransys as fr
import fransys_author
import fransys_parts
import pytest
import typst
from _model_build_cover import system_document
from _pdf_measure import capital_boxes, font_names, stroke_widths, text_objects
from fransys_el import REF_TINTS
from fransys_pdf import font_dir, source
from fransys_pdf._frame import band_height_mm, title_columns
from fransys_render import pages
from test_units_worked_example import _system_design

from fransys_model.derive import unit_release
from fransys_model.derive.print_sizes import (
    LINE_RULE_MM,
    LINE_THICK_MM,
    LINE_THIN_MM,
    TextRole,
    role_height_mm,
)
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Orientation,
    Page,
    PageRole,
    SheetFormat,
    SymbolPlacement,
    default_profile,
    default_sheet_format,
    sheet_for,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Document,
    DocumentPreset,
    Function,
    FunctionKind,
    Item,
    PageKind,
    Port,
    PortRole,
    Project,
    Revision,
)
from fransys_model.vocab.tables import units as units_table

pytestmark = pytest.mark.wp("pdf")

_ORIGIN = Origin(file="tests/test_exact_sizes_pdf.py", line=1, note="invented")
_TOLERANCE_MM = 0.02  # the ink cross-check; the roles are 0.7 mm apart
_OBJECT_TOLERANCE_MM = 0.02  # a text object's font size times the ratio is exact to rounding
_HOUSE_MM = default_profile().text_height_mm


def _role(role: TextRole) -> float:
    return float(role_height_mm(role, _HOUSE_MM))


# Marked word -> the capital height (mm) its role prints at (EXACT-SIZES E3).
_ROLE_OF_WORD = {
    "HEKone": _role(TextRole.HEADING_1),
    "HEKtwo": _role(TextRole.HEADING_2),
    "HEKthree": _role(TextRole.BODY),
    "HEKbody": _role(TextRole.BODY),
    "HEKnotes": _role(TextRole.BODY),
    "HEKtitle": _role(TextRole.BODY),
    "HEKtable": _role(TextRole.LABEL),
    "HEKlabel": _role(TextRole.LABEL),
}
_SIZES_MM = {_role(role) for role in TextRole}


def _model(*, symbols: tuple[str, ...] = (), module_mm: str = "2.5"):
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
    item = Item(
        id=make_id(Item, ("item", "k1")),
        key=("item", "k1"),
        part=None,
        parent=None,
        position=None,
        tag="K1",
        description="Invented",
        installed=True,
    )
    function = Function(
        id=make_id(Function, ("function", "k1")),
        key=("function", "k1"),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port_key = ("function", "k1", "1")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=function.id,
        template=None,
        name="HEKlabel",
        role=PortRole.GENERIC,
    )
    label = Label(
        id=make_id(Label, ("label", "l1")),
        key=("label", "l1"),
        page=page.id,
        function=None,
        port=port.id,
        conductor=None,
        kind=LabelKind.MARKING,
        slot="",
        x=80,
        y=80,
        width=4,
        height=2,
        produced_by="test",
    )
    document = Document(
        id=make_id(Document, ("document", "d1")),
        key=("document", "d1"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=location.id,
        item=None,
        add=(),
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
        cover="# HEKone\n\n## HEKtwo\n\n### HEKthree\n\nHEKbody",
        notes="HEKnotes",
    )
    records = [
        location,
        project,
        revision,
        drawing_set,
        page,
        item,
        function,
        port,
        label,
        document,
        sheet,
    ]
    for number, symbol in enumerate(symbols):  # motor-3ph carries the only texts, "M" and "3"
        key = ("symbol_placement", f"s{number}")
        records.append(
            SymbolPlacement(
                id=make_id(SymbolPlacement, key),
                key=key,
                function=function.id,
                page=page.id,
                x=40 + 40 * number,
                y=160,
                orientation=Orientation.R0,
                poles=1,
                symbol=symbol,
                library_version="test",
                produced_by="test",
            )
        )
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft), document


def _compile(*, symbols: tuple[str, ...] = (), module_mm: str = "2.5") -> bytes:
    model, document = _model(symbols=symbols, module_mm=module_mm)
    text = source(model, document.id, pages(model, tints=REF_TINTS))
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
    assert {box.font.split("+")[-1] for box in capitals} == {"DejaVuSansCondensed"} or all(
        "DejaVu" in box.font for box in capitals
    )


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
    allowed = {round(float(w), 3) for w in (LINE_THIN_MM, LINE_THICK_MM, LINE_RULE_MM)}
    assert set(widths) <= allowed, widths
    assert round(float(LINE_THICK_MM), 3) in widths  # the frame border
    assert round(float(LINE_THIN_MM), 3) in widths  # the frame ticks
    assert round(float(LINE_RULE_MM), 3) in widths  # the revision table's rules


def _faces(pdf: bytes) -> set[str]:
    return {name.split("+")[-1] for name in font_names(pdf)}


def test_every_embedded_font_is_dejavu_sans_condensed(built_pdf):
    """A4, non-symbol half: every character is set in a DejaVu Sans Condensed face."""
    assert _faces(built_pdf) == {"DejaVuSansCondensed", "DejaVuSansCondensed-Bold"}


def test_a_symbol_text_is_dejavu_sans_condensed_too():
    """A4, symbol half: the motor symbol's "M" and "3" are set in the same face.

    With system fonts off, symdef's generic `sans-serif` resolves to the bundled face.
    """
    assert _faces(_compile(symbols=("motor-3ph",))) <= {
        "DejaVuSansCondensed",
        "DejaVuSansCondensed-Bold",
    }


def _on_a_role(cap_mm: float) -> bool:
    return any(abs(cap_mm - size) <= _OBJECT_TOLERANCE_MM for size in _SIZES_MM)


def test_every_text_object_of_the_invented_document_is_a_role_size(built_pdf):
    """A1: every text object, not only the marked words, prints a role size (font size x ratio)."""
    objects = text_objects(built_pdf)
    assert objects
    assert [o for o in objects if not _on_a_role(o.cap_mm)] == []
    assert {round(o.cap_mm, 1) for o in objects} == {1.8, 2.5, 3.5, 5.0}


def _unit_id(model, *, name, prefix):
    return next(
        unit_id
        for unit_id, unit in units_table(model).items()
        if unit_release(model, unit_id).name == name and unit.key[0] == prefix
    )


@pytest.fixture(scope="module")
def units_pdfs(tmp_path_factory) -> list[bytes]:
    """The units worked example written through the public API: its PDFs carry turned texts."""
    parts = fransys_parts.load("demo_parts")
    design, _, _ = _system_design(parts)
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
            fr.DocumentPreset.PCB_SCHEMATIC,
            _unit_id(probe, name="demo-io-board", prefix="pump1"),
            cover=covers / "board.md",
        ),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=covers / "system.md"),
    )
    written = fr.write(result, tmp_path_factory.mktemp("out"))
    return [path.read_bytes() for path in written if path.suffix == ".pdf"]


def test_every_text_object_of_a_multi_unit_set_is_a_role_size_turned_ones_too(units_pdfs):
    """A1 over three real documents: a turned text (a vertical reference, a cable core label)
    measures through its matrices like an upright one, because a matrix's scale is the length of
    its vertical column vector."""
    assert len(units_pdfs) == 3
    objects = [o for pdf in units_pdfs for o in text_objects(pdf)]
    assert any(o.turned for o in objects)
    assert [o for o in objects if not _on_a_role(o.cap_mm)] == []


def test_a_multi_unit_set_prints_only_the_line_widths_and_the_one_face(units_pdfs):
    """A2 and A4 over the same three documents, their symbols included."""
    allowed = {float(w) for w in (LINE_THIN_MM, LINE_THICK_MM, LINE_RULE_MM)}
    for pdf in units_pdfs:
        widths = stroke_widths(pdf)
        assert [w for w in widths if all(abs(w - one) > 0.005 for one in allowed)] == []
        assert _faces(pdf) <= {"DejaVuSansCondensed", "DejaVuSansCondensed-Bold"}


# A3, amended on the owner's answer A1: a profile's `text_height_mm` of 2.5 floors every page kind.
_PROFILE_MM = 2.5
_NOTICE = "Property of Demo Co. Do not copy."


def _profile_design():
    """One invented design at `text_height_mm` 2.5: a schematic page, a motor cable."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Invented", number="X-1", customer="Demo", revision=1, author="d")
    d.revision(1, date="2026-10-13", text="First issue", created="XX")
    d.profile(text_height_mm=Decimal(str(_PROFILE_MM)))
    c1 = d.location("C1", "Demo cabinet")
    supply, field = d.group("SUP", "Supply"), d.group("EXT", "Field")
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=supply)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=supply)
    d.wiring(colour="BU", gauge="0.75")(q1.fn("element")["2"], k1.fn("coil")["A1"])
    m0, m1 = (d.item("DEMO-MOTOR-4KW", tag=f"M{n}", group=field) for n in (0, 1))
    d.cable("DEMO-CBL-4G1.5", tag="W1").core(1, m0["U"], m1["U"])
    return parts, d.draft(), c1


@pytest.fixture(scope="module")
def profile_pdfs(tmp_path_factory) -> list[tuple[bytes, object]]:
    """A cabinet document (cover, notes, schematic, BOM) and a system one (cover, block diagram,
    cable drawing, cable list, BOM) at profile 2.5: `(pdf, model)` each."""
    parts, draft, c1 = _profile_design()
    folder = tmp_path_factory.mktemp("covers")
    (folder / "cabinet.md").write_text("# Cabinet\n\n## Sub\n\nBody.\n", encoding="utf-8")
    (folder / "cabinet.notes.md").write_text("Some notes.\n", encoding="utf-8")
    (folder / "system.md").write_text("# System\n\n## Sub\n\nBody.\n", encoding="utf-8")
    result = fr.build(
        parts,
        draft,
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=folder / "cabinet.md", notice=_NOTICE
        ),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=folder / "system.md", notice=_NOTICE),
    )
    written = fr.write(result, tmp_path_factory.mktemp("out"))
    return [(path.read_bytes(), result.model) for path in written if path.suffix == ".pdf"]


def test_a_profile_text_height_is_the_smallest_text_of_every_page_kind(profile_pdfs):
    """A3: nothing prints under 2.5 mm capitals, on a schematic page, a block diagram, a cable
    drawing's core labels, the lists, the cover, the notes and every title block; the 3.5 and 5
    roles stay."""
    assert len(profile_pdfs) == 2
    objects = [o for pdf, _model in profile_pdfs for o in text_objects(pdf)]
    assert [(o.text, round(o.cap_mm, 2)) for o in objects if o.cap_mm < _PROFILE_MM - 0.02] == []
    assert {round(o.cap_mm, 1) for o in objects} == {2.5, 3.5, 5.0}
    assert any(o.turned for o in objects)  # a turned core label measured like an upright text


def _title_block_cells(sheet):
    """The title block's cells, `(left, bottom, right, top)` mm with y up, as `_title_block` sets
    them: row 1 is a three-column title then four columns, row 2 six columns, the notice and the
    logo each span both rows."""
    cols = title_columns(sheet, notice=True)  # this test's documents all carry a notice
    edge = [sheet.content_x_mm + sum(cols[:i]) for i in range(len(cols) + 1)]
    low, mid = sheet.content_y_mm, sheet.content_y_mm + band_height_mm(sheet) / 2
    high = sheet.content_y_mm + band_height_mm(sheet)
    row1 = [(edge[0], edge[3])] + [(edge[i], edge[i + 1]) for i in (3, 4, 5)]
    row2 = [(edge[i], edge[i + 1]) for i in range(6)]
    spans = [(edge[6], edge[7]), (edge[7], edge[8])]
    return (
        [(left, mid, right, high) for left, right in row1]
        + [(left, low, right, mid) for left, right in row2]
        + [(left, low, right, high) for left, right in spans]
    )


def _page_sheet(model, width_mm):
    house = default_sheet_format()
    return house if abs(width_mm - house.width_mm) < 1 else sheet_for(model, PageKind.BLOCK_DIAGRAM)


def test_every_title_block_text_stays_inside_its_cell_at_a_larger_profile(profile_pdfs):
    """A3: each text object inside the title block band has its whole box inside the cell that
    holds its centre, vertically and horizontally, at profile 2.5 (nothing shrinks)."""
    tolerance, seen = 0.05, 0
    for pdf, model in profile_pdfs:
        for o in text_objects(pdf):
            sheet = _page_sheet(model, o.page_mm[0])
            left, bottom, right, top = o.bounds_mm
            cx, cy = (left + right) / 2, (bottom + top) / 2
            low = sheet.content_y_mm
            if not (low < cy < low + band_height_mm(sheet) and sheet.content_x_mm < cx):
                continue
            if cx > sheet.width_mm - sheet.content_x_mm:
                continue
            cell = next(
                c for c in _title_block_cells(sheet) if c[0] < cx < c[2] and c[1] < cy < c[3]
            )
            inside = (
                left >= cell[0] - tolerance
                and right <= cell[2] + tolerance
                and bottom >= cell[1] - tolerance
                and top <= cell[3] + tolerance
            )
            assert inside, (o.text, o.bounds_mm, cell)
            seen += 1
    assert seen > 40  # the labels, the values, the notice and the page counter of every page
