"""`check` stops a cable block too big for the page body (CD8, Q7, pdf-0022, acceptance 15).

A block is laid out in grid units and scaled to mm by its own sheet; the page body is the
document's sheet minus the run's frame. The house sheet (A3, content 410 x 267 mm, module 2.5 mm)
leaves a 400 x 246 mm body, which is 1280 x 787 G. Hand-built `CableBlock` records stand in for
the layout engine. The missing-SVG finding (acceptance 16) is in `test_checks.py`.
"""

from dataclasses import replace
from decimal import Decimal

from _build import (
    cable_facet,
    cable_product_facet,
    document,
    item,
    model,
    part,
    project,
    sheet_format,
)
from fransys_pdf import check

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import Severity, make_id
from fransys_model.layout import CableBlock
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_BODY_G = (1280, 787)  # the house sheet's page body in grid units
_SVG = "<svg>block</svg>"


def _findings(width: int, height: int, *, sheet_module_mm: Decimal | None = None):
    """The `DOCUMENT_NO_DRAWINGS` findings of one lone cable whose block is `width` x `height` G.

    With `sheet_module_mm` the block names its own authored sheet of that module, so its grid is
    scaled differently from the house sheet the document is drawn on.
    """
    harness = item("wh1", description="Demo harness")
    cable_part = part("w1", description="Cable one part")
    cable = item("w1", description="Cable one", parent=harness.id, part=cable_part.id)
    own_sheet = None
    if sheet_module_mm is not None:
        own_sheet = replace(
            sheet_format("own", width_mm=420, height_mm=297), module_mm=sheet_module_mm
        )
    key = ("layout", "cable-engine", "cable_block", "w1")
    block = CableBlock(
        id=make_id(CableBlock, key),
        key=key,
        subject=cable.id,
        unit=None,
        width=width,
        height=height,
        pitch=4,
        sheet_format=None if own_sheet is None else own_sheet.id,
        produced_by="test",
    )
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        remove=(K.CONTENTS, K.BOM),
    )
    records = [
        harness,
        cable,
        cable_facet("w1", subject=cable.id, length_mm=None),
        cable_part,
        cable_product_facet("w1", subject=cable_part.id, core_count=0),
        block,
        doc,
        *([own_sheet] if own_sheet is not None else []),
    ]
    m = model(project(), *records)
    svgs = {cable_block_key(None, cable.id): _SVG}
    return [f for f in check(m, svgs) if f.code == "DOCUMENT_NO_DRAWINGS"]


def test_a_block_that_fills_the_page_body_exactly_gives_no_finding() -> None:
    """The clean twin: 1280 x 787 G is 400 x 246 mm (to the grid unit)."""
    assert _findings(*_BODY_G) == []


def test_a_block_wider_than_the_page_body_is_an_error() -> None:
    """One grid unit over the body width: the ERROR names the block's key and both sizes."""
    (finding,) = _findings(_BODY_G[0] + 1, 10)
    assert finding.severity is Severity.ERROR
    assert finding.message.startswith("HARNESS_DRAWING: block ")
    assert "1281 x 10 G" in finding.message
    assert "1280 x 787 G" in finding.message


def test_a_block_taller_than_the_page_body_is_an_error() -> None:
    """One grid unit over the body height."""
    (finding,) = _findings(10, _BODY_G[1] + 1)
    assert finding.severity is Severity.ERROR
    assert "10 x 788 G" in finding.message


def test_a_block_is_scaled_by_its_own_sheet_not_the_documents() -> None:
    """A block on a 5 mm-module sheet: 640 G is 400 mm and fits the 400 mm body, 641 G does not,
    though both are under the 1280 G the house sheet's module would allow.
    """
    assert _findings(640, 10, sheet_module_mm=Decimal(5)) == []
    (finding,) = _findings(641, 10, sheet_module_mm=Decimal(5))
    assert "641 x 10 G" in finding.message
    assert "the page body holds 640 x 393 G" in finding.message
