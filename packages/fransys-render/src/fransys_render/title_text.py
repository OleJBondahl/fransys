"""The title block's printed text: width, cut, one-line fields, the wrapped notice (render-0019).

Moved from `fransys_model.derive` (CC1, model-0373): it measures, so it sits beside symdef. The
callers pass the room (mm) a cell offers.
"""

from typing import TYPE_CHECKING, Protocol

import symdef
from symdef import Weight

from electrical_symbols import LIBRARY
from fransys_model.derive import FieldOverflow, TitleBlockOverflow, TitleBlockStrings

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.derive import (
        DocumentSheets,
        FieldForms,
        SheetIndexRow,
        Sizes,
        TitleBlockFields,
    )

__all__ = [
    "field_printed",
    "index_titles",
    "notice_line_count",
    "notice_pitch_mm",
    "notice_room_chars",
    "notice_unfit",
    "title_block_overflows",
    "title_block_strings",
]

_NOTICE_LINE_EM = 1.2  # the notice's line pitch in em

# the cell whose `TitleBlockFields` field has another name (`sheet_counter` fills `sheet`)
_FIELD_OF_CELL = {"sheet": "sheet_counter"}
# the cell pdf fills with the page counter: it holds no field of `TitleBlockFields`
_COUNTER_CELL = "page"


def text_width_mm(text: str, *, size_mm: float, bold: bool = False) -> float:
    """The width of `text` set `size_mm` high in the library font, regular or bold."""
    return symdef.text_width(LIBRARY.font, text, size_mm, Weight.THICK if bold else Weight.NORMAL)


def fits(text: str, *, size_mm: float, bold: bool = False, width_mm: float) -> bool:
    """Whether `text` set at `size_mm` (bold or not) is no wider than `width_mm`."""
    return text_width_mm(text, size_mm=size_mm, bold=bold) <= width_mm


def cut_to_width(text: str, *, ellipsis: str, size_mm: float, bold: bool = False, width_mm: float) -> tuple[str, bool]:
    """`(shown, was_cut)`: `text` if it fits, else cut by character plus `ellipsis`."""
    if fits(text, size_mm=size_mm, bold=bold, width_mm=width_mm):
        return text, False
    ellipsis_width = text_width_mm(ellipsis, size_mm=size_mm, bold=bold)
    budget = width_mm - ellipsis_width
    kept = ""
    for ch in text:
        candidate = kept + ch
        if text_width_mm(candidate, size_mm=size_mm, bold=bold) > budget:
            break
        kept = candidate
    return kept + ellipsis, True


def one_line_field(
    preferred: str,
    *,
    size_mm: float,
    bold: bool = False,
    width_mm: float,
    shorter: tuple[str, ...] = (),
) -> tuple[str, bool]:
    """`(text, fits)`: the first of `preferred` and `shorter` that fits, else the last, cut.

    The one rule for which text a one-line cell prints and whether it needs the cut; `shorter`
    follows `preferred` in decreasing length.
    """
    candidates = (preferred, *shorter)
    for text in candidates:
        if fits(text, size_mm=size_mm, bold=bold, width_mm=width_mm):
            return text, True
    return candidates[-1], False


def field_printed(  # noqa: PLR0913 -- the text, its cut mark, room, size, weight and shorter forms [public keyword API kept, decision 0444]
    text: str,
    *,
    ellipsis: str,
    room_mm: float,
    size_mm: float,
    bold: bool = False,
    shorter: tuple[str, ...] = (),
) -> tuple[str, bool, str]:
    """`(base, fits, printed)` of a one-line cell: `printed` is the base, cut if it misses."""
    metrics = {"size_mm": size_mm, "bold": bold, "width_mm": room_mm}
    base, ok = one_line_field(text, shorter=shorter, **metrics)
    return base, ok, base if ok else cut_to_width(base, ellipsis=ellipsis, **metrics)[0]


def notice_lines(text: str, *, width_mm: float, font_mm: float) -> tuple[str, ...]:
    """Greedy word-wrap at `font_mm`: an approximation of Typst's wrap; `()` for no words."""
    words = text.split()
    if not words:
        return ()
    lines = []
    current = words[0]
    for token in words[1:]:
        candidate = f"{current} {token}"
        if text_width_mm(candidate, size_mm=font_mm) <= width_mm:
            current = candidate
        else:
            lines.append(current)
            current = token
    lines.append(current)
    return tuple(lines)


