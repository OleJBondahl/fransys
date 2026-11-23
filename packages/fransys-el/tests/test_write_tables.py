"""A contact-table spot is named apart from a designation corner (R339)."""

from dataclasses import replace

from fransys_el import write_tables
from fransys_el.placement_tables import is_table_spot
lazy import pytest

from electrical_symbols import LIBRARY
from fransys_layout.core import Box
from fransys_layout.drawing import DrawnText


def test_only_a_table_spot_is_a_table_spot() -> None:
    assert is_table_spot("table-BR")
    assert not any(is_table_spot(c) for c in ("TL", "TR", "BL", "BR"))


def _lines_under(text: DrawnText, monkeypatch: pytest.MonkeyPatch) -> list[DrawnText]:
    monkeypatch.setattr(write_tables, "where_text", lambda _m, _here, there: f"p{there[0]}")
    monkeypatch.setattr(write_tables, "where_link", lambda *_: None)
    monkeypatch.setattr(write_tables, "where_targets", lambda _m, _f, rows, page: [r for r in rows if r[0] != page])
    rows = [("a", None), ("b", None), ("c", None)]
    return write_tables._lines(None, (LIBRARY, 3, "a"), text, rows, None)  # ty: ignore[invalid-argument-type] - doubles (R2997)


def test_where_lines_step_one_line_pitch_down_under_an_upright_tag_and_right_of_a_turned_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """The step is the library's block pitch (one line pitch), not the tag box's height, which holds every reserved line."""
    tag = DrawnText("-X1:1", Box(10, 20, 30, 16), "TAG", "NW", "s")
    low = _lines_under(tag, monkeypatch)
    assert [t.box.x for t in low] == [10, 10]
    step = low[1].box.y - low[0].box.y
    assert 0 < step == low[0].box.y - tag.box.y < tag.box.h
    turned = _lines_under(replace(tag, box=Box(10, 20, 16, 30), anchor="SW", turned=True), monkeypatch)
    assert [t.box.x for t in turned] == [10 + step, 10 + 2 * step]
    assert all(t.turned and t.anchor == "SW" and t.box.y == tag.box.y for t in turned)  # TP6: every turned line starts at the annex top


def test_a_turned_text_in_a_taller_annex_stands_at_the_annex_top_nearest_its_terminal() -> None:
    """TP6 (owner Q1 a): the ink of a turned tag touches the top edge of its annex, however much of the annex it leaves free below."""
    annex = Box(10, 20, 16, 100)
    assert write_tables.line_box(annex, 30, 16, turned=True) == Box(10, 20, 16, 30)
    assert write_tables.line_box(annex, 30, 16, turned=False) == Box(10, 20, 30, 16)
