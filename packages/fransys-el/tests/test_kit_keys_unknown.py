"""A key the model lacks is refused with a `ProblemError` naming the key and the fix (KIT-PINS)."""

import pytest
from fransys_el import ProblemError
from fransys_el.kit_keys import function_of
from kit_instances import INSTANCES


def test_function_of_refuses_a_key_the_model_lacks() -> None:
    model = INSTANCES[next(iter(INSTANCES))]()
    with pytest.raises(ProblemError, match="nonexistent-key") as raised:
        function_of(model, "nonexistent-key")  # ty: ignore[invalid-argument-type]  # a wrong key on purpose
    assert raised.value.fix == "pick only keys the model has"
    assert raised.value.key == "nonexistent-key"
