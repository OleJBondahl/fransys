"""The title block's text rules: width, cut, one-line fields, wrapped notice, frame labels."""

from derive_helpers import house_record

from fransys_model.derive import (
    Sizes,
    TitleBlockFields,
    cut_to_width,
    field_printed,
    fits,
    frame_labels,
    notice_lines,
    notice_room_chars,
    notice_unfit,
    one_line_field,
    text_width_mm,
    title_block_strings,
)
from fransys_model.derive.rows_sheet_pages import TitleBlockText
from fransys_model.layout import FrameForm

_CELLS = [
    "title",
    "number",
    "revision",
    "revision_date",
    "customer",
    "author",
    "page_title",
    "scope",
    "sheet",
    "page",
]
_TEXT = TitleBlockText(labels=frozendict({cell: cell.title() for cell in _CELLS}), ellipsis="…")

_TEN_PT_MM = 10 * 25.4 / 72  # the size the width numbers in these tests were worked out at


def test_bold_text_width_differs_from_regular():
    """`bold=True` picks the bold advances over the regular ones, a genuinely different
    table (not a no-op): the same text set bold measures a different width.
    """
    text = "A somewhat long value"
    regular = text_width_mm(text, size_mm=_TEN_PT_MM, bold=False)
    bold = text_width_mm(text, size_mm=_TEN_PT_MM, bold=True)
    assert regular != bold


def test_cut_to_width_bold_needs_more_cutting_than_regular():
    """`bold` reaches every width computation inside `cut_to_width` (`fits`, the ellipsis's own
    width, and the per-character loop): at a width between the two tables' whole-text widths,
    the regular text fits untouched while the bold text must be cut.
    """
    text = "A somewhat long value"
    size_mm = _TEN_PT_MM
    regular_width = text_width_mm(text, size_mm=size_mm, bold=False)
    bold_width = text_width_mm(text, size_mm=size_mm, bold=True)
    width_mm = (regular_width + bold_width) / 2
    assert fits(text, size_mm=size_mm, bold=False, width_mm=width_mm)
    assert not fits(text, size_mm=size_mm, bold=True, width_mm=width_mm)
    assert cut_to_width(text, ellipsis="…", size_mm=size_mm, bold=False, width_mm=width_mm) == (
        text,
        False,
    )
    bold_cut, bold_was_cut = cut_to_width(
        text, ellipsis="…", size_mm=size_mm, bold=True, width_mm=width_mm
    )
    assert bold_was_cut is True
    assert bold_cut != text
    assert bold_cut.endswith("…")


def test_cut_to_width_default_bold_is_false():
    """`cut_to_width`'s own default (`bold=False`) is exercised by omitting the keyword: at a
    width where only the bold rendering needs cutting, the default call must not cut.
    """
    text = "A somewhat long value"
    size_mm = _TEN_PT_MM
    regular_width = text_width_mm(text, size_mm=size_mm, bold=False)
    bold_width = text_width_mm(text, size_mm=size_mm, bold=True)
    width_mm = (regular_width + bold_width) / 2
    assert cut_to_width(text, ellipsis="…", size_mm=size_mm, width_mm=width_mm) == (text, False)


def test_cut_to_width_loop_uses_bold_metrics_not_regular():
    """The per-character loop's own `text_width_mm(candidate, ..., bold=bold)` call must use
    the bold table too, not just the initial `fits` check: at a width between the bold and
    regular cumulative widths of a bold-heavy repeated character, cutting bold text stops
    three characters earlier than cutting the same text with the loop's bold flag dropped.
    """
    size_mm = _TEN_PT_MM
    text = "m" * 20  # bold 'm' is noticeably wider than regular 'm' in the bundled font
    ellipsis_width = text_width_mm("…", size_mm=size_mm, bold=True)
    bold_9 = text_width_mm("m" * 9, size_mm=size_mm, bold=True)
    regular_10 = text_width_mm("m" * 10, size_mm=size_mm, bold=False)
    bold_10 = text_width_mm("m" * 10, size_mm=size_mm, bold=True)
    budget = (bold_9 + bold_10) / 2  # between 9 and 10 bold ms
    assert regular_10 <= budget  # the regular table would keep a tenth m: the test can tell
    width_mm = budget + ellipsis_width
    assert not fits(text, size_mm=size_mm, bold=True, width_mm=width_mm)
    kept, was_cut = cut_to_width(text, ellipsis="…", size_mm=size_mm, bold=True, width_mm=width_mm)
    assert was_cut is True
    assert kept == "m" * 9 + "…"


