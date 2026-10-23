"""An outline whose symbol cannot be stretched raises a DrawError naming the outline and its key."""

import pytest
from fransys_el import style
from fransys_render.draw import DrawError, svg
from test_draw import drawing

from electrical_symbols import LIBRARY
from fransys_layout.drawing import DrawnOutline


def test_an_outline_key_that_is_not_a_stretchable_frame_raises_naming_it() -> None:
    outline = DrawnOutline("o", "break-contact", ((0, 0), (64, 0), (64, 32), (0, 32)), None)
    with pytest.raises(DrawError, match=r"outline 'o' \('break-contact'\).*use a frame es key"):
        svg(drawing(outlines=(outline,)), LIBRARY, style(LIBRARY))