def notice_pitch_mm(font_mm: float) -> float:
    """The distance from one notice line to the next at `font_mm`."""
    return font_mm * _NOTICE_LINE_EM


def notice_line_count(height_mm: float, *, font_mm: float) -> int:
    """How many notice lines at `font_mm` a cell `height_mm` high holds."""
    return int(height_mm // notice_pitch_mm(font_mm))


def notice_unfit(text: str, *, width_mm: float, font_mm: float, capacity: int) -> bool:
    """Whether `text` wrapped at `font_mm` needs more than `capacity` lines."""
    if not text:
        return False
    return len(notice_lines(text, width_mm=width_mm, font_mm=font_mm)) > capacity


def notice_room_chars(width_mm: float, *, font_mm: float, capacity: int) -> int:
    """About how many characters of running text `capacity` lines hold, to the nearest ten below."""
    sample = "the quick brown fox jumps over the lazy dog"
    per_line = width_mm * len(sample) / text_width_mm(sample, size_mm=font_mm)
    return int(per_line * capacity) // 10 * 10


class _CellText(Protocol):
    """The listing's title-block text: its cell labels and its cut mark."""

    @property
    def labels(self) -> Iterable[str]: ...
    @property
    def ellipsis(self) -> str: ...


def title_block_strings(
    fields: TitleBlockFields,
    rooms: Mapping[str, float],
    sizes: Sizes,
    text: _CellText,
    notice: tuple[float, int],
) -> TitleBlockStrings:
    """What the title block prints: each field cut to its slot's room, the notice wrapped.

    `notice` is the notice cell's width in mm and the number of lines it holds.
    """
    notice_width_mm, notice_capacity = notice
    printed: dict[str, str] = {}
    unfit = []
    for slot in (cell for cell in text.labels if cell != _COUNTER_CELL):
        name = _FIELD_OF_CELL.get(slot, slot)
        shorter = fields.page_title_shorter if name == "page_title" else ()
        base, ok, shown = field_printed(
            getattr(fields, name),
            ellipsis=text.ellipsis,
            room_mm=rooms[slot],
            size_mm=sizes.body,
            bold=name == "title",
            shorter=shorter,
        )
        printed[slot] = shown
        if not ok:
            unfit.append(FieldOverflow(field=name, shown=base))
    wrapped = notice_lines(fields.notice, width_mm=notice_width_mm, font_mm=sizes.label)
    return TitleBlockStrings(
        printed=frozendict(printed),
        notice=wrapped[:notice_capacity],
        unfit=tuple(unfit),
        notice_unfit=notice_unfit(fields.notice, width_mm=notice_width_mm, font_mm=sizes.label, capacity=notice_capacity),
    )


def _misses(form: FieldForms, rooms: Mapping[str, float], body_mm: float) -> TitleBlockOverflow | None:
    """The overflow of one field's text (`form.forms`: the preferred, then shorter ones), or `None`.

    A field whose cell the `[title_block]` record leaves out prints nowhere and overflows nowhere.
    """
    slot = "sheet" if form.field == "sheet_counter" else form.field
    if slot not in rooms:
        return None
    base, ok = one_line_field(
        form.forms[0],
        width_mm=rooms[slot],
        size_mm=body_mm,
        bold=form.field == "title",
        shorter=form.forms[1:],
    )
    return None if ok else TitleBlockOverflow(field=form.field, where=form.where, shown=base)


def title_block_overflows(forms: tuple[FieldForms, ...], sheets: DocumentSheets, rooms: Mapping[str, float]) -> tuple[TitleBlockOverflow, ...]:
    """The fields that miss their cell: `forms` is `derive.title_block_forms`."""
    printed = {cell: rooms[cell] for cell in sheets.title_text.labels if cell in rooms}
    found = (_misses(form, printed, sheets.sizes.body) for form in forms)
    return tuple(item for item in found if item is not None)


def index_titles(rows: tuple[SheetIndexRow, ...], ellipsis: str, sizes: Sizes, room_mm: float | None) -> tuple[str, ...]:
    """The printed title of each sheet index row: cut to the title cell's room, whole without."""
    if room_mm is None:
        return tuple(row.title for row in rows)
    return tuple(
        field_printed(
            row.title,
            ellipsis=ellipsis,
            room_mm=room_mm,
            size_mm=sizes.body,
            shorter=row.shorter,
        )[2]
        for row in rows
    )
