"""GRID-HOME SB9: render reads the build's library and the facade's record equals it."""

from decimal import Decimal

import pytest
from fransys._drawing_library import _record
from fransys_render import _library as render_library

from electrical_symbols import LIBRARY


def test_render_reads_the_library_it_is_given_equal_to_the_facade_record() -> None:
    record = _record(LIBRARY)
    assert record.divisions == render_library.DIVISIONS
    assert LIBRARY.font is not None
    smallest = Decimal(str(LIBRARY.font.heights["smallest"]))
    size = render_library.font_size_mm(LIBRARY, smallest)
    assert float(size) == pytest.approx(float(record.ems["1.8"]))
    assert record.ascent_ratio == Decimal(LIBRARY.font.ascent) / Decimal(LIBRARY.font.units_per_em)
