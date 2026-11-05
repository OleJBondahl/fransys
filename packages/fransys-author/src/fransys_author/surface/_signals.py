"""Short names for the PLC signal types a block asks for (EA).

Current loops only (4-20 mA); the voltage, RTD and relay types have no short name.
`PE` and `POWER` have none: `d.earth` and the supplies own those nets.
"""

from typing import Final

from fransys_model.vocab import NetClass, SignalType

DI: Final = SignalType.DI
DO: Final = SignalType.DO
AI: Final = SignalType.AI_CURRENT
AO: Final = SignalType.AO_CURRENT

CONTROL: Final = NetClass.CONTROL
SIGNAL: Final = NetClass.SIGNAL
GENERIC: Final = NetClass.GENERIC
