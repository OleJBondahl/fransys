"""The PE-core fact: a core on a PE-role port must be green-yellow (IEC 60204-1, EARTH-12)."""

lazy from collections.abc import Iterable

from fransys_model.derive.facts.roles import is_pe_role
from fransys_model.vocab.colours import RESERVED_CODES
lazy from fransys_model.vocab.enums import PortRole

_GNYE = RESERVED_CODES["protective earth"]
_SCREEN = RESERVED_CODES["shield"]


def core_on_pe_not_gnye(colour: str, port_roles: Iterable[PortRole]) -> bool:
    """Whether a core of `colour` lands on a PE-role port without being GNYE.

    A screen (`SH`) is no conductor core and is exempt.
    The author refuses it at the call and the `CORE_ON_PE_NOT_GNYE` check finds it in a model.
    """
    return colour not in {_GNYE, _SCREEN} and any(is_pe_role(role) for role in port_roles)
