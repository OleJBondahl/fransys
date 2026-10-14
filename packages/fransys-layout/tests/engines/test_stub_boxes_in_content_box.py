"""Every harness stub box, as render will draw it, lies inside its page's content box."""

import pytest
from fransys_el import OPTIONS
from layout_cabinet import build_cabinet
from usecases.test_usecases import _NARROW_WIDTH_MM, _on_sheet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages.content import content_box
from fransys_model.kernel import freeze
from fransys_model.layout import LinkMarker

CASES = {
    "cabinet": build_cabinet,
    "cabinet_narrow": lambda: _on_sheet(_NARROW_WIDTH_MM),
    "cabinet_two_location": lambda: build_cabinet(second_location=True),
}


@pytest.mark.parametrize("name", CASES)
def test_every_stub_box_lies_inside_the_content_box(name: str) -> None:
    """The box origin is the one render derives: centred on the stub unless `box_x` holds it."""
    model = freeze(CASES[name]())
    content = content_box(read_inputs(model, options=OPTIONS).sheet)
    laid, _ = lay_out_schematic(model, OPTIONS)
    markers = [m for m in laid.tables["layout.link_marker"].values() if isinstance(m, LinkMarker)]
    stubs = [m for m in markers if m.carrier is not None]
    assert stubs or name == "cabinet_two_location"  # that case has no leaving harness stub
    for m in stubs:
        x = m.box_x if m.box_x is not None else m.x - m.width // 2
        assert content.x <= x
        assert x + m.width <= content.x + content.width
