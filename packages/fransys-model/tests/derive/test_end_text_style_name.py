"""The text style of a cable end is `EndTextStyle`, not the layout enum's name (EL-9 part 0)."""

from fransys_model import layout
from fransys_model.derive.texts import end_text


def test_the_end_text_style_is_named_apart_from_the_layout_end_style() -> None:
    """`EndStyle` is the layout enum; the text module's own type must not share its name."""
    assert not hasattr(end_text, "EndStyle")
    assert end_text.EndTextStyle is not layout.EndStyle
