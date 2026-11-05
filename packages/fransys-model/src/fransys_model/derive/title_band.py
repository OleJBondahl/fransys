"""The title-block band a text size needs: the stack scales with the text (TS2, ruling (c)).

The symbol's data is the other half: `title-block.toml` gives each row a y cut between its label
box and its value box, and a test in `fransys-render` pins the two together.
"""

lazy from fransys_model.kernel import Model

from .facts.house_settings import title_block_form_of
from .print_sizes import TextRole, role_height_mm

__all__ = ["title_band_need"]

# The authored stack is the `[title_block]` record's `band_mm`, `centre_gap_mm` and the two reference heights: by default the
# label and value slots of a row sit 3.125 apart, centre to centre (a 1.75 label box, a 1 mm gap,
# a 2.5 value box: 0.875 + 1 + 1.25), in the 20 mm band.
# A band's growth lands on the six y cuts by weight (1, 4, 1 in each row). The middle cut, between
# the label and the value, takes 4 of the 12 shares, so the gap grows by a third of the growth.
GAP_SHARE = 4 / 12
# The title block still measures text in the model (RENDER-DERIVE-CUT, KI-251).


def title_band_need(model: Model) -> float:
    """The band in mm at which the build's label and value capitals clear each other.

    The centre gap scales with the two capital heights from the house gap, so the house heights
    keep the authored stack and need 20 mm exactly; font sizes are proportional to the heights.
    """
    form = title_block_form_of(model)
    band, house_gap = float(form.band_mm), float(form.centre_gap_mm)
    heights = role_height_mm(model, TextRole.LABEL) + role_height_mm(model, TextRole.BODY)
    gap_need = house_gap * float(heights / (form.label_height_mm + form.value_height_mm))
    return band + max(0.0, gap_need - house_gap) / GAP_SHARE
