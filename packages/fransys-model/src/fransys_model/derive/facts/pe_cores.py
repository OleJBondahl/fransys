"""The PE-core fact: a core on a PE-role port must be green-yellow (IEC 60204-1, EARTH-12)."""

lazy from collections.abc import Iterable

from fransys_model.elecdef import PinRole
from fransys_model.vocab.colours import RESERVED_CODES

_GNYE = RESERVED_CODES["protective earth"]


def core_on_pe_not_gnye(colour: str, port_roles: Iterable[PinRole | None]) -> bool:
    """Whether a core of `colour` lands on a PE-role port without being GNYE.

    A screen (`SH`) is no conductor core and is exempt.
    The author refuses it at the call and the `CORE_ON_PE_NOT_GNYE` check finds it in a model.
    """
    return colour not in (RESERVED_CODES["shield"], _GNYE) and any(role is PinRole.PE for role in port_roles)
