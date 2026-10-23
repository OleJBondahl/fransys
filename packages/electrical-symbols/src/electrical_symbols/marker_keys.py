"""The reference-marker symbol of each reference kind, its text slot and its turns (es-0082).

The core measures one marker symbol for every kind (layout-0305), so the table maps each kind
to it; a kind that draws another symbol later changes its row. Data, not a rule in a caller.
"""

from symdef import SymdefError

__all__ = ["MARKER_FACING", "MARKER_SLOT", "MARKER_TURNED", "MARKER_TURN_FACING", "marker_symbol"]

#: The slot of the marker symbol that holds the reference text.
MARKER_SLOT = "ref"

#: The marker symbol points east at R0; this turn points its box along the side it faces.
MARKER_FACING = frozendict({"E": "R0", "S": "R90", "W": "R180", "N": "R270"})

#: The symbol of a marker on a north or south pin: its text reads along the wire (S20 M1-M6).
MARKER_TURNED = "marker-arrow-turned"

#: The turn of `MARKER_TURNED` that points it south or north (it points south at R0).
MARKER_TURN_FACING = frozendict({"S": "R0", "N": "R180"})

_SYMBOL = frozendict(
    {
        "tag": "reference-marker",
        "arrow": "reference-marker",
        "star": "reference-marker",
        "stub": "reference-marker",
        "copy": "reference-marker",
    }
)


def marker_symbol(kind: str) -> str:
    """The library key of the marker symbol that draws a reference of `kind` (`RefKind` value)."""
    if kind not in _SYMBOL:
        msg = f"no marker symbol for reference kind {kind!r}: add its row to marker_keys._SYMBOL"
        raise SymdefError(msg)
    return _SYMBOL[kind]
