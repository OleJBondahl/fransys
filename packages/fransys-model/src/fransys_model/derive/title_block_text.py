"""The title block's printed text: width, cut, one-line fields, the wrapped notice (pdf-0010).

Moved whole from `fransys_pdf._frame`; the callers pass the room (mm) a cell offers.
"""

from functools import partial
lazy from collections.abc import Mapping

from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

from .house_settings import title_block_form_of, word
from .rows_sheet import FieldOverflow, Sizes, TitleBlockFields, TitleBlockStrings
from .rows_sheet_pages import DocumentSheets, TitleBlockOverflow, TitleBlockText
from .text_width import UNITS_PER_EM, text_units
from .title_block import document_facts

__all__ = [
    "cut_to_width",
    "field_printed",
    "fits",
    "notice_line_count",
    "notice_lines",
    "notice_pitch_mm",
    "notice_room_chars",
    "notice_unfit",
    "one_line_field",
    "text_width_mm",
    "title_block_overflows",
    "title_block_strings",
    "title_block_words",
]

_NOTICE_LINE_EM = 1.2  # the notice's line pitch in em

# the cell whose `TitleBlockFields` field has another name (`sheet_counter` fills `sheet`)
_FIELD_OF_CELL = {"sheet": "sheet_counter"}
# the cell pdf fills with the page counter: it holds no field of `TitleBlockFields`
_COUNTER_CELL = "page"


def title_block_words(model: Model) -> TitleBlockText:
    """The labels of the `[title_block]` record's cells, in its order, and the cut mark."""
    cells = title_block_form_of(model).fields
    return TitleBlockText(
        labels=frozendict({cell: word(model, cell) for cell in cells}),
        ellipsis=word(model, "ellipsis"),
    )


def text_width_mm(text: str, *, size_mm: float, bold: bool = False) -> float:
    """The width of `text` in DejaVu Sans Condensed at `size_mm`, from the one table."""
    return text_units(text, bold=bold) / UNITS_PER_EM * size_mm


def fits(text: str, *, size_mm: float, bold: bool = False, width_mm: float) -> bool:
    """Whether `text` set at `size_mm` (bold or not) is no wider than `width_mm`."""
    return text_width_mm(text, size_mm=size_mm, bold=bold) <= width_mm


def cut_to_width(
    text: str, *, ellipsis: str, size_mm: float, bold: bool = False, width_mm: float
) -> tuple[str, bool]:
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


def field_printed(  # noqa: PLR0913 -- the text, its cut mark, room, size, weight and shorter forms
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


def title_block_strings(
    fields: TitleBlockFields,
    rooms: Mapping[str, float],
    sizes: Sizes,
    *,
    text: TitleBlockText,
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
        notice_unfit=notice_unfit(
            fields.notice, width_mm=notice_width_mm, font_mm=sizes.label, capacity=notice_capacity
        ),
    )


_DOCUMENT_FIELDS = ("title", "number", "customer", "revision", "revision_date", "author")


def _misses(
    field: str,
    forms: tuple[str, ...],
    where: str,
    *,
    rooms: Mapping[str, float],
    body_mm: float,
) -> TitleBlockOverflow | None:
    """The overflow of one field's text (`forms`: the preferred, then shorter ones), or `None`.

    A field whose cell the `[title_block]` record leaves out prints nowhere and overflows nowhere.
    """
    slot = "sheet" if field == "sheet_counter" else field
    if slot not in rooms:
        return None
    base, ok = one_line_field(
        forms[0], width_mm=rooms[slot], size_mm=body_mm, bold=field == "title", shorter=forms[1:]
    )
    return None if ok else TitleBlockOverflow(field=field, where=where, shown=base)


def title_block_overflows(
    model: Model, document: Id[Document], sheets: DocumentSheets, rooms: Mapping[str, float]
) -> tuple[TitleBlockOverflow, ...]:
    """The fields that miss their cell: the six document-level ones, then each checked page's."""
    record = documents(model)[document]
    printed = {cell: rooms[cell] for cell in sheets.title_text.labels if cell in rooms}
    miss = partial(_misses, rooms=printed, body_mm=sheets.sizes.body)
    facts = dict(zip(_DOCUMENT_FIELDS, document_facts(model, record.id), strict=True))
    found = [miss(f, (facts[f],), "document") for f in _DOCUMENT_FIELDS]
    seen: set[str] = set()
    for page in (p for p in sheets.pages if p.group):
        fields = page.fields
        if page.group not in seen:
            seen.add(page.group)
            found.append(miss("scope", (fields.scope,), page.group))
        titles = (fields.page_title, *fields.page_title_shorter)
        found.append(miss("page_title", titles, page.where))
        found.append(miss("sheet_counter", (fields.sheet_counter,), page.where))
    return tuple(item for item in found if item is not None)
