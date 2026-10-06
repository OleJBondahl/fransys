"""A list cell must break lines only between items, never inside a designation (pdf-0013).

`derive.cell_text` joins a tuple-valued cell's items with `"; "` into one string, and `_table`
(and `_terminal_table`) currently emit that whole string as one plain `text(...)` call. Typst
line-wraps a `text(...)` call anywhere a break opportunity falls, including at the leading `-`
of a designation like `-X01:L3:4` -- so a narrow column can end one line `"-X01:L3:3; -"` and
start the next `"X01:L3:4"`, splitting the designation across the dash.

The designer's ruling (decision pdf-0013): a list cell must break only between items. The fix
(`fransys_pdf._lists._cell_typst`): wrap each item of a tuple-valued cell in its own
unbreakable `box(...)`, joined by literal `"; "` text, instead of one `text(...)` over the whole
joined string. The joined TEXT `cell_text` produces is unchanged
(`tests/test_csv_agrees_with_pdf_lists.py` pins it against the CSV).

Two methods, matched to what each claim needs:

- SOURCE tests parse the generated Typst source (regex over `_table`'s returned string). They
  prove structure (is a cell boxed per item?) and text-preservation (do the string literals in
  the cell's markup still concatenate back to `cell_text`'s own joined string?). There is no PDF
  text extractor in this workspace and none may be added, so text-preservation is checked at
  the Typst-source level, not by reading back a rendered page.
- COMPILED tests render to PNG with `typst.compile(..., format="png")` (as `test_compile.py`
  already does) and compare pixels. Only a real compile can prove where Typst actually breaks a
  line; a source-level check cannot (Typst's line breaker, not this package, decides that). The
  two compiled tests here compare a `box(...)`-joined production render against a hand-written
  reference built from a plain `text(...)`/`linebreak()` sequence: two different Typst layout
  paths that happen to draw the same glyphs, which is not bit-exact even when the boxed and
  hand-written cells are visibly identical (demonstrated by decoding both PNGs and diffing every
    byte: 42 bytes differ, out of 2,931,360, by exactly 1 out of 255 -- anti-aliasing rounding
  from the two paths hinting glyphs a fraction of a pixel apart -- for the narrow-column test,
  and 3 bytes by 1 for the wide-column one). `_pixels_close` tolerates that: same width and
  height, and every byte within `_MAX_CHANNEL_DIFF`, with at most `_MAX_DIFFERING_BYTES`
  differing (both well above the demonstrated counts, so a real mismatch -- a wrongly placed
  line break -- still fails it by a wide margin).

Before the fix (base `eb0192b`), `_lists._table` and `_lists._terminal_table` emitted one bare
`text(...)` per cell with no `box(...)`, and the compiled tests failed on exact pixel equality
(no tolerance needed there: a wrongly-broken line differs by far more than 1/255 on far more than
3-42 bytes). Three tests FAILED on that base:
`test_tuple_cell_items_are_each_boxed`, `test_single_item_tuple_cell_is_boxed_too`,
`test_narrow_cell_breaks_mid_designation_today_not_at_the_fix_target`.
"""

import re

import typst
from _png import decode_png
from fransys_pdf import _lists
from fransys_pdf._lists import _table
from fransys_pdf._typst import literal
from test_lists import _two_sided_strip_model  # the strip model _terminal_table tests reuse

from fransys_model.derive import cell_text, terminal_rows, terminal_strips

_PAGE = "#set page(width: 210mm, height: 100mm, margin: 5mm)\n"
_9PT = '#set text(font: "Liberation Serif", size: 9pt)\n'
_PPI = 150.0

# The two compiled tests compare a `box(...)`-joined production render against a hand-written
# `text(...)`/`linebreak()` reference: two different Typst layout paths that draw the same
# glyphs but are not bit-exact even when visibly identical (measured: 42 of 2,931,360 bytes
# differ by 1/255 for the narrow-column test, 3 bytes by 1/255 for the wide-column one -- see
# module docstring). Both bounds below sit far above those counts; a real mismatch, a wrongly
# placed line break, differs by far more than this on far more of the page.
_MAX_CHANNEL_DIFF = 2
_MAX_DIFFERING_BYTES = 200

# `_table` puts a header word first (humanised from this column name); choosing a header word
# with no letters or punctuation in common with the designation values below keeps the two
# apart when a test scans "every string literal in the source" instead of isolating one cell.
_DESIGNATIONS_HEADER = ("designations",)
_DESIGNATIONS_VALUE = ("-X01:L3:3", "-X01:L3:4", "-X2:0V:1")


