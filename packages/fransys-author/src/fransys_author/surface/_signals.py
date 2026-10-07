"""Short names for the PLC signal types a function block asks for, and for `d.net`'s kinds (EA).

`EARTHED` and `IT` are the supplies' earthing systems. `ABOVE` and `BELOW` are the two sides
`d.layout.side` takes: the model's `Side.N` and `Side.S`, one enum for both (HL14).
Current loops only (4-20 mA); the voltage, RTD and relay types have no short name.
`PE` and `POWER` have none: `d.earth` and the supplies own those nets.
"""

from typing import Final

from fransys_model.layout import Side
from fransys_model.vocab import Earthing, NetClass, SignalType

DI: Final = SignalType.DI
DO: Final = SignalType.DO
AI: Final = SignalType.AI_CURRENT
AO: Final = SignalType.AO_CURRENT

CONTROL: Final = NetClass.CONTROL
SIGNAL: Final = NetClass.SIGNAL
GENERIC: Final = NetClass.GENERIC

EARTHED: Final = Earthing.EARTHED
IT: Final = Earthing.IT

ABOVE: Final = Side.N
BELOW: Final = Side.S
