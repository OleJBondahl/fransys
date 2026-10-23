"""The warnings of a drawing set that cannot draw all it holds (el-0022, designer Ruling 83).

A net with one symbol in a set loses it from that set; a set with symbols and no page draws nothing.
Neither is ever silent: each is a WARNING naming the net or the set.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import port_designation
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import FINDING_CODES

from .codes import FINDING_CODES as EL_CODES
from .write_ids import port_values

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_model.kernel import Id, Model

    from .placement_sets import DrawingScope

__all__ = ["cut_net_findings", "set_failure_finding", "set_without_page_findings"]

_INFO = {info.code: info for info in (*FINDING_CODES, *EL_CODES)}


def _symbols(problem: PlacementProblem, scope: DrawingScope) -> str:
    """The printed designations of the set's symbols, in the problem's order."""
    names = (s.id.partition(" ")[0] for s in problem.symbols if s.id in scope.symbols)
    return ", ".join(dict.fromkeys(names))


def cut_net_findings(
    model: Model, problem: PlacementProblem, scope: DrawingScope, number: int
) -> tuple[Finding, ...]:
    """One WARNING per net whose single symbol in `scope` is all `restrict` leaves of it."""
    ports = port_values(model)
    found = []
    for net in problem.nets:
        inside = [p for p in net.pins if p.sym in scope.symbols]
        if len({p.sym for p in inside}) != 1 or len(inside) == len(net.pins):
            continue
        port = ports.get(net.id)
        name = port_designation(model, port) if port is not None else net.id  # ty: ignore[invalid-argument-type] - a port id
        found.append(
            Finding(
                code="NET_CUT_BY_SET",
                severity=Severity.WARNING,
                subjects=(port,) if port is not None else (),
                message=(
                    f"the net of port {name} has one end in drawing set {number} "
                    f"({_symbols(problem, scope)}) and its other end in another set: not drawn here"
                ),
                fix=_INFO["NET_CUT_BY_SET"].filled(),
            )
        )
    return tuple(found)


def set_without_page_findings(
    problem: PlacementProblem, scope: DrawingScope, layout: CoreLayout, number: int
) -> tuple[Finding, ...]:
    """One WARNING when `scope` holds symbols and the core gave it no page."""
    if not scope.symbols or layout.pages:
        return ()
    subjects: tuple[Id[object], ...] = (scope.of_unit,) if scope.of_unit is not None else ()
    return (
        Finding(
            code="SET_WITHOUT_PAGE",
            severity=Severity.WARNING,
            subjects=subjects,
            message=(
                f"drawing set {number} holds {_symbols(problem, scope)} but has no page: "
                "every net of its symbols has its other end in another set"
            ),
            fix=_INFO["SET_WITHOUT_PAGE"].filled(),
        ),
    )


def set_failure_finding(
    error: Exception, problem: PlacementProblem, scope: DrawingScope, number: int
) -> Finding:
    """One `PLACEMENT_PROBLEM` ERROR for a drawing set whose layout raised `error` (FLIP-NOW F2).

    It names the set, its unit and symbols, and the error class; the set draws no page.
    """
    subjects: tuple[Id[object], ...] = (scope.of_unit,) if scope.of_unit is not None else ()
    return Finding(
        code="PLACEMENT_PROBLEM",
        severity=Severity.ERROR,
        subjects=subjects,
        message=(
            f"drawing set {number} ({_symbols(problem, scope)}) could not be laid out, "
            f"so it has no page: {type(error).__name__}: {error}"
        ),
        fix=_INFO["PLACEMENT_PROBLEM"].filled(),
    )
