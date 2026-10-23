"""A blank cable end draws nothing; a title-block overflow finding names its remedy by field."""

from decimal import Decimal

from fransys_render._cable_ink import Ink
from fransys_render._cable_pen import Pen
from fransys_render.cables import _end
from fransys_render.sheet_check import _overflow
from render_library import freeze

from fransys_model.kernel import Draft, make_id
from fransys_model.layout import BlockRow, CableBlock, EndBox, EndStyle
from fransys_model.vocab import Document, Item


def test_a_blank_end_draws_no_box_label_or_cell() -> None:
    block_id = make_id(CableBlock, ("cable_block", "blank"))
    block = CableBlock(
        id=block_id,
        key=("cable_block", "blank"),
        subject=make_id(Item, ("item", "x")),
        unit=None,
        width=40,
        height=16,
        pitch=4,
        sheet_format=None,
        produced_by="test",
    )
    end = EndBox(
        id=make_id(EndBox, ("end_box", "blank")),
        key=("end_box", "blank"),
        block=block_id,
        item=make_id(Item, ("item", "x")),
        row=BlockRow.TOP,
        style=EndStyle.BLANK,
        x=0,
        y=0,
        width=40,
        height=16,
        pins=(),
        produced_by="test",
    )
    ink = Ink(Pen(module_mm=Decimal("2.5"), text_height_mm=Decimal("2.5"), pad_g=2))
    model = freeze(Draft())
    _end(model, ink, block, end)  # a blank end reads neither the model nor the block
    assert ink.body() == ""


def test_only_a_page_title_overflow_points_at_the_page_title_setting() -> None:
    subject = make_id(Document, ("document", "d"))
    page_title = _overflow(subject, "page_title", "p2", "A very long page title")
    assert page_title.code == "TITLE_BLOCK_TEXT_OVERFLOW"
    assert page_title.subjects == (subject,)
    assert page_title.message.endswith("; set a shorter title with d.layout.page_title")
    assert "'A very long page title'" in page_title.message
    title = _overflow(subject, "title", "p2", "Long")
    assert not title.message.endswith("d.layout.page_title")
    assert title.message.endswith("cut with '…'")
