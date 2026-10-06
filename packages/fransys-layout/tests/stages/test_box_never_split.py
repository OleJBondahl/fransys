"""V5, layout-0103: an item box is drawn on one page, inside its content width, on every fixture."""

import pytest
from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_model

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import GENERIC_BOX_KEY
from fransys_model.kernel import freeze

_MODELS = {
    "cabinet": lambda: freeze(build_cabinet()),
    "two_location": lambda: freeze(build_cabinet(second_location=True)),
    "narrow": lambda: narrow_model(245),
}


@pytest.mark.parametrize("name", sorted(_MODELS))
def test_no_item_box_spans_two_pages_on_a_cabinet_fixture(name: str) -> None:
    model = _MODELS[name]()
    inputs = read_inputs(model)
    results, _ = stage_results(model, inputs)
    boxes = [p for p in results.layout.placed if p.geometry.key == GENERIC_BOX_KEY]
    assert boxes, "no box on this fixture: the check would pass over nothing"
    for placed in boxes:
        keepout = placed.geometry.keepout
        assert placed.at.x + keepout.x >= 0
        assert placed.at.x + keepout.x + keepout.width <= inputs.sheet.content_width
