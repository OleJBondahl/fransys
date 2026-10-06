"""Layout enums: the closed member sets used by `layout.*` records (design/layout-namespace.md).

Registered with the kernel the same way `vocab/enums.py` is, and holding strings only.
"""

from enum import Enum

from fransys_model.kernel import register_enum


@register_enum
class Orientation(Enum):
    """How a symbol is turned on the page: mirror in x first, then a clockwise turn.

    The eight values match the symbol libraries' orientations one to one. The member
    names are a contract: `fransys-layout` converts its geometry enum to this one by
    member name, so a rename here is a change there. Example: a contact drawn in a
    horizontal control rung is `R90`.
    """

    R0 = "r0"
    R90 = "r90"
    R180 = "r180"
    R270 = "r270"
    MR0 = "mr0"
    MR90 = "mr90"
    MR180 = "mr180"
    MR270 = "mr270"


@register_enum
class MarkerSide(Enum):
    """Which end of a severed signal a `LinkMarker` stands for.

    `OWNER` is where the signal comes from, `USER` where it continues.
    """

    OWNER = "owner"
    USER = "user"


@register_enum
class PlacementView(Enum):
    """Which view of the model a `SymbolPlacement` draws: function, item or pin."""

    FUNCTION = "function"
    ITEM = "item"
    PIN = "pin"


@register_enum
class StarKind(Enum):
    """What a star `LinkMarker` is: a stub to another location, a reference, a branch."""

    OFF = "off"
    REF = "ref"
    BRANCH = "branch"


@register_enum
class Side(Enum):
    """A side of a symbol or box, the compass direction something faces."""

    N = "n"
    E = "e"
    S = "s"
    W = "w"


@register_enum
class PageRole(Enum):
    """The drawing role of a `Page`; roles may share a page.

    A `POWER` group and a `CONTROL` group can be drawn on one page; the page's `role` is its
    first group's (deep-dive D4, decision layout-0048). Coarser than `NetClass` on purpose:
    an engine draws power and PE nets on `POWER` pages, control and generic nets on
    `CONTROL` pages, signal nets on `SIGNAL` pages.
    The member names are a contract: `fransys-layout` converts its stage-side role
    enum to this one by member name.
    """

    POWER = "power"
    CONTROL = "control"
    SIGNAL = "signal"


@register_enum
class LabelKind(Enum):
    """What a `Label` shows; the text itself is rendered from the model, never stored.

    `TAG` is the item designation at a function, `MARKING` a port name, `WIRE` a conductor
    label, `CROSS_REFERENCE` where the other functions of the same item are drawn.
    """

    TAG = "tag"
    MARKING = "marking"
    WIRE = "wire"
    CROSS_REFERENCE = "cross_reference"
