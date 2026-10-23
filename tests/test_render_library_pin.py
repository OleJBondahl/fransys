"""GRID-HOME SB9: render's own reading of the library equals the facade's record."""

from fransys._drawing_library import _record
from fransys_render import _library as render_library


def test_render_copy_equals_the_facade_record() -> None:
    record = _record()
    assert record.divisions == render_library.DIVISIONS
    assert record.capital_ratio == render_library.CAPITAL_RATIO
    assert record.ascent_ratio == render_library.ASCENT_RATIO
