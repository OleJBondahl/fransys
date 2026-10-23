"""The marking-to-conductor table: which `ConductorMark` a pin marking names (EL-5, POT-31).

IEC 60445 designations as marked, `+` and `-` as the DC conductors, IEC 60034-8 motor ends.
`CONDUCTOR_MARKS[marking]` is a plain lookup; a marking that names no conductor is absent.
Every `ConductorMark` is the value of at least one marking, checked at import.
"""

from .enums import ConductorMark
from .roles_types import complete

_C = ConductorMark
CONDUCTOR_MARKS: frozendict[str, ConductorMark] = frozendict(
    {
        **{mark.value: mark for mark in ConductorMark},
        "+": _C.L_PLUS,
        "-": _C.L_MINUS,
        "U": _C.L1,
        "U1": _C.L1,
        "V": _C.L2,
        "V1": _C.L2,
        "W": _C.L3,
        "W1": _C.L3,
    }
)
complete(dict.fromkeys(CONDUCTOR_MARKS.values()), ConductorMark)
