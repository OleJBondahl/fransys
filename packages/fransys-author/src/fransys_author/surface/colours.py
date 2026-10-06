"""IEC 60757 colour codes as importable names: `from ...colours import BU`.

Every value is read from the model's colour lists, so a code the model lacks cannot exist here.
"""

from typing import Final

from fransys_author.errors import AuthorError
from fransys_model.vocab import BASE_COLOURS, RESERVED_COLOURS, split_colour


def _code(name: str) -> str:
    """The model's own spelling of the base or reserved code `name`.

    Does not accept a code the model lacks: that raises at import.
    """
    if name not in BASE_COLOURS and name not in RESERVED_COLOURS:
        msg = f"colour code {name!r} is not in the model's colour lists"
        raise AuthorError(msg)
    return name


BK: Final = _code("BK")
BN: Final = _code("BN")
RD: Final = _code("RD")
OG: Final = _code("OG")
YE: Final = _code("YE")
GN: Final = _code("GN")
BU: Final = _code("BU")
VT: Final = _code("VT")
GY: Final = _code("GY")
WH: Final = _code("WH")
PK: Final = _code("PK")
GD: Final = _code("GD")
SR: Final = _code("SR")
TQ: Final = _code("TQ")
SH: Final = _code("SH")
GNYE: Final = GN + YE

if split_colour(GNYE) is None:
    _msg = f"GNYE ({GNYE!r}) is not a colour the model accepts"
    raise AuthorError(_msg)

__all__ = [
    "BK",
    "BN",
    "BU",
    "GD",
    "GN",
    "GNYE",
    "GY",
    "OG",
    "PK",
    "RD",
    "SH",
    "SR",
    "TQ",
    "VT",
    "WH",
    "YE",
]
