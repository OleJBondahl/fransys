"""The one table from a `SignalType` to how a WAGO channel is written (spec section 6)."""

from dataclasses import dataclass
from typing import Final

from fransys_model.vocab import SignalType


@dataclass(frozen=True, slots=True, kw_only=True)
class SignalFormat:
    """How one signal type reads in a module fragment (field meanings: `docs/SPEC.md`)."""

    abbr: str
    output: bool
    kind: str
    description: str


_DIGITAL_IN = SignalFormat(
    abbr="DI", output=False, kind="bool", description="Digital input channel"
)
_ANALOG_IN = SignalFormat(abbr="AI", output=False, kind="short", description="Analog input channel")
_ANALOG_OUT = SignalFormat(
    abbr="AO", output=True, kind="short", description="Analog output channel"
)

SIGNALS: Final[dict[SignalType, SignalFormat]] = {
    SignalType.DI: _DIGITAL_IN,
    SignalType.DO: SignalFormat(
        abbr="DO", output=True, kind="bool", description="Digital output channel"
    ),
    SignalType.AI_CURRENT: _ANALOG_IN,
    SignalType.AI_VOLTAGE: _ANALOG_IN,
    SignalType.AO_CURRENT: _ANALOG_OUT,
    SignalType.AO_VOLTAGE: _ANALOG_OUT,
    SignalType.RTD: SignalFormat(
        abbr="RTD", output=False, kind="short", description="Analog input channel"
    ),
    SignalType.RELAY: SignalFormat(
        abbr="RO", output=True, kind="bool", description="Relay output channel"
    ),
}
