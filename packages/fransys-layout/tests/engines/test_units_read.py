"""`read/units.py`: which units contain a unit, its top-level unit, whether it is nested.

Small unit-only models built by hand: `_model` takes `(name, parent name)` pairs.
"""

from layout_cabinet import unit_with_release

from fransys_layout.engines.schematic.read.units import (
    containing_units,
    is_nested,
    top_level_unit,
    unit_nesting,
)
from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab import Unit

_ORIGIN = Origin(file="tests/engines/test_units_read.py", line=1, note="units read tests")


def _unit(name: str) -> Id[Unit]:
    return make_id(Unit, ("units-read", name))


def _model(*units: tuple[str, str | None]) -> Model:
    """A model of units `(name, parent name)`; a parent cycle is allowed (`freeze` accepts it)."""
    draft = Draft()
    for name, parent in units:
        unit, release = unit_with_release(
            ("units-read", name), name=name, parent=None if parent is None else _unit(parent)
        )
        draft.extend((release, unit), origin=_ORIGIN)
    return freeze(draft)


def test_three_levels_of_nesting_read_as_the_units_holding_the_leaf() -> None:
    """A leaf in a mid in a top: the leaf's containing units are all three, its top is `top`."""
    # UNDO: read/units.py `is_nested`: `> 1` -> `> 2` (a mid unit is no longer nested)
    # UNDO: read/units.py `top_level_unit`: return `unit` (the leaf is its own top)
    model = _model(("top", None), ("mid", "top"), ("leaf", "mid"))
    top, mid, leaf = _unit("top"), _unit("mid"), _unit("leaf")
    assert containing_units(model, leaf) == {leaf, mid, top}
    assert top_level_unit(model, leaf) == top
    assert top_level_unit(model, mid) == top
    assert top_level_unit(model, top) == top
    assert is_nested(model, leaf)
    assert is_nested(model, mid)
    assert not is_nested(model, top)


def test_no_unit_and_an_unknown_unit_are_in_no_unit() -> None:
    model = _model(("top", None))
    for unit in (None, _unit("absent")):
        assert containing_units(model, unit) == frozenset()
        assert top_level_unit(model, unit) is None
        assert not is_nested(model, unit)


def test_unit_nesting_inside_holds_every_unit_and_its_containing_units() -> None:
    """`inside` is what a hand walk up `Unit.parent` gives, for every unit of the model."""
    model = _model(("top", None), ("mid", "top"), ("leaf", "mid"), ("other", None))
    top, mid, leaf, other = (_unit(name) for name in ("top", "mid", "leaf", "other"))
    nesting = unit_nesting(model, [leaf, other, None])
    assert dict(nesting.inside) == {
        top: {top},
        mid: {mid, top},
        leaf: {leaf, mid, top},
        other: {other},
    }
    assert nesting.nested == {leaf}


def test_a_parent_cycle_ends_and_reads_as_nested_with_no_top() -> None:
    """A.parent = B and B.parent = A: no walk loops; each is nested in the other, neither is top."""
    model = _model(("a", "b"), ("b", "a"))
    a, b = _unit("a"), _unit("b")
    assert containing_units(model, a) == {a, b}
    assert is_nested(model, a)
    assert top_level_unit(model, a) is None
