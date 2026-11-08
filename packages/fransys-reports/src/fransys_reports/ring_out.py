"""The ring-out sheet: one document's joins as an Excel workbook an electrician marks on a phone (R2008)."""

import datetime as dt
import io
from typing import TYPE_CHECKING

import xlsxwriter

from fransys_model.derive import ring_out_cells, ring_out_headers, ring_out_rows, ring_out_statuses, ring_out_title, ring_out_words

if TYPE_CHECKING:
    from xlsxwriter.format import Format
    from xlsxwriter.workbook import Workbook
    from xlsxwriter.worksheet import Worksheet

    from fransys_model.derive import DocumentId, RingOutRow, RingOutWords
    from fransys_model.kernel import Model

_CREATED = dt.datetime(2000, 1, 1, tzinfo=dt.UTC)  # fixed: the same model gives the same bytes
_WIDTHS = (5, 8, 24, 24, 14, 9, 7, 10, 12, 26, 26)
_HEADER_ROW, _STATUS_COLUMN, _EXTRA_ROWS = 1, 8, 20


def _status_rules(sheet: Worksheet, first: int, last: int, words: RingOutWords, formats: tuple[Format, Format]) -> None:
    """The Status dropdown and its colours on rows `first` to `last`."""
    column = _STATUS_COLUMN
    sheet.data_validation(first, column, last, column, {"validate": "list", "source": list(ring_out_statuses(words))})
    for word, fmt in zip(ring_out_statuses(words), formats, strict=False):
        sheet.conditional_format(first, column, last, column, {"type": "cell", "criteria": "==", "value": f'"{word}"', "format": fmt})


def _write_rows(sheet: Worksheet, rows: tuple[RingOutRow, ...], words: RingOutWords, wrap: Format) -> int:
    """Rows from the line under the header; the line after the last one."""
    for line, row in enumerate(rows, _HEADER_ROW + 1):
        for column, value in enumerate(ring_out_cells(row, line - _HEADER_ROW, words)):
            sheet.write(line, column, value, wrap)
    return _HEADER_ROW + 1 + len(rows)


def ring_out_xlsx(model: Model, document: DocumentId) -> bytes:
    """Write `document`'s ring-out sheet as an `.xlsx`: every wire, core and bridge to measure, line by line.

    One sheet: a title row (the document's name and the revision), a frozen, filtered header, then the
    wires, the cores and the bridges in their derive homes' order, each with a `Type` column. `Status`
    is a dropdown (OK green, Wrong red, empty is not tested); `Found instead` and `Comment` are free
    text; 20 empty lines headed "Found, not on drawing" follow for joins the drawing lacks. Every word
    is a `[words]` key (`ring_*`). The created date is fixed, so the same model gives the same bytes.

    Raises:
        KeyError: `document` names no document of `model`.
        SchemaError: a word key is absent from `[words]`.
    """
    words, rows = ring_out_words(model), ring_out_rows(model, document)
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {"in_memory": True})
    book.set_properties({"created": _CREATED})
    _fill(book, ring_out_title(model, document), rows, words)
    book.close()
    return buffer.getvalue()


def _fill(book: Workbook, title: str, rows: tuple[RingOutRow, ...], words: RingOutWords) -> None:
    """The one sheet: title, header, rows, extra block and Status rules."""
    sheet = book.add_worksheet(words.sheet)
    bold, wrap = book.add_format({"bold": True, "text_wrap": True}), book.add_format({"text_wrap": True, "valign": "top"})
    formats = (book.add_format({"bg_color": "#C6EFCE"}), book.add_format({"bg_color": "#FFC7CE"}))
    sheet.write(0, 0, title, bold)
    for column, (head, width) in enumerate(zip(ring_out_headers(words), _WIDTHS, strict=True)):
        sheet.write(_HEADER_ROW, column, head, bold)
        sheet.set_column(column, column, width, wrap)
    end = _write_rows(sheet, rows, words, wrap)
    sheet.freeze_panes(_HEADER_ROW + 1, 0)
    sheet.autofilter(_HEADER_ROW, 0, max(end - 1, _HEADER_ROW), len(_WIDTHS) - 1)
    sheet.write(end + 1, 0, words.extra, bold)
    _status_rules(sheet, _HEADER_ROW + 1, end + 1 + _EXTRA_ROWS, words, formats)
