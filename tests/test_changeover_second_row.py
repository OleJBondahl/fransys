"""S13 (decision layout-0090): a changeover's two throws hang under its pole in two rows.

The fixture is the field case `field_cases/test_changeover_throws_to_two_strips.py` inside its
unit: poles 3 and 4 of a changeover, each throw wired to its own terminal of a field strip
that stands at another location than the relay. That field case routes clean with or without
the second row, so its pass says nothing about where the second throw stands; this test does.

Row 1 is the throw the layout already hung under its pole, the break throw. The second throw
is the one not in row 1 (S13's own definition): the make throw, whose terminal the chain used
to continue into and `cut_locations` then cut away into the strip's own column. It stands in
row 2 under its pole, in its pole's lane, on a straight wire, with no reference at either end.

Can-fail probe (one Edit, run, undone): `stages/chains.py::_attached_rows` putting every
attachment in one row fails the row-two test for both poles while the field case keeps passing.
"""

import importlib.util
from pathlib import Path

import pytest

from fransys_model.layout import LinkMarker, Route, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, ports

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


def _placed(model, *key: str) -> SymbolPlacement:
    fns = functions(model)
    (placement,) = [
        p for p in layout_of(model, SymbolPlacement).values() if fns[p.function].key == key
    ]
    return placement


def _pole(model, pole: int) -> SymbolPlacement:
    return _placed(model, "UNIT", "K1", "fn", f"co_{pole}")


def _terminal(model, strip: str, pole: int) -> SymbolPlacement:
    return _placed(model, "UNIT", strip, "terminal", f"RUN{pole}", "1", "fn", "terminal")


def _make_route(model, pole: int) -> Route:
    """The route of the wire from pole `pole`'s make throw to its field terminal."""
    function = _pole(model, pole).function
    (port,) = [
        pid for pid, p in ports(model).items() if p.function == function and p.name == f"{pole}4"
    ]
    (route,) = [r for r in layout_of(model, Route).values() if port in (r.a, r.b)]
    return route


@pytest.mark.parametrize("pole", _POLES)
def test_the_make_throw_stands_in_row_two_under_its_pole_on_a_straight_wire(model, pole) -> None:
    """Row 0 the pole, row 1 its break terminal, row 2 its make terminal, all on the pole's page;
    the make wire runs straight down from the throw to the terminal, a reference at neither end.
    """
    head, brk, make = (
        _pole(model, pole),
        _terminal(model, "X02", pole),
        _terminal(model, "X01", pole),
    )
    assert head.page == brk.page == make.page
    assert head.y < brk.y < make.y
    route = _make_route(model, pole)
    assert len(route.points) == 2
    assert {point.x for point in route.points} == {make.x}
    assert not [m for m in layout_of(model, LinkMarker).values() if m.port in (route.a, route.b)]


def test_each_throw_row_holds_both_poles_in_pole_order(model) -> None:
    """The break terminals share row 1 and the make terminals row 2, pole 3's lane left of 4's."""
    brk = [_terminal(model, "X02", pole) for pole in _POLES]
    make = [_terminal(model, "X01", pole) for pole in _POLES]
    assert len({p.y for p in brk}) == 1
    assert len({p.y for p in make}) == 1
    assert brk[0].x < brk[1].x
    assert make[0].x < make[1].x
