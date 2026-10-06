"""The closed set of wire and core colours: IEC 60757 colour codes (decision model-0070).

One home for the grammar. A colour is one of:

- a base code, one of `BASE_COLOURS` (`BU`);
- two different base codes joined, for a two-colour core (`GNYE`);
- a base code and a core number, for numbered cores (`BK1`);
- a reserved code, one of `RESERVED_COLOURS` (`SH`, a shield), alone: it is not one half of a
  pair and takes no core number;
- empty, meaning no colour is recorded.

Matching is exact and case-sensitive. `validators.colours` guards it (`WIRE_COLOUR_UNKNOWN`);
`fransys_wireviz` reads it to draw a colour.
"""

from typing import Final

# Code and full name, in the standard's order. The names are the ones the drawings print.
BASE_COLOURS: Final = frozendict(
    {
        "BK": "black",
        "BN": "brown",
        "RD": "red",
        "OG": "orange",
        "YE": "yellow",
        "GN": "green",
        "BU": "blue",
        "VT": "violet",
        "GY": "grey",
        "WH": "white",
        "PK": "pink",
        "GD": "gold",
        "SR": "silver",
        "TQ": "turquoise",
    }
)

# Codes that are not one of the standard's fourteen but are legal on their own. A shield is a
# conductor, not a colour of a core, so `SH` never pairs or takes a number. The name is printed.
RESERVED_COLOURS: Final = frozendict({"SH": "shield"})

# What a finding says an allowed colour is; built from the two tables, so they never differ.
COLOUR_GRAMMAR: Final = (
    "an IEC 60757 colour code: a base code ("
    + ", ".join(f"{code} {name}" for code, name in BASE_COLOURS.items())
    + "), two different base codes joined (GNYE), a base code and a core number (BK1), or "
    + ", ".join(f"{code} {name}" for code, name in RESERVED_COLOURS.items())
    + " alone"
)


def split_colour(colour: str) -> tuple[str, str] | None:
    """`colour` as `(base codes, core number)`, or `None` when the grammar does not allow it.

    `"BU"` gives `("BU", "")`, `"GNYE"` gives `("GNYE", "")`, `"BK1"` gives `("BK", "1")`, and
    the empty colour gives `("", "")`. The base codes come back joined, two letters each, in the
    order written. A core number has no sign, no leading zero and follows a single base code.
    A reserved code gives itself and no number (`"SH"` gives `("SH", "")`), so the first item is
    then not a base code; `SHBK`, `BKSH` and `SH1` give `None`.
    """
    if not colour or colour in RESERVED_COLOURS:
        return colour, ""
    base, number = colour[:2], colour[2:]
    if base not in BASE_COLOURS:
        return None
    if not number:
        return base, ""
    if number.isascii() and number.isdigit() and number[0] != "0":
        return base, number
    if number in BASE_COLOURS and number != base:
        return colour, ""
    return None
