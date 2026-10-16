"""The title-block band a text size needs: the stack scales with the text (TS2, ruling (c)).

The symbol's data is the other half: `title-block.toml` gives each row a y cut between its label
box and its value box, and a test in `fransys-render` pins the two together.
"""

from .print_sizes import HOUSE_TEXT_HEIGHT_MM, TextRole, font_size_mm, role_height_mm

__all__ = ["title_band_need"]

# The authored stack, in mm: the label and value slots of a row sit 3.125 apart, centre to centre
# (a 1.75 label box, a 1 mm gap, a 2.5 value box: 0.875 + 1 + 1.25), in the 20 mm band.
HOUSE_BAND_MM = 20.0
HOUSE_CENTRE_GAP_MM = 3.125
# A band's growth lands on the six y cuts by weight (1, 4, 1 in each row). The middle cut, between
# the label and the value, takes 4 of the 12 shares, so the gap grows by a third of the growth.
GAP_SHARE = 4 / 12
_HOUSE_LABEL = float(font_size_mm(role_height_mm(TextRole.LABEL, HOUSE_TEXT_HEIGHT_MM)))
_HOUSE_BODY = float(font_size_mm(role_height_mm(TextRole.BODY, HOUSE_TEXT_HEIGHT_MM)))


def title_band_need(label: float, body: float) -> float:
    """The band in mm at which a label of font size `label` clears the value of font size `body`.

    The centre gap scales with the two font sizes from the house gap, so the house sizes keep the
    authored stack and need 20 mm exactly; the capitals and the descenders keep their proportions.
    """
    gap_need = HOUSE_CENTRE_GAP_MM * ((label + body) / (_HOUSE_LABEL + _HOUSE_BODY))
    return HOUSE_BAND_MM + max(0.0, gap_need - HOUSE_CENTRE_GAP_MM) / GAP_SHARE
