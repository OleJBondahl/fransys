"""A `d.layout.pins_below` hint puts every pin of a generic box on S (BOX-SIDES).

Can-fail probe: drop the hint check at the top of `box_sides` and the hinted box has pins on N.
"""

import fransys as fr
from fransys_el import symbol_kit
from fransys_el.placement_sides import box_sides
from placement_fixtures import leads

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY, default_order
from fransys_model.kernel import natural_key

_PINS = tuple(f"CH{n:02d}-" for n in range(1, 9))


def _sides(*, hinted: bool) -> tuple[str, ...]:
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        card = d.device("A1", None, pins=_PINS, external=True)
    if hinted:
        d.layout.pins_below(card)
    model = fr.build(d).model
    (pick,) = (p for p in leads(symbol_kit(model, LIBRARY)).values() if p.key == GENERIC_BOX_KEY)
    return box_sides(model, pick, default_order(pick.ports.values(), natural_key))


def test_a_hinted_box_has_every_pin_on_s() -> None:
    assert _sides(hinted=True) == ("s",) * len(_PINS)


def test_the_same_box_without_the_hint_has_pins_on_n() -> None:
    assert "n" in _sides(hinted=False)
