"""`RESERVED_CODES` is the one home of the two reserved conductor codes (CABLE-05, CABLE-06)."""

from fransys import colours

from fransys_model.elecdef import Colour, core_colour
from fransys_model.vocab import COLOUR_GRAMMAR, RESERVED_CODES


def test_table_holds_the_screen_and_the_protective_earth_core():
    assert dict(RESERVED_CODES) == {"shield": "SH", "protective earth": "GNYE"}


def test_readers_expose_the_table_values():
    assert RESERVED_CODES["shield"] == colours.SH
    assert RESERVED_CODES["protective earth"] == colours.GNYE


def test_the_library_reads_both_reserved_codes():
    earth, screen = core_colour(RESERVED_CODES["protective earth"]), core_colour(RESERVED_CODES["shield"])
    assert earth is not None
    assert earth.protective
    assert screen is not None
    assert screen.screen
    assert RESERVED_CODES["shield"] not in Colour.__members__


def test_grammar_lists_base_codes_in_natural_order():
    listed = COLOUR_GRAMMAR.split("a base code (")[1].split(")")[0].split(", ")
    codes = [item.split()[0] for item in listed]
    assert codes == sorted(codes)
    assert "GNYE" not in codes
    assert len(codes) == 14
