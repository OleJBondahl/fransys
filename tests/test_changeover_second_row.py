"""Layout-0090: a changeover's two throws hang under its pole in two rows.

The fixture is the field case `field_cases/test_changeover_throws_to_two_strips.py` inside its
unit: poles 3 and 4 of a changeover, each throw wired to its own terminal of a field strip
that stands at another location than the relay. That field case routes clean with or without
the second row, so its pass says nothing about where the second throw stands; this test does.

Row 1 is the throw the layout already hung under its pole, the break throw. The second throw
is the one not in row 1 (layout-0090): the make throw, whose terminal the chain used
to continue into and `cut_locations` then cut away into the strip's own column. It stands in
row 2 under its pole, in its pole's lane, on a straight wire, with no reference at either end.

Can-fail probe (one Edit, run, undone): `stages/chains.py::_attached_rows` putting every
attachment in one row fails the row-two test for both poles while the field case keeps passing.
"""

import importlib.util
from pathlib import Path

import pytest
from _drawn_pages import drawn_pages

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`, and
# ty cannot resolve a `sys.path` insert; the field case's own build is loaded from its file.
_FIELD_CASE = (
    Path(__file__).resolve().parent / "field_cases" / "test_changeover_throws_to_two_strips.py"
)
_spec = importlib.util.spec_from_file_location("_changeover_field_case", _FIELD_CASE)
assert _spec is not None
assert _spec.loader is not None
_field_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_field_case)

_POLES = (3, 4)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    """The field case's build inside its unit, shared by the module's tests."""
    return _field_case._build(tmp_path_factory.mktemp("second_row"), in_unit=True).model


def _pole(model, pole: int):
    """The (page, symbol) of the changeover contact of pole `pole`; its common is `<pole>1`."""
    (found,) = [
        (page, s)
        for page, drawing in drawn_pages(model).items()
        for s in drawing.symbols
        if s.key == "change-over-contact" and dict(s.slots).get("marking.com") == f"{pole}1"
    ]
    return found


def _rows_under(model, pole: int) -> list:
    """The terminals in the pole's column on its page, one list per row, top row first."""
    page, head = _pole(model, pole)
    column = [
        s
        for s in drawn_pages(model)[page].symbols
        if s.key == "terminal" and abs(s.x - head.x) <= 16
    ]
    return [[s for s in column if s.y == y] for y in sorted({s.y for s in column})]


@pytest.mark.parametrize("pole", _POLES)
def test_the_make_throw_stands_in_row_two_under_its_pole_on_a_straight_wire(model, pole) -> None:
    """Row 0 the pole, row 1 its break terminal, row 2 its make terminal, all on the pole's page;
    the make wire runs straight down from the throw to the terminal, a reference at neither end.
    """
    page, head = _pole(model, pole)
    rows = _rows_under(model, pole)
    assert len(rows) == 2  # row 1 the break terminal, row 2 the make terminal
    (brk,), (make,) = (sorted(row, key=lambda s: s.x) for row in rows)
    assert head.y < brk.y < make.y
    drawing = drawn_pages(model)[page]
    straight = [
        w for w in drawing.wires if len(w.points) == 2 and {x for x, _ in w.points} == {make.x}
    ]
    assert straight
    assert not drawing.markers


def test_each_throw_row_holds_both_poles_in_pole_order(model) -> None:
    """The break terminals share row 1 and the make terminals row 2, pole 3's lane left of 4's."""
    rows = [_rows_under(model, pole) for pole in _POLES]
    assert all(len(row) == 2 for row in rows)
    brk = [row[0][0] for row in rows]
    make = [row[1][0] for row in rows]
    assert len({p.y for p in brk}) == 1
    assert len({p.y for p in make}) == 1
    assert brk[0].x < brk[1].x
    assert make[0].x < make[1].x
