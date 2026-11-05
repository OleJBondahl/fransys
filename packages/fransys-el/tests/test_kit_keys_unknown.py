"""A key the model lacks is refused with a `ProblemError` naming the key and the fix (KIT-PINS)."""

from typing import Any

import pytest
from fransys_el import ProblemError
from fransys_el.kit_keys import function_of
from kit_instances import INSTANCES


def test_function_of_refuses_a_key_the_model_lacks() -> None:
    model = INSTANCES[next(iter(INSTANCES))]()
    key: Any = "nonexistent-key"  # not a PickKey on purpose
    with pytest.raises(ProblemError, match="nonexistent-key") as raised:
        function_of(model, key)
    assert raised.value.fix == "pick only keys the model has"
    assert raised.value.key == "nonexistent-key"