def test_cut_to_width_stops_strictly_before_the_width_not_at_it():
    """The loop's own `> budget` (not `>=`) keeps a character whose running width lands
    exactly on the budget: at that exact boundary, "AB" is kept whole and only the following
    character is cut, proving the comparison is strict.
    """
    text = "ABCDEFGH"

    def _exact(size_mm: float) -> bool:  # float sums must give back the budget exactly
        e, c = text_width_mm("…", size_mm=size_mm), text_width_mm("AB", size_mm=size_mm)
        return (e + c) - e == c

    size_mm = next(s for s in (10.0, 9.0, 8.0, 12.0, 11.0, 7.0) if _exact(s))
    ellipsis_width = text_width_mm("…", size_mm=size_mm, bold=False)
    candidate_width = text_width_mm("AB", size_mm=size_mm, bold=False)
    width_mm = ellipsis_width + candidate_width
    assert not fits(text, size_mm=size_mm, width_mm=width_mm)
    assert cut_to_width(text, ellipsis="…", size_mm=size_mm, width_mm=width_mm) == ("AB…", True)


def test_notice_lines_of_empty_text_is_no_lines():
    """The `not words` guard: no words at all returns no lines."""
    assert notice_lines("", width_mm=100, font_mm=10) == ()


def test_notice_lines_of_one_word_returns_it_unwrapped():
    """A single word never enters the `for` loop body at all -- the post-loop
    `lines.append(current)` is what actually returns it.
    """
    assert notice_lines("OneWord", width_mm=100, font_mm=10) == ("OneWord",)


def test_notice_lines_splits_two_words_that_do_not_fit_together():
    """The loop's `else` branch: when the combined candidate is too wide, the first word
    ends its own line and the second starts a new one -- neither dropped nor merged.
    """
    size_mm = 10
    word1, word2 = "wordone", "wordtwo"
    combined_width = text_width_mm(f"{word1} {word2}", size_mm=size_mm)
    single_widths = (text_width_mm(word1, size_mm=size_mm), text_width_mm(word2, size_mm=size_mm))
    width_mm = (max(single_widths) + combined_width) / 2
    assert width_mm > max(single_widths)  # each word alone fits
    assert width_mm < combined_width  # together they do not
    assert notice_lines(f"{word1} {word2}", width_mm=width_mm, font_mm=size_mm) == (word1, word2)


def test_notice_lines_keeps_two_words_together_at_the_exact_boundary():
    """The loop's own `<= width_mm` (not `<`) keeps two words on one line when their combined
    width lands exactly on `width_mm`, proving the comparison is inclusive, not strict.
    """
    size_mm = 10
    text = "wordone wordtwo"
    width_mm = text_width_mm(text, size_mm=size_mm)
    assert notice_lines(text, width_mm=width_mm, font_mm=size_mm) == (text,)


# -- the capped notice, the strings of a title block, the frame labels ------------------------

_SIZES = Sizes(label=2.5, body=3.4, heading_2=4.8, heading_1=6.9, title_band_mm=20)
_ROOMS = {
    "title": 80.0,
    "number": 40.0,
    "revision": 20.0,
    "revision_date": 20.0,
    "customer": 40.0,
    "author": 40.0,
    "page_title": 60.0,
    "scope": 30.0,
    "sheet": 20.0,
}


def _fields(**over: object) -> TitleBlockFields:
    base = {
        "title": "T",
        "number": "N",
        "customer": "C",
        "revision": "A",
        "revision_date": "2026",
        "author": "me",
        "page_title": "Page",
        "scope": "S",
        "sheet_counter": "1.2",
    }
    return TitleBlockFields(**(base | over))  # ty: ignore[invalid-argument-type] -- test helper: keywords are the record's own fields


def test_field_printed_returns_base_fits_and_printed():
    """A text that fits prints whole; one that misses prints cut, the base kept for the finding."""
    room = text_width_mm("short", size_mm=3.4) + 0.01
    assert field_printed("short", ellipsis="…", room_mm=room, size_mm=3.4) == (
        "short",
        True,
        "short",
    )
    base, ok, shown = field_printed("short and longer", ellipsis="…", room_mm=room, size_mm=3.4)
    assert (base, ok) == ("short and longer", False)
    assert shown.endswith("…")
    assert fits(shown, size_mm=3.4, width_mm=room)


