"""The throw table: one row per `PortRole`, as data (EL-5, CON-04, CON-05).

`THROWS[role]` is a plain lookup: no default row and no `.get`. A role without a row fails at
import (`complete`). A changeover's roles are `COMMON`, `BREAK` and `MAKE`; every other role is no
throw. The word is the one a series names a throw by (`k1.co_1.no`).
"""

from fransys_model.kernel import value

from .enums import PortRole
from .roles_types import complete


@value
class ThrowRow:
    """What a `PortRole` is in a changeover: a `throw` (BREAK or MAKE) or the `common` it joins.

    `word` names a throw (`nc`, `no`); `closed_at_rest` is true if the common closes to it at rest.
    Example: `THROWS[PortRole.BREAK]` is a throw, word `nc`, closed at rest.
    """

    common: bool = False
    throw: bool = False
    word: str | None = None
    closed_at_rest: bool | None = None


_R = PortRole
_THROW_ROWS: frozendict[PortRole, ThrowRow] = frozendict(
    {
        _R.GENERIC: ThrowRow(),
        _R.INTERNAL: ThrowRow(),
        _R.EXTERNAL: ThrowRow(),
        _R.PE: ThrowRow(),
        # contacts.py _pole: a switched link joins a common to a throw, either way round
        _R.COMMON: ThrowRow(common=True),
        # contacts.py _changeover_state: the break throw is closed at rest; _throws.py "nc"
        _R.BREAK: ThrowRow(throw=True, word="nc", closed_at_rest=True),
        # contacts.py _changeover_state: the make throw is closed when operated; _throws.py "no"
        _R.MAKE: ThrowRow(throw=True, word="no", closed_at_rest=False),
    }
)
THROWS = complete(_THROW_ROWS, PortRole)
