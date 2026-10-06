"""GOLDEN-FIX 2 follow-up: the text a `tag.conn` label is measured from is the text render prints.

A connector's designation on a row lead of pins is `connector_designation` ("-K1"; "-A1-X1" on a
device with two labelled connectors, decision model-0073), one derive function (D12 + designer
ruling). Layout sizes the label's box from its request text, so a request text of
the port designation ("-K1:2") would over-reserve; the box width must be the width of
`label_text` for every `tag.conn` label, at top level and in a unit's own set.

Can-fail, checked by hand: with `pin_tag` leaving the pin's own request text on the `tag.conn`
request, the test fails on the top-level label.
"""

import importlib.util

from workspace_root import WORKSPACE_ROOT

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import Label, layout_of

_ROOT_TESTS = WORKSPACE_ROOT / "tests"


def _system_model():
    """The two-cabinet system of the units worked example, loaded by path (root tests are not a
    package)."""
    path = _ROOT_TESTS / "test_units_worked_example.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._build_system()[0].model


def test_a_connector_row_lead_is_measured_from_the_text_render_prints() -> None:
    model = _system_model()
    inputs = read_inputs(model)
    results, _ = stage_results(model, inputs)
    height = inputs.profile.text_height
    measured = sorted(one.box.width for one in results.layout.labels if one.slot == "tag.conn")
    printed = sorted(
        text_width(label_text(model, lb), height=height)
        for lb in layout_of(model, Label).values()
        if lb.slot == "tag.conn"
    )
    assert measured
    assert measured == printed
