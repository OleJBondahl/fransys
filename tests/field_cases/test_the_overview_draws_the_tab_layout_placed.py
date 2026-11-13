"""Field case: a unit with a supply terminal strip and a lamp, and a cable to a second lamp in the field, on the overview page.
The bug: the page script drew each cable tab at its own size, while layout had placed the line to touch a tab of another size.
Fixed by overview-0012, `OverviewTab` records `width` and `height`, and the page data holds them so the script computes no tab size."""

import test_a_unit_box_takes_its_place_colour_on_the_overview as host

from electrical_symbols import LIBRARY
from fransys_layout.engines.overview import lay_out_overview
from fransys_model.layout import OverviewBox, layout_of

_X, _Y, _WIDTH, _HEIGHT = 0, 1, 4, 5  # the page tab row: x, y, text_width, text, width, height

built = host.built  # the module-scope build, shared: pytest finds a fixture by its module name


def test_every_drawn_tab_has_the_size_layout_recorded(built) -> None:
    model, data = built
    recorded = sorted((t.x, t.y, t.width, t.height) for b in layout_of(lay_out_overview(model, LIBRARY)[0], OverviewBox).values() for t in b.tabs)
    drawn = sorted((t[_X], t[_Y], t[_WIDTH], t[_HEIGHT]) for view in data["views"] for box in view["boxes"] for t in box["tabs"])
    assert recorded
    assert drawn == recorded
