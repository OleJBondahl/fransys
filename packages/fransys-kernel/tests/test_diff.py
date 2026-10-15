"""Tests: `kernel.diff`."""

from typing import Any

import pytest

from fransys_kernel import Draft, Id, ModelDiff, Origin, SchemaError, diff, freeze


def _thing_id(digit: str) -> Id[Any]:
    return Id(kind="thing", value=digit * 32)


def _model(thing_cls: type, origin: Origin, **names: str) -> Any:
    """A model of things: `name` keyword `t1="pump"` is the thing with id digit `1`."""
    draft = Draft()
    for label, name in names.items():
        digit = label.removeprefix("t")
        draft.add(thing_cls(id=_thing_id(digit), key=(digit,), name=name), origin=origin)
    return freeze(draft)


def test_diff_of_a_model_with_itself_is_three_empty_tuples(thing_cls: type, origin: Origin) -> None:
    """Nothing added, removed or changed."""
    model = _model(thing_cls, origin, t1="pump", t2="valve")
    assert diff(model, model) == ModelDiff(added=(), removed=(), changed=())


@pytest.mark.parametrize("bad", [None, "model", 3])
def test_diff_refuses_something_that_is_not_a_model(
    bad: Any, thing_cls: type, origin: Origin
) -> None:
    """Either side: a `SchemaError`, not an `AttributeError`."""
    model = _model(thing_cls, origin, t1="pump")
    with pytest.raises(SchemaError, match="two Models") as excinfo:
        diff(bad, model)
    assert excinfo.value.kind == "diff"
    with pytest.raises(SchemaError, match="two Models") as excinfo:
        diff(model, bad)
    assert excinfo.value.kind == "diff"
