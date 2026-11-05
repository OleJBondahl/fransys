"""The rows of the required-drawn ledger: what a drawing must show, and why it is carried (0371).

A row is a conductor end or a function symbol. Each is drawn, `Carried` by a reason, or an ERROR.
"""

from enum import Enum

from fransys_model.kernel import Id, SchemaError, register_enum, value
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Port

__all__ = ["Carried", "CarriedReason", "ConductorEnd", "FunctionSymbol", "Required"]


@value
class ConductorEnd:
    """One end of a conductor: it leaves `port` and reaches `far`, the conductor's other end."""

    conductor: Id[Conductor]
    port: Id[Port]
    far: Id[Port]


@value
class FunctionSymbol:
    """A function the schematic must draw as a symbol."""

    function: Id[Function]


type Required = ConductorEnd | FunctionSymbol


@register_enum
class CarriedReason(Enum):
    """Why a required row stands undrawn on purpose; the finding or ruling that names it follows."""

    SPARE = "SPARE"  # SPARE_TERMINALS, SPARE_FUNCTIONS
    UNWIRED = "UNWIRED"  # FUNCTION_NOT_WIRED
    OFF_DOCUMENT = "OFF_DOCUMENT"  # REFERENCE_OFF_DOCUMENT


@value
class Carried:
    """A required row that stands undrawn for `reason`: a conductor `end` or a function `symbol`.

    A kernel value holds no union, so the row is two fields; exactly one is set.
    """

    reason: CarriedReason
    end: ConductorEnd | None = None
    symbol: FunctionSymbol | None = None

    def __post_init__(self) -> None:
        """Refuse a `Carried` that names no row, or two."""
        if (self.end is None) == (self.symbol is None):
            msg = "a Carried row names one conductor end or one function symbol"
            raise SchemaError(msg, kind=type(self).__qualname__)
