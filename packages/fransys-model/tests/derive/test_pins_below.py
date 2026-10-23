"""`derive.pins_below` and `check_pins_below` (BOX-SIDES): the hint's one fact and its warning.

Built from `examples/demo-parts` only. Can-fail probes: make `pins_below` return `True` and the
unhinted-function test fails; lower `_MIN_PINS` to 1 and the one-port test fails.
"""

import fransys as fr

from fransys_model.derive import check_pins_below, pins_below
from fransys_model.kernel import Model, Severity
from fransys_model.vocab import functions, items

_PINS = ("CH01-", "CH02-", "CH03-")


def _build(*, one_port_hint: bool = False) -> Model:
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        card = d.device("A1", None, pins=_PINS, external=True)
        d.device("A2", None, pins=_PINS, external=True)
        lone = d.device("A3", None, pins=("P",), external=True)
    d.layout.pins_below(card)
    if one_port_hint:
        d.layout.pins_below(lone)
    return fr.build(d).model


def _function(model: Model, tag: str):
    return next(f.id for f in functions(model).values() if items(model)[f.item].tag == tag)


def test_the_hinted_function_is_true_and_another_is_false() -> None:
    model = _build()
    assert pins_below(model, _function(model, "A1"))
    assert not pins_below(model, _function(model, "A2"))


def test_a_hint_on_a_box_does_not_warn() -> None:
    assert check_pins_below(_build()) == ()


def test_a_hint_on_a_one_port_device_warns_naming_it() -> None:
    model = _build(one_port_hint=True)
    (found,) = check_pins_below(model)
    assert (found.code, found.severity) == ("PINS_BELOW_NOT_A_BOX", Severity.WARNING)
    assert found.subjects == (_function(model, "A3"),)
    assert "A3" in found.message
