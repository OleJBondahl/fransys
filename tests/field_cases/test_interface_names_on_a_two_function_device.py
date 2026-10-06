"""Field case: a device with two functions marks the named ones a boundary.

The engineering shape: an I/O board unit with one two-connector part: `x1` is the interface the
cabinet plugs into, `x2` a spare connector left open on purpose.

The bug: `interface=True` and `unused=True` took the device's one function, so a device with two
functions could not take them, and a script reached for the engine's own `boundary` and `unused`.

The rule (EA15, G26, owner "B1"): `interface=` and `unused=` take `True` (every function) or a
tuple of the part's function names. A name the part lacks raises and names its functions. A name
in `unused` is a boundary too.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys_author import AuthorError

from fransys_model.vocab.tables import boundaries, functions, unused_boundaries

_PART = "DEMO-IO-2X"


def _names(model: fr.Model, ids: list) -> set[str]:
    return {functions(model)[i].name for i in ids}


class _Io(NamedTuple):
    A1: Any


@fr.unit("demo-io", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _named(d: fr.Design) -> _Io:
    return _Io(d.device("A1", _PART, interface=("x1",), unused=("x2",)))


@fr.unit("demo-io-all", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _all(d: fr.Design) -> _Io:
    return _Io(d.device("A1", _PART, interface=True))


def _model(unit: Any) -> fr.Model:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(unit, "IO")
    return fr.build(d).model


def test_names_mark_exactly_those_functions() -> None:
    """`interface=("x1",)` and `unused=("x2",)`: x1 is a boundary; x2 is one, and unused."""
    model = _model(_named)
    assert _names(model, [b.function for b in boundaries(model).values()]) == {"x1", "x2"}
    assert _names(model, [u.function for u in unused_boundaries(model).values()]) == {"x2"}


def test_true_marks_every_function() -> None:
    model = _model(_all)
    assert _names(model, [b.function for b in boundaries(model).values()]) == {"x1", "x2"}


def test_a_name_the_part_lacks_raises_and_names_the_functions() -> None:
    d = fr.design("demo_parts", place="C1")
    with pytest.raises(AuthorError, match=r"x9.*functions: x1, x2"):
        d.device("A1", _PART, interface=("x9",))
