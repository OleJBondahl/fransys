"""The warnings of a drawing set that cannot draw all it holds (el-0022, designer Ruling 83).

A net cut by a set with no pin to carry its stub loses its end from that set; a set with
symbols and no page draws nothing.
Neither is ever silent: each is a WARNING naming the net or the set.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import connected_ports, item_designation, item_unit
from fransys_model.vocab import FINDING_CODES
lazy from fransys_model.kernel import Finding, natural_join

from .board_findings import undrawn_board_nets
from .codes import FINDING_CODES as EL_CODES
from .drawn_ids import core_symbol_id
from .drawn_netlist import pin_owner

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from fransys_layout.core import PlacementProblem
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist
    from .placement_kit import SymbolKit
    from .placement_sets import DrawingScope

__all__ = ["set_failure_finding", "set_without_page_findings"]

_INFO = {info.code: info for info in (*FINDING_CODES, *EL_CODES)}


def _symbols(problem: PlacementProblem, scope: DrawingScope) -> str:
    """The printed designations of the set's symbols, in the problem's order."""
    names = (s.id.partition(" ")[0] for s in problem.symbols if s.id in scope.symbols)
    return ", ".join(dict.fromkeys(names))


def _board_cause(model: Model, scope: DrawingScope) -> str:
    """The boards of the set's unit with nets drawn nowhere, as the clause that says why."""
    boards = [
        f"{item_designation(model, b)} ({natural_join(names)})"
        for b, names in undrawn_board_nets(model).items()
        if item_unit(model, b) == scope.of_unit
    ]
    if not boards:
        return ""
    return f"; board {', '.join(boards)} is a black box, so its nets are drawn nowhere (BOARD_NETS_NOT_DRAWN)"


def _nets_drawn(model: Model, owners: Mapping[str, Mapping[str, Id[Port]]], net: Netlist, scope: DrawingScope, drawn: Collection[str]) -> bool:
    """True when the net of each wired port of the set is drawn on some page; a set with no wired port has no net to lose (NO-SILENT-DROP)."""
    mine = {core_symbol_id(s) for s in scope.symbols}
    wired = {p.value for p in connected_ports(model)}
    ports = [p.value for sid, pins in owners.items() if sid in mine for p in pins.values() if p.value in wired]
    return all(net.net(model, p) in drawn for p in ports)


def set_without_page_findings(model: Model, kit: SymbolKit, net: Netlist, pageless: Iterable[tuple[DrawingScope, int]]) -> tuple[Finding, ...]:
    """One ERROR per set that holds symbols, got no page and has its nets drawn on no other page.

    A black-box set drawn in its container counts as drawn when all its nets are drawn there.
    """
    drawn = {net.net(model, p) for p in net.placed}
    owners = pin_owner(model, kit)
    found = []
    for scope, number in pageless:
        if _nets_drawn(model, owners, net, scope, drawn):
            continue
        subjects: tuple[Id[object], ...] = (scope.of_unit,) if scope.of_unit is not None else ()
        held = natural_join({s.partition(" ")[0] for s in scope.symbols})
        found.append(
            _INFO["SET_WITHOUT_PAGE"].finding(
                subjects,
                f"drawing set {number} holds {held} but has no page and its nets are drawn on no other page" + _board_cause(model, scope),
            )
        )
    return tuple(found)


def set_failure_finding(error: Exception, problem: PlacementProblem, scope: DrawingScope, number: int) -> Finding:
    """One `PLACEMENT_PROBLEM` ERROR for a drawing set whose layout raised `error` (FLIP-NOW F2).

    It names the set, its unit and symbols, and the error class; the set draws no page.
    """
    subjects: tuple[Id[object], ...] = (scope.of_unit,) if scope.of_unit is not None else ()
    return _INFO["PLACEMENT_PROBLEM"].finding(
        subjects,
        f"drawing set {number} ({_symbols(problem, scope)}) could not be laid out, so it has no page: {type(error).__name__}: {error}",
    )
