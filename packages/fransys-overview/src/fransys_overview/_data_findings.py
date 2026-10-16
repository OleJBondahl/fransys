"""The findings layer's data: per view, the worst severity and its count on each box and line (O18).

A box's number counts the distinct findings of its worst severity (a finding with several subjects
on one box counts once); the box also carries every finding it holds, each once, for the panel.

The roll-up of a finding's subjects onto the boxes and lines of a view is `derive.finding_marks`;
this module only joins its marks to the findings' codes and messages.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import finding_marks
from fransys_model.derive.order import findings_in_order
from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from fransys_model.derive import FindingMark, ViewRows
    from fransys_model.kernel import Finding, Model

    from ._data import _Tables

Tally = dict[int, dict[int, int]]  # at -> {finding index: its severity rank}
_RANK = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
_NAME = {0: "info", 1: "warning", 2: "error"}


def _flat(model: Model, tally: Tally, findings: tuple[Finding, ...]) -> list[list[Any]]:
    """`[index, worst, count, [[severity, code, count, messages], ...]]`, worst code first.

    Messages follow in finding order (FT4); they print designations, never an Id (A10).
    """
    out: list[list[Any]] = []
    for at, held in sorted(tally.items()):
        worst = max(held.values())
        counts: dict[tuple[int, str], list[Finding]] = {}
        for i, rank in held.items():
            counts.setdefault((rank, findings[i].code), []).append(findings[i])
        ordered = sorted(counts.items(), key=lambda one: (-one[0][0], one[0][1]))
        listed = [
            [_NAME[rank], code, len(found), _messages(model, found)]
            for (rank, code), found in ordered
        ]
        out.append([at, _NAME[worst], sum(1 for r in held.values() if r == worst), listed])
    return out


def _messages(model: Model, found: list[Finding]) -> list[str]:
    """The messages of one code's findings in finding order."""
    return [f.message for f in findings_in_order(model, found)]


def _tally(marks: tuple[FindingMark, ...], *, lines: bool) -> Tally:
    """The `at -> {finding index: severity rank}` of the boxes, or of the lines."""
    return {
        m.at: {h.finding: _RANK[h.severity] for h in m.held} for m in marks if m.on_line is lines
    }


def findings_data(
    tables: _Tables, drawn: list[ViewRows], findings: tuple[Finding, ...]
) -> list[Any] | None:
    """`[[boxes, lines]]` per view, each `[index, severity, count, finding indexes]`, or `None`.

    `drawn` holds the rows of the views the page has, in the page's order.
    """
    per_view = [finding_marks(tables.model, rows, findings) for rows in drawn]
    if not any(per_view):
        return None
    return [
        [
            _flat(tables.model, _tally(marks, lines=False), findings),
            _flat(tables.model, _tally(marks, lines=True), findings),
        ]
        for marks in per_view
    ]


__all__ = ["findings_data"]
