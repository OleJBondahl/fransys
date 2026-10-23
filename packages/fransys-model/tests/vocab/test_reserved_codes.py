"""`RESERVED_CODES` is the one home of the two reserved conductor codes (CABLE-05, CABLE-06)."""

from fransys import colours

from fransys_model.derive.core_pairs import SCREEN
from fransys_model.vocab import BASE_COLOURS, RESERVED_CODES, split_colour


def test_table_holds_the_screen_and_the_protective_earth_core():
    assert dict(RESERVED_CODES) == {"shield": "SH", "protective earth": "GNYE"}


def test_readers_expose_the_table_values():
    assert colours.SH == RESERVED_CODES["shield"] == SCREEN
    assert RESERVED_CODES["protective earth"] == colours.GNYE


def test_gnye_is_gn_and_ye_and_sh_is_no_base_colour():
    assert RESERVED_CODES["protective earth"] == colours.GN + colours.YE
    assert RESERVED_CODES["shield"] not in BASE_COLOURS


def test_grammar_still_accepts_both_alone():
    for code in RESERVED_CODES.values():
        assert split_colour(code) == (code, "")
