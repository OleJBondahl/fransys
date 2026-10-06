"""The pole side and conductor of a port: the stated value, else the one a standard marking gives.

Decision parts-0010 (spec F9). One function, `facts`, so the marking tables live here only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_model.vocab import ConductorMark, FunctionKind, LinkKind, PoleSide, is_pole_link

if TYPE_CHECKING:
    from . import _toml

# IEC 60445 designations as marked, `+` and `-` as the DC conductors, IEC 60034-8 motor ends.
_CONDUCTOR_MARKINGS = {
    **{mark.value: mark for mark in ConductorMark},
    "+": ConductorMark.L_PLUS,
    "-": ConductorMark.L_MINUS,
    "U": ConductorMark.L1,
    "U1": ConductorMark.L1,
    "V": ConductorMark.L2,
    "V1": ConductorMark.L2,
    "W": ConductorMark.L3,
    "W1": ConductorMark.L3,
}
_COIL_SIDES = {"A1": PoleSide.LINE, "A2": PoleSide.LOAD}


def _pole_ports(entry: _toml.Table) -> set[str]:
    """The names of the ports on a switched or protective link of this function."""
    function = FunctionKind(entry["kind"])
    links = entry.get("links", ())
    return {
        link[end]
        for link in links
        if "kind" in link and is_pole_link(function, LinkKind(link["kind"]))
        for end in ("a", "b")
    }


def _side_from_marking(entry: _toml.Table, port: _toml.Table, marking: str) -> PoleSide | None:
    if entry["kind"] == "coil":
        return _COIL_SIDES.get(marking)
    if marking.isdigit() and port["name"] in _pole_ports(entry):
        return PoleSide.LINE if int(marking) % 2 else PoleSide.LOAD
    return None


def facts(entry: _toml.Table, port: _toml.Table) -> tuple[PoleSide | None, ConductorMark | None]:
    """`(pole_side, conductor_mark)` of one port of a function entry; a stated key wins."""
    marking = port.get("marking") or port["name"]
    side = PoleSide(port["side"]) if "side" in port else _side_from_marking(entry, port, marking)
    conductor = (
        ConductorMark(port["conductor"])
        if "conductor" in port
        else _CONDUCTOR_MARKINGS.get(marking)
    )
    return side, conductor
