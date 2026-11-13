"""Door to the family library `elecdef` (spec LIB-ADOPT R1): the names a reader needs.

`At`, `Quantity`, `Range`, `Rating`, `Role` and `Unit` carry the figures of a part file (a
rating, a coil window, a breaking capacity); `Current` is the AC/DC condition of a figure.
"""

from elecdef import At, Block, Breaker, Connection, Fuse, Quantity, Range, Rating, Role, Unit
from elecdef.connector import Connector
from elecdef.pins import Link, LinkKind, Pin, PinRole, Side, poles, throws
from elecdef.vocab import ContactForm, Current, Gender

__all__ = [
    "At",
    "Block",
    "Breaker",
    "Connection",
    "Connector",
    "ContactForm",
    "Current",
    "Fuse",
    "Gender",
    "Link",
    "LinkKind",
    "Pin",
    "PinRole",
    "Quantity",
    "Range",
    "Rating",
    "Role",
    "Side",
    "Unit",
    "poles",
    "throws",
]
