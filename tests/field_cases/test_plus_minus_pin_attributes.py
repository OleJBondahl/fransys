"""Field case: a pin named `+` or `-` is reached by its typed attribute `_plus` or `_minus`.

The engineering shape: a primary cell with one function holding the pins `+` and `-`; the
generated parts module declares them as `_plus` and `_minus` (decision 0206, point 1).

The bug (0.19.6): `Device` and `Fn` refused every attribute that starts with `_`, so the
attributes the type checker accepted raised `AttributeError` at build time.
The fix (decision 0206, point 3): the catch-alls resolve a mapped name too; a dunder or a
private name that maps to no pin still raises.
"""

import copy

import fransys as fr
import pytest
from fransys.parts_module import parts_module

_UNMAPPED, _DUNDER = "_nothing", "__nothing__"


def _cell():
    d = fr.design("demo_parts", place="CAB")
    return d, d.device("BT1", "DEMO-CELL-3V6")


def test_the_generated_module_declares_the_names() -> None:
    text = parts_module("demo_parts")
    assert "_plus: Pin" in text
    assert "_minus: Pin" in text


def test_an_underscore_pin_attribute_gives_the_pin_of_the_brackets() -> None:
    _, cell = _cell()
    assert cell.cell._plus == cell.cell["+"]
    assert cell.cell._minus == cell.cell["-"]
    assert cell._plus == cell["+"]


def test_a_private_name_that_is_no_pin_still_raises() -> None:
    _, cell = _cell()
    with pytest.raises(AttributeError):
        getattr(cell, _UNMAPPED)
    with pytest.raises(AttributeError):
        getattr(cell.cell, _UNMAPPED)
    with pytest.raises(AttributeError):
        getattr(cell, _DUNDER)


def test_a_device_survives_copy_and_pickle_protocols() -> None:
    _, cell = _cell()
    assert copy.copy(cell)._label == "BT1"
    assert copy.deepcopy(cell.cell)._label == "BT1"