def _render(source: str) -> bytes:
    raw = typst.compile((_PAGE + _9PT + source).encode("utf-8"), format="png", ppi=_PPI)
    return raw[0] if isinstance(raw, list) else raw


def _assert_pixels_close(a: bytes, b: bytes) -> None:
    """`a` and `b`, two `typst.compile(..., format="png")` pages, are the same layout.

    Same width and height, and every byte within `_MAX_CHANNEL_DIFF`, with at most
    `_MAX_DIFFERING_BYTES` differing -- tolerating the anti-aliasing noise between a
    `box(...)`-joined render and a hand-written `linebreak()` one (module docstring), not a real
    difference in where a line breaks.
    """
    raster_a, raster_b = decode_png(a), decode_png(b)
    assert (raster_a.width, raster_a.height) == (raster_b.width, raster_b.height)
    diffs = [abs(x - y) for x, y in zip(raster_a.pixels, raster_b.pixels, strict=True) if x != y]
    assert len(diffs) <= _MAX_DIFFERING_BYTES, len(diffs)
    assert max(diffs, default=0) <= _MAX_CHANNEL_DIFF, max(diffs, default=0)


def _with_column_width(table_source: str, width_mm: int) -> str:
    """`table_source`'s own `columns: (...)` replaced by one fixed-width column."""
    return re.sub(r"columns: \([^)]*\)", f"columns: ({width_mm}mm)", table_source)


