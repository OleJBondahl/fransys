"""Which drawn box or line of a view each finding counts on (overview-0010, OVERVIEW O18).

The page draws the badges; the roll-up of a subject onto the boxes and lines it names is
`view_rollup`'s. A finding counts once on a box, however many of its subjects roll up there.
"""

lazy from collections.abc import Sequence

from fransys_model.kernel import Severity
lazy from fransys_model.kernel import Finding, Model

from .rows_marks import FindingHold, FindingMark
from .view_rollup import subject_marks, view_lookup
lazy from .rows_overview_view import ViewRows

__all__ = ["finding_marks"]

type _Held = dict[int, dict[int, Severity]]


def _marks(*, on_line: bool, held: _Held) -> list[FindingMark]:
    return [
        FindingMark(
            on_line=on_line,
            at=at,
            held=tuple(FindingHold(finding=i, severity=v) for i, v in one.items()),
        )
        for at, one in sorted(held.items())
    ]


def finding_marks(
    model: Model, rows: ViewRows, findings: Sequence[Finding]
) -> tuple[FindingMark, ...]:
    """One `FindingMark` per box, then per line, of the view `rows` that `findings` name.

    A subject not drawn on the view counts on its nearest drawn ancestor box; one with none is
    left out. A finding holds its index in `findings` and counts once per box or line.
    """
    lookup = view_lookup(model, rows)
    boxes: _Held = {}
    lines: _Held = {}
    for index, finding in enumerate(findings):
        for subject in finding.subjects:
            on_boxes, on_lines = subject_marks(model, rows, lookup, subject)
            for at in on_lines:
                lines.setdefault(at, {})[index] = finding.severity
            for at in on_boxes:
                boxes.setdefault(at, {})[index] = finding.severity
    return tuple(_marks(on_line=False, held=boxes) + _marks(on_line=True, held=lines))
