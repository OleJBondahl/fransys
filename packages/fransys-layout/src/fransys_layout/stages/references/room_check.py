"""S4, layout-0143: a reference box drawn wider than the room its pass reserved is reported.

The band is sized at the floor `#n` digits (`refs` is known only after `place`), and the column
widths come from the pass before, at its `p<sheet>` digits. A set whose final decisions need more
digits draws a box wider than that room. Nothing is carried into another pass: it is one finding.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import heads_group
from fransys_model.kernel import Finding, Severity

from .digits import FLOOR, SetDigits, set_digits

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages.types import PagePlan

    from .types import MarkerDecision, References

REFERENCE_BOX_EXCEEDS_ROOM = "REFERENCE_BOX_EXCEEDS_ROOM"


def box_room_findings(
    decided: tuple[References, tuple[Finding, ...]], first_plans: Iterable[PagePlan]
) -> tuple[References, tuple[Finding, ...]]:
    """`decided` with one `REFERENCE_BOX_EXCEEDS_ROOM` per set whose box outgrew its room (S4).

    `first_plans` are the pages of the pass that sized the columns: its `p<sheet>` digits are
    the room; the band's `#n` room is the floor's.
    """
    references, found = decided
    reserved = {one.drawing_set: one.sheets for one in set_digits((), first_plans, {})}
    over = (
        one
        for one in references.digits
        if one.refs > FLOOR.refs or one.sheets > reserved.get(one.drawing_set, one.sheets)
    )
    return references, (*found, *(_finding(one, references.markers) for one in over))


def _finding(one: SetDigits, markers: Iterable[MarkerDecision]) -> Finding:
    """The finding of one set: its reference ends are the subjects."""
    ports = tuple(
        m.port
        for m in markers
        if m.drawing_set == one.drawing_set and not m.symbol and heads_group(m.star, m.side.value)
    )
    return Finding(
        code=REFERENCE_BOX_EXCEEDS_ROOM,
        severity=Severity.WARNING,
        subjects=ports,
        message=(
            f"drawing set {one.drawing_set}: a reference box is drawn for {one.refs}-digit #n and "
            f"{one.sheets}-digit p<sheet>, wider than the room its pass reserved"
        ),
    )
