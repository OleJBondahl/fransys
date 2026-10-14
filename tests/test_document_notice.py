"""DOCUMENT-NOTICE A1/A5: a unit-only design prints the notice and logo on every page.

The engineering shape: one unit released alone, with no `d.project`. Its documents carry the IP
notice and the logo; the release has one subject. With a `d.project` beside it, the unit's
Author cell is the unit revision's `created`, the project's document keeps the project's author.
Decisions model-0225, pdf-0036, root 0193.
"""

import fransys as fr
import fransys_author
import fransys_parts
import pypdfium2 as pdfium
from pypdfium2 import raw

from fransys_model.vocab import PageKind, projects, unit_releases

NOTICE = "(c) Demo AS"
LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<rect width="10" height="10" fill="#f00"/></svg>'
)


def _build(tmp_path, *, notice: str, logo: bool, project: bool = False):
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    if project:
        d.project(title="Station", number="P-1", customer="Demo", revision=1, author="XYQ")
        d.revision(1, date="2026-01-01", text="First issue", created="XYQ")
    u = d.scope("cab").unit("demo-unit", version=1, revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="ABQ")
    c1 = u.location("C1", "Cabinet")
    grp = u.group("PLC", "PLC")
    terminal = u.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    u.boundary(terminal)
    fld, fld_grp = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    d.cable("DEMO-CBL-4G1.5", tag="WM1", length_mm=15000).core(1, terminal.outer, motor["U"])
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    logo_path = None
    if logo:
        logo_path = tmp_path / "logo.svg"
        logo_path.write_text(LOGO, encoding="utf-8")
    documents = [
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            "demo-unit",
            cover=cover,
            remove=(PageKind.SCHEMATIC,),
            notice=notice,
            logo=logo_path,
        )
    ]
    if project:
        system_cover = tmp_path / "system.md"
        system_cover.write_text("# System\n", encoding="utf-8")
        documents.append(
            fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover, notice=notice)
        )
    result = fr.build(parts, d.draft(), *documents)
    out = tmp_path / "out"
    unit_pdf = [p for p in fr.write(result, out, unit=u) if p.suffix == ".pdf"]
    system_pdf = [
        p
        for p in fr.write(result, out, unit=None)
        if p.suffix == ".pdf" and p.name.startswith("P-1")
    ]
    return result, unit_pdf, system_pdf


def _page_texts(pdf: bytes) -> list[str]:
    return [page.get_textpage().get_text_range() for page in pdfium.PdfDocument(pdf)]


def _images_per_page(pdf: bytes) -> list[int]:
    return [
        sum(obj.type == raw.FPDF_PAGEOBJ_IMAGE for obj in page.get_objects(max_depth=8))
        or sum(obj.type == raw.FPDF_PAGEOBJ_PATH for obj in page.get_objects(max_depth=8))
        for page in pdfium.PdfDocument(pdf)
    ]


def test_a_unit_only_release_prints_the_notice_and_logo_on_every_page(tmp_path):
    """A1: more than one page, each with the notice text; one release subject, no project."""
    result, unit_pdf, _system = _build(tmp_path, notice=NOTICE, logo=True)
    assert projects(result.model) == {}
    assert len(unit_releases(result.model)) == 1
    (pdf,) = unit_pdf
    texts = _page_texts(pdf.read_bytes())
    assert len(texts) > 1
    assert [NOTICE in text for text in texts] == [True] * len(texts)
    assert min(_images_per_page(pdf.read_bytes())) >= 1


def test_without_the_notice_no_page_has_it(tmp_path):
    """The positive control: the same design with no notice prints none."""
    _result, (pdf,), _system = _build(tmp_path, notice="", logo=False)
    assert not any(NOTICE in text for text in _page_texts(pdf.read_bytes()))


def test_a_unit_page_prints_the_unit_revisions_created_and_a_project_page_the_author(tmp_path):
    """A5: the unit's Author cell is its revision's `created`; the system's is the project's."""
    _result, (unit_pdf,), (system_pdf,) = _build(tmp_path, notice=NOTICE, logo=False, project=True)
    unit_texts = _page_texts(unit_pdf.read_bytes())
    system_texts = _page_texts(system_pdf.read_bytes())
    assert all("ABQ" in text and "XYQ" not in text for text in unit_texts)
    assert all("XYQ" in text and "ABQ" not in text for text in system_texts)
