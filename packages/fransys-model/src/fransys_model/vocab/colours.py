"""The closed set of wire and core colours: IEC 60757 colour codes (decision model-0070).

One home for the grammar. A colour is one of:

- a base code, one of `BASE_COLOURS` (`BU`);
- two different base codes joined, for a two-colour core (`GNYE`);
- a base code and a core number, for numbered cores (`BK1`);
- a reserved code, one of `RESERVED_CODES` (`SH`, a shield), alone: it is not one half of a
  pair and takes no core number;
- empty, meaning no colour is recorded.

Matching is exact and case-sensitive. `validators.colours` guards it (`WIRE_COLOUR_UNKNOWN`);
`fransys_wireviz` reads it to draw a colour.
"""

from typing import Final

from fransys_model.kernel import SchemaError

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

# The two reserved conductor codes, by meaning (CABLE-05, CABLE-06). `SH` is the cable screen: a
# conductor, not a colour of a core, so it never pairs or takes a number. `GNYE` is the
# protective-earth core, GN and YE joined (IEC 60204-1).
RESERVED_CODES: Final = frozendict({"shield": "SH", "protective earth": "GNYE"})

_EARTH = RESERVED_CODES["protective earth"]
if not (_EARTH[:2] in BASE_COLOURS and _EARTH[2:] in BASE_COLOURS) or any(
    code in BASE_COLOURS for code in RESERVED_CODES.values()
):
    _msg = f"RESERVED_CODES {dict(RESERVED_CODES)!r} disagrees with BASE_COLOURS"
    raise SchemaError(_msg, kind="reserved_codes")

# What a finding says an allowed colour is; built from the two tables, so they never differ.
COLOUR_GRAMMAR: Final = (
    "an IEC 60757 colour code: a base code ("
    + ", ".join(f"{code} {name}" for code, name in BASE_COLOURS.items())
    + "), two different base codes joined (GNYE), a base code and a core number (BK1), or "
    + f"{RESERVED_CODES['shield']} shield"
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
    if not colour or colour in RESERVED_CODES.values():
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
