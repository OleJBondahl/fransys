"""layout-0316 D: the symdef layer gives the old builder's values (bytes do not move)."""

import pytest
from placement_fixtures import demo_model, kit_for, planted_model
from symdef_layer_equivalence import checked, diffs, pairs


@pytest.mark.parametrize("make", [planted_model, demo_model])
def test_the_layer_equals_the_old_builder_at_every_orientation(make) -> None:
    model = make()
    assert checked(model, kit_for(model)) == []


def test_a_wrong_view_is_seen() -> None:
    """Can fail: one wider R180 footprint makes `diffs` name it."""
    from symdef_layer_equivalence import planted

    model = demo_model()
    old, new = pairs(model, kit_for(model))[0]
    assert diffs(old, new) == []
    assert any("R180 footprint" in line for line in diffs(old, planted(new)))
