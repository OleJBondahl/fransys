"""`table_source`: the two-row split rule, the whole block, the repeated heading (pdf-0027)."""

from fransys_pdf._tables import table_source

_ROW = ["text(1)", "text(2)"]


def _source(rows: int, **kw: tuple[str, str]) -> str:
    return table_source(["auto", "1fr"], ["text(a)", "text(b)"], [_ROW] * rows, rule="0.18mm", **kw)


def test_a_table_of_three_rows_is_one_unbreakable_block():
    text = _source(3)
    assert text.startswith("#block(breakable: false)[")
    assert "rowspan" not in text


def test_a_table_of_four_rows_pins_its_first_two_and_last_two_rows():
    text = _source(4)
    assert not text.startswith("#block(breakable: false)")
    assert text.count("rowspan: 2") == 2


def test_five_rows_give_two_span_cells_and_one_free_row():
    assert _source(5).count("rowspan: 2") == 2


def test_a_titled_table_repeats_its_heading_with_cont_and_names_its_anchor():
    text = _source(6, heading=("-X1 (cont.)", "term0"))
    assert "-X1 (cont.)" in text
    assert "locate(<term0>)" in text
    assert text.rstrip("\n ]").endswith("<term0>")


def test_an_untitled_table_has_no_repeat():
    assert "(cont.)" not in _source(6)
