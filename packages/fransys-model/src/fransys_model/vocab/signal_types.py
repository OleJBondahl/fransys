"""The signal-type table: one row per `SignalType`, as data (EL-3 C1).

`SIGNAL_TYPES[signal]` is a plain lookup: no default row and no `.get`. A signal type without a
row fails at import (`complete`). `derive.signal_kind` reads the two fields.
"""

from fransys_model.kernel import value

from .enums import SignalType
from .roles_types import complete


@value
class SignalRow:
    """What a `SignalType` is: `output` for a PLC output channel, `analogue` for a value signal.

    Example: `SIGNAL_TYPES[SignalType.RELAY]` is `output` and not `analogue`.
    """

    output: bool
    analogue: bool


_S = SignalType
_SIGNAL_ROWS: frozendict[SignalType, SignalRow] = frozendict(
    {
        # kinds.py: DI is digital in; DO and RELAY are digital out
        _S.DI: SignalRow(output=False, analogue=False),
        _S.DO: SignalRow(output=True, analogue=False),
        _S.RELAY: SignalRow(output=True, analogue=False),
        # kinds.py: the two analogue inputs and RTD are analogue in
        _S.AI_CURRENT: SignalRow(output=False, analogue=True),
        _S.AI_VOLTAGE: SignalRow(output=False, analogue=True),
        _S.RTD: SignalRow(output=False, analogue=True),
        # kinds.py: the two analogue outputs are analogue out
        _S.AO_CURRENT: SignalRow(output=True, analogue=True),
        _S.AO_VOLTAGE: SignalRow(output=True, analogue=True),
    }
)
SIGNAL_TYPES = complete(_SIGNAL_ROWS, SignalType)
