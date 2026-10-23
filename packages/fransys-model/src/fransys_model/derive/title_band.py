"""The title-block band a text size needs: the stack scales with the text (TS2, ruling (c)).

The symbol's data is the other half: `title-block.toml` gives each row a y cut between its label
box and its value box, and a test in `fransys-render` pins the two together.
"""

lazy from fransys_model.kernel import Model

from .house_settings import title_block_form_of
from .print_sizes import TextRole, font_size_mm, house_text_height_mm, role_height_mm

__all__ = ["title_band_need"]

# The authored stack is the `[title_block]` record's `band_mm` and `centre_gap_mm`: by default the
# label and value slots of a row sit 3.125 apart, centre to centre (a 1.75 label box, a 1 mm gap,
# a 2.5 value box: 0.875 + 1 + 1.25), in the 20 mm band.
# A band's growth lands on the six y cuts by weight (1, 4, 1 in each row). The middle cut, between
# the label and the value, takes 4 of the 12 shares, so the gap grows by a third of the growth.
GAP_SHARE = 4 / 12


def _house_size(model: Model, role: TextRole) -> float:
    house = house_text_height_mm(model)
    return float(font_size_mm(model, role_height_mm(model, role, house)))


def title_band_need(model: Model, label: float, body: float) -> float:
    """The band in mm at which a label of font size `label` clears the value of font size `body`.

    The centre gap scales with the two font sizes from the house gap, so the house sizes keep the
    authored stack and need 20 mm exactly; the capitals and the descenders keep their proportions.
    """
    form = title_block_form_of(model)
    band, house_gap = float(form.band_mm), float(form.centre_gap_mm)
    gap_need = house_gap * (
        (label + body) / (_house_size(model, TextRole.LABEL) + _house_size(model, TextRole.BODY))
    )
    return band + max(0.0, gap_need - house_gap) / GAP_SHARE
