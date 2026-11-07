"""Field case: `d.layout.order` called with group names as strings, the way a guide example once spelled it.
The bug: the call died with a raw `AttributeError` on `str.key`, naming neither the call nor the fix.
Fixed by model-0441 (R1841): an `AuthorError` names `d.layout.order`, the argument and the group handles to pass."""

import fransys as fr
import pytest


def test_an_order_hint_given_strings_is_an_author_error_naming_the_call_and_the_fix() -> None:
    d = fr.design("demo_parts")
    with d.function("PUMPS", "Pumps") as pumps:
        d.device("K1", "DEMO-RLY-2CO-24")
    with pytest.raises(fr.AuthorError) as raised:
        d.layout.order(pumps, "valves")  # ty: ignore[invalid-argument-type]  the case is a string given where a Group belongs
    message = str(raised.value)
    assert "d.layout.order" in message
    assert "'valves'" in message
    assert "group handles" in message
