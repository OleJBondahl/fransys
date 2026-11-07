"""The one table from a CDP kind (`derive.cdp_kind`) to how a WAGO channel is written."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True, kw_only=True)
class SignalFormat:
    """How one CDP kind reads in a module fragment (field meanings: `docs/SPEC.md`)."""

    kind: str
    description: str
    digital: bool


SIGNALS: Final[dict[str, SignalFormat]] = {
    "DI": SignalFormat(kind="bool", description="Digital input channel", digital=True),
    "DO": SignalFormat(kind="bool", description="Digital output channel", digital=True),
    "AI": SignalFormat(kind="short", description="Analog input channel", digital=False),
    "AO": SignalFormat(kind="short", description="Analog output channel", digital=False),
}
