"""A blank cable end draws nothing; a title-block overflow finding names its remedy by field."""

from decimal import Decimal

from fransys_render._cable_ink import Ink
from fransys_render._cable_pen import Pen
from fransys_render.cables import _end
from fransys_render.sheet_check import _overflow

from electrical_symbols import LIBRARY
from fransys_layout import PlacedEnd
from fransys_model.kernel import make_id
from fransys_model.vocab import Document, Item


def test_a_blank_end_draws_no_box_label_or_cell() -> None:
    item = make_id(Item, ("item", "x"))
    end = PlacedEnd(
        item=item,
        top=True,
        dashed=False,
        blank=True,
        label="",
        x=0,
        y=0,
        width=40,
        height=16,
        cells=(),
    )
    ink = Ink(Pen(LIBRARY, module_mm=Decimal("2.5"), text_height_mm=Decimal("2.5"), pad_g=2, font_g=11))
    _end(ink, end)  # a blank end draws nothing
    assert ink.body() == ""


def test_only_a_page_title_overflow_points_at_the_block_text() -> None:
    subject = make_id(Document, ("document", "d"))
    page_title = _overflow(subject, "page_title", "p2", "A very long page title")
    assert page_title.code == "TITLE_BLOCK_TEXT_OVERFLOW"
    assert page_title.subjects == (subject,)
    assert page_title.message.endswith("; shorten the d.function text of a block the page draws")
    assert "'A very long page title'" in page_title.message
    title = _overflow(subject, "title", "p2", "Long")
    assert not title.message.endswith("d.function text of a block the page draws")
    assert title.message.endswith("cut with '…'")