def _literal_strings(text: str) -> list[str]:
    """Every Typst string literal in `text`, unescaped, in order (`_typst.literal`'s own escaping:
    backslash and double-quote only, so a naive quoted-string pattern is exact for this source).
    """
    return [
        match[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        for match in re.findall(r'"(?:[^"\\]|\\.)*"', text)
    ]


# -- 1. SOURCE tests --------------------------------------------------------------------------


def test_tuple_cell_items_are_each_boxed():
    """pdf-0013's target: each of the tuple's 3 items stands in its own `box(...)`, so a line
    can only break between boxes, never inside one. FAILED on the pre-fix base (`eb0192b`):
    `text.count("box(") == 0`, not 3 -- there was no box anywhere.
    """
    text = _table(_DESIGNATIONS_HEADER, [(_DESIGNATIONS_VALUE,)], _DESIGNATIONS_HEADER)
    assert text.count("box(") == len(_DESIGNATIONS_VALUE)


def test_single_item_tuple_cell_is_boxed_too():
    """The rule applies even to a one-item tuple -- boxing is about the cell's *type* (a tuple,
    joined by `cell_text`), not about whether there is more than one item to protect a break
    between. FAILED on the pre-fix base (no `box(` at all).
    """
    text = _table(_DESIGNATIONS_HEADER, [(("-X01:L3:3",),)], _DESIGNATIONS_HEADER)
    assert "box(" in text


def test_plain_str_cell_is_not_boxed():
    """A plain string cell (a description, a net) is not a tuple and must keep wrapping freely
    -- `box(...)` would stop a long description from wrapping at all. Passed before and after
    the fix: only tuple-valued cells get boxed.
    """
    text = _table(("description",), [("A free-text description, not a designation list",)], ())
    assert "box(" not in text
    assert 'text("A free-text description, not a designation list")' in text


def test_terminal_table_ends_cells_are_each_boxed():
    """`_terminal_table` (the Bridge-column table, not `_table`) shares `_cell_typst` for its
    Side A / Side B cells (both tuple-valued: a terminal's ends). Cheap reuse of
    `test_lists.py`'s own two-sided-strip fixture rather than a new one: only one of its rows
    has a non-empty end on each side (a wire's far end), giving one boxed item per side.
    """
    model, _doc = _two_sided_strip_model()
    (strip,) = terminal_strips(model)
    text = _lists._terminal_table(model, terminal_rows(model, strip))
    assert 'box(text("-K1:A1:1"))' in text
    assert 'box(text("-K2:B1:1"))' in text
    assert text.count("box(") == 2


def test_table_cell_text_is_unchanged_by_the_wrap_fix():
    """Text-preservation guard: every Typst string literal in the one data cell's markup,
    concatenated in order with no added separator, must equal `cell_text`'s own `"; "`-joined
    string -- on the pre-fix base (one literal, the whole string) and after the fix (several
    literals: each item plus the `"; "` separators, which concatenate back to the same joined
    string). This is what stands in for `tests/test_csv_agrees_with_pdf_lists.py`'s guarantee at
    the Typst-source level: whatever markup shape the cell takes, the text it prints must not
    change. Isolates the one data cell by giving the header a word (humanised from
    `_DESIGNATIONS_HEADER`) that shares no substring with the designation values, then drops
    that one header literal from the scanned list.
    """
    text = _table(_DESIGNATIONS_HEADER, [(_DESIGNATIONS_VALUE,)], _DESIGNATIONS_HEADER)
    header_literal = _lists._humanise(_DESIGNATIONS_HEADER[0])
    cell_literals = [s for s in _literal_strings(text) if s != header_literal]
    assert "".join(cell_literals) == cell_text(_DESIGNATIONS_VALUE)


# -- 2. COMPILED layout test (the real proof) --------------------------------------------------
#
# W = 28mm. Measured (scratch script, not checked in) by rendering the pre-fix production
# `_table(...)` output for `_WRAP_VALUE` with its `columns: (...)` replaced by a single fixed
# width, at several widths, and comparing the resulting PNG byte-for-byte against a hand-written
# reference table whose cell is `text("-X01:L3:3; -") + linebreak() + text("-X01:L3:4")` (the
# pre-fix bug's actual break point: after the dash of the second item). Widths 26-29mm rendered
# byte-identical to that "breaks after the dash" reference; 30mm+ no longer wrapped at all. 28mm
# sits in the middle of that matching range, comfortably clear of both edges.


_WRAP_VALUE = ("-X01:L3:3", "-X01:L3:4")
_WRAP_WIDTH_MM = 28


def test_narrow_cell_breaks_only_between_the_two_items():
    """The real proof, compiled: at `_WRAP_WIDTH_MM`, the production cell (each item boxed by
    `_cell_typst`) renders the same layout as a hand-written reference that breaks between the
    two items -- the break landing after the first item's own `";"`, never inside the second
    item's designation. On the pre-fix base (one bare `text(...)`, no `box`), this instead broke
    at the leading `-` of the second designation (`test_csv_agrees_with_pdf_lists.py`'s sibling
    defect, decision pdf-0013) and this assertion FAILED (pixel mismatch: two different renders,
    not the anti-aliasing noise `_assert_pixels_close` tolerates).
    """
    table = _table(_DESIGNATIONS_HEADER, [(_WRAP_VALUE,)], _DESIGNATIONS_HEADER)
    production = _render(_with_column_width(table, _WRAP_WIDTH_MM))

    correct_layout_reference = _with_column_width(
        "#table(columns: (1fr), stroke: 0.5pt, "
        f"table.header(strong(text({literal(_lists._humanise(_DESIGNATIONS_HEADER[0]))}))), "
        'text("-X01:L3:3;") + linebreak() + text("-X01:L3:4"))',
        _WRAP_WIDTH_MM,
    )
    correct_layout = _render(correct_layout_reference)

    # Not vacuous: the correct layout really is a different render from letting the same
    # string wrap on its own (today's plain, unboxed cell) -- if it were pixel-identical to
    # `production`, the assertion below would prove nothing.
    wrong_layout = _render(
        _with_column_width(
            "#table(columns: (1fr), stroke: 0.5pt, "
            f"table.header(strong(text({literal(_lists._humanise(_DESIGNATIONS_HEADER[0]))}))), "
            f"text({literal(cell_text(_WRAP_VALUE))}))",
            _WRAP_WIDTH_MM,
        )
    )
    assert correct_layout != wrong_layout

    _assert_pixels_close(production, correct_layout)


# -- 3. Regression guard: nothing wraps, boxing changes nothing ------------------------------


def test_wide_cell_renders_identically_whether_or_not_items_are_boxed():
    """When a tuple cell's whole `"; "`-joined text fits on one line, boxing each item changes
    nothing visible: a hand-written `text("a; b")` (the pre-fix shape) renders pixel-identical
    to the production `_table(...)` cell at a width wide enough that nothing wraps either way.
    Passed before and after the fix (a regression guard).
    """
    value = ("a", "b")
    table = _table(_DESIGNATIONS_HEADER, [(value,)], _DESIGNATIONS_HEADER)
    production = _render(table)  # 1fr column on a 210mm page: far wider than "a; b" needs

    reference = (
        "#table(columns: (1fr), stroke: 0.5pt, "
        f"table.header(strong(text({literal(_lists._humanise(_DESIGNATIONS_HEADER[0]))}))), "
        f"text({literal(cell_text(value))}))"
    )
    _assert_pixels_close(production, _render(reference))
