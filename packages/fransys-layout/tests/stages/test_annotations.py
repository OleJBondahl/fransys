"""Every stage value type resolves its annotations eagerly (docs/design/stages.md 6; ruff TC004).

The model's `@value` reads every field annotation at runtime, so a name used in one may not
be imported under `TYPE_CHECKING`. `annotationlib.Format.VALUE` evaluates the annotations as
Python does, and raises `NameError` for a name that is not there.
"""

import annotationlib
import dataclasses
import inspect
from typing import TYPE_CHECKING

import pytest

from fransys_layout.engines.schematic.read import StageInputs
from fransys_layout.stages import types as stage_types

if TYPE_CHECKING:
    from decimal import Decimal


def _value_types() -> list[type]:
    """Every dataclass defined in `stages/types.py`, then `StageInputs`, in name order."""
    found = [
        cls
        for _, cls in inspect.getmembers(stage_types, inspect.isclass)
        if dataclasses.is_dataclass(cls) and cls.__module__ == stage_types.__name__
    ]
    return [*found, StageInputs]


VALUE_TYPES = _value_types()


def test_the_check_covers_every_stage_value() -> None:
    """The collection is not empty by accident: the two ends of the list are in it."""
    names = {cls.__name__ for cls in VALUE_TYPES}
    assert len(VALUE_TYPES) >= 30
    assert {"Profile", "FunctionSpec", "Column", "LinkMarker", "Layout", "StageInputs"} <= names


@pytest.mark.parametrize("cls", VALUE_TYPES, ids=lambda cls: cls.__name__)
def test_a_stage_value_resolves_its_annotations_eagerly(cls: type) -> None:
    annotations = annotationlib.get_annotations(cls, format=annotationlib.Format.VALUE)
    assert annotations


def test_the_check_can_fail() -> None:
    """A field annotated with a name imported only under `TYPE_CHECKING` raises `NameError`."""

    class Broken:
        amount: Decimal

    with pytest.raises(NameError):
        annotationlib.get_annotations(Broken, format=annotationlib.Format.VALUE)
