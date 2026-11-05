"""The text style of a cable end is `EndTextStyle`, not the old layout enum's name (EL-9 part 0)."""

from fransys_model.derive.texts import end_text


def test_the_end_text_style_is_named_apart_from_the_layout_end_style() -> None:
    """`EndStyle` was the layout enum; the text module's own type must not take its name."""
    assert not hasattr(end_text, "EndStyle")
