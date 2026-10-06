"""TEXT-ROOM (layout-0094): a column's room counts a supply text's first free box, one side only.

On `power_fixture`'s plant a placed function with a supply symbol (text `+24`) has a keep-out that
reaches, right of that symbol's body, the text's width and the profile's text clearance (its
first candidate, E, is clear there). The field case holds the side-blocked one (p03).
"""

from power_fixture import power_run

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import text_width, translate
from fransys_layout.stages.texts.power import power_places

_PAD = DEFAULT_PROFILE.marker_padding


def test_a_supply_text_widens_its_keepout_on_the_side_of_its_first_free_box() -> None:
    """UNDO: in `with_power_rooms` return `boxes` at once: no keep-out widens."""
    layout = power_run()[2].layout
    wide = text_width("+24", height=DEFAULT_PROFILE.text_height) + _PAD
    bars = [one for one in power_places(layout.markers) if one.text]
    assert bars
    keepouts = [(f, translate(f.geometry.keepout, dx=f.at.x, dy=f.at.y)) for f in layout.placed]
    for bar in bars:
        (owner,) = (
            k
            for f, k in keepouts
            if (f.drawing_set, f.page) == (bar.drawing_set, bar.page)
            and k.x <= bar.pin.x <= k.x + k.width
            and k.y <= bar.pin.y <= k.y + k.height
        )
        assert owner.x + owner.width >= bar.body.x + bar.body.width + wide
