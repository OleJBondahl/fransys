"""The rails an AC or DC supply gets when the author names none (EL-7 part F, Ruling 17).

`ac` lists the phase rails with their phase angle in degrees; `ac_neutral` is the neutral's mark.
`dc` lists the plus, minus and mid marks; `dc_zero` is the potential name of a 0 V rail.
"""

from typing import Any

from .enums import ConductorMark

_C = ConductorMark
RAIL_DEFAULTS: frozendict[str, Any] = frozendict(
    {
        "ac": ((_C.L1, 0), (_C.L2, 120), (_C.L3, 240)),
        "ac_neutral": _C.N,
        "dc": (_C.L_PLUS, _C.L_MINUS, _C.M),
        "dc_zero": "0V",
    }
)
