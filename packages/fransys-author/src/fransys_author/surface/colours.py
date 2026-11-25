"""IEC 60757 colour codes as importable names: `from ...colours import BU`.

Every value is read from the library's `Colour` list, so a code it lacks cannot exist here.
"""

from typing import Final

from fransys_model.elecdef import Colour
from fransys_model.vocab import RESERVED_CODES

BK: Final = Colour.BK.name
BN: Final = Colour.BN.name
RD: Final = Colour.RD.name
OG: Final = Colour.OG.name
YE: Final = Colour.YE.name
GN: Final = Colour.GN.name
BU: Final = Colour.BU.name
VT: Final = Colour.VT.name
GY: Final = Colour.GY.name
WH: Final = Colour.WH.name
PK: Final = Colour.PK.name
GD: Final = Colour.GD.name
SR: Final = Colour.SR.name
TQ: Final = Colour.TQ.name
SH: Final = RESERVED_CODES["shield"]
GNYE: Final = Colour.GNYE.name

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
