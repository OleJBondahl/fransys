"""GRID-HOME SB9: render reads the build's library and the facade's record equals it."""

from decimal import Decimal

import fransys as fr
import pytest
from fransys._drawing_library import _record
from fransys._settings_library import library_of
from fransys_render import _library as render_library

from electrical_symbols import LIBRARY
from fransys_model.kernel import Draft, freeze


def test_render_reads_the_library_it_is_given_equal_to_the_facade_record() -> None:
    record = _record(freeze(Draft()), LIBRARY)
    assert record.divisions == render_library.DIVISIONS
    assert LIBRARY.font is not None
    smallest = Decimal(str(LIBRARY.font.heights["smallest"]))
    size = render_library.font_size_mm(LIBRARY, smallest)
    assert float(size) == pytest.approx(float(record.ems["1.8"]))
    assert record.ascent_ratio == Decimal(LIBRARY.font.ascent) / Decimal(LIBRARY.font.units_per_em)


def test_render_follows_the_build_library_not_the_house_one(tmp_path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text("[font.heights]\nsmallest = 2.0\n", encoding="utf-8")
    built = library_of(fr.settings(path))
    assert built.font is not None
    assert built.font.heights["smallest"] == 2.0
    assert render_library.capital_ratio(built) == render_library.capital_ratio(LIBRARY)
    assert render_library.text_room_g(
        built, Decimal(2), Decimal("2.5")
    ) == render_library.text_room_g(LIBRARY, Decimal(2), Decimal("2.5"))