def test_one_line_field_takes_the_first_shorter_form_that_fits():
    """The shorter form prints when only it fits; with none fitting the last one is the base."""
    room = text_width_mm("mid", size_mm=3.4) + 0.01
    assert one_line_field(
        "a much longer text", size_mm=3.4, width_mm=room, shorter=("mid", "m")
    ) == (
        "mid",
        True,
    )
    assert one_line_field("long one", size_mm=3.4, width_mm=0.1, shorter=("long", "lo")) == (
        "lo",
        False,
    )


def test_notice_lines_wrap_a_known_sentence_at_a_known_width():
    """Three words, room for two on a line: the third starts the second line."""
    width = text_width_mm("alpha beta", size_mm=2.5) + 0.01
    assert notice_lines("alpha beta gamma", width_mm=width, font_mm=2.5) == ("alpha beta", "gamma")


def test_notice_unfit_counts_the_lines_against_the_capacity():
    """Two lines fit a capacity of two and miss a capacity of one; no text never misses."""
    width = text_width_mm("alpha beta", size_mm=2.5) + 0.01
    text = "alpha beta gamma"
    assert notice_unfit(text, width_mm=width, font_mm=2.5, capacity=1) is True
    assert notice_unfit(text, width_mm=width, font_mm=2.5, capacity=2) is False
    assert notice_unfit("", width_mm=width, font_mm=2.5, capacity=0) is False


def test_notice_room_chars_is_the_sample_estimate_to_the_ten_below():
    """Ten sample sentences wide and two lines: 43 characters a width, 86 chars, 80 below."""
    sample = "the quick brown fox jumps over the lazy dog"
    width = text_width_mm(sample, size_mm=2.5)
    assert notice_room_chars(width, font_mm=2.5, capacity=2) == 80
    assert notice_room_chars(width, font_mm=2.5, capacity=0) == 0


def test_title_block_strings_print_the_base_when_it_fits():
    """Every field fits: printed is the text per slot (`sheet_counter` fills `sheet`)."""
    got = title_block_strings(_fields(), _ROOMS, _SIZES, text=_TEXT, notice=(30, 2))
    assert got.printed["sheet"] == "1.2"
    assert got.printed["title"] == "T"
    assert set(got.printed) == set(_ROOMS)
    assert got.unfit == ()
    assert got.notice == ()
    assert got.notice_unfit is False


def test_title_block_strings_print_the_shorter_form_when_only_it_fits():
    """A page title too long for its room prints its shorter form and is not unfit."""
    rooms = _ROOMS | {"page_title": text_width_mm("Short", size_mm=3.4) + 0.01}
    fields = _fields(page_title="A very long page title indeed", page_title_shorter=("Short",))
    got = title_block_strings(fields, rooms, _SIZES, text=_TEXT, notice=(30, 2))
    assert got.printed["page_title"] == "Short"
    assert got.unfit == ()


def test_title_block_strings_cut_with_an_ellipsis_and_report_unfit():
    """No form fits: the printed text is cut with `…` and the field is named with its base."""
    fields = _fields(scope="Scope that is far too long", page_title_shorter=("x",))
    rooms = _ROOMS | {"scope": 6.0}
    got = title_block_strings(fields, rooms, _SIZES, text=_TEXT, notice=(30, 2))
    assert got.printed["scope"].endswith("…")
    assert [(u.field, u.shown) for u in got.unfit] == [("scope", "Scope that is far too long")]


def test_title_block_strings_cap_the_notice_to_the_capacity():
    """A notice of three lines in a two-line cell shows two lines and reports unfit."""
    width = text_width_mm("alpha beta", size_mm=2.5) + 0.01
    fields = _fields(notice="alpha beta gamma delta epsilon zeta")
    got = title_block_strings(fields, _ROOMS, _SIZES, text=_TEXT, notice=(width, 2))
    assert len(got.notice) == 2
    assert got.notice == notice_lines(fields.notice, width_mm=width, font_mm=2.5)[:2]
    assert got.notice_unfit is True


def test_frame_labels_number_the_columns_and_letter_the_rows():
    """An 8 by 6 frame reads 1..8 across and A..F down."""
    labels = frame_labels(house_record(FrameForm), 8, 6)
    assert labels.columns == ("1", "2", "3", "4", "5", "6", "7", "8")
    assert labels.rows == ("A", "B", "C", "D", "E", "F")
