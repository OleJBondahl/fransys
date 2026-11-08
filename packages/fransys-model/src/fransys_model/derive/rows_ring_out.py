"""The row shapes of the ring-out sheet: one join to test, and the words that head it (R2008, model-0199)."""

from decimal import Decimal
from enum import Enum

from fransys_model.kernel import value

__all__ = ["RingOutKind", "RingOutRow", "RingOutWords"]


class RingOutKind(Enum):
    """What kind of join a ring-out row is: a panel wire, a cable core or a terminal bridge."""

    WIRE = "wire"
    CORE = "core"
    BRIDGE = "bridge"


@value
class RingOutRow:
    """One join the electrician measures end to end.

    `from_`/`to` are the printed ends, `label` the wire label or the cable core text, `colour`
    and `cross_section_mm2` the wire's or the core's cable's (`""` and `None` for a bridge), `drawing` the
    page text of the first drawing of this document that shows an end, `""` for none.
    """

    join: RingOutKind
    from_: str
    to: str
    label: str
    colour: str
    cross_section_mm2: Decimal | None
    drawing: str


@value
class RingOutWords:
    """Every word the sheet prints, read from `[words]`; the dropdown values are `ok`, `wrong`, `untested`."""

    sheet: str
    revision: str
    no: str
    type: str
    wire: str
    core: str
    bridge: str
    from_: str
    to: str
    label: str
    colour: str
    mm2: str
    drawing: str
    status: str
    ok: str
    wrong: str
    untested: str
    found: str
    comment: str
    extra: str
