"""`BOARD_NETS_NOT_DRAWN` (R305; layout-0322, moved here): a net wholly on an opaque board.

A board that shares its unit with another top-level device is a black box (layout-0044): the nets
between its parts are not drawn. One warning per board names them, in natural order.
"""

from typing import TYPE_CHECKING

from fransys_layout import FINDING_CODES
from fransys_model.derive import (
    enclosing_boards,
    is_sole_unit_root,
    item_designation,
    item_of_port,
    nets,
    port_rails,
)
from fransys_model.kernel import Finding, Severity, natural_join

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port

__all__ = ["board_nets_findings"]

_INFO = {info.code: info for info in FINDING_CODES}


def _innermost_opaque_board(model: Model, ends: Iterable[Id[Port]]) -> Id[Item] | None:
    """The innermost opaque board that is an ancestor-or-self of the item of every end."""
    common: frozenset[Id[Item]] | None = None
    outer_first: tuple[Id[Item], ...] = ()
    for port in ends:
        item = item_of_port(model, port)
        boards = tuple(b for b in enclosing_boards(model, item) if not is_sole_unit_root(model, b))
        common = frozenset(boards) if common is None else common & frozenset(boards)
        outer_first = outer_first or boards
        if not common:
            return None
    return [b for b in outer_first if b in (common or ())][-1] if common else None


def _dropped(model: Model) -> dict[Id[Item], set[str]]:
    """Each opaque board with the names of the nets wholly on it."""
    found: dict[Id[Item], set[str]] = {}
    for net in nets(model).values():
        if not port_rails(model, net.ports[0]) and (
            board := _innermost_opaque_board(model, net.ports)
        ):
            found.setdefault(board, set()).add(net.name or "net")
    return found


def board_nets_findings(model: Model) -> tuple[Finding, ...]:
    """One `BOARD_NETS_NOT_DRAWN` (`WARNING`) per opaque board, naming its undrawn nets."""
    return tuple(
        Finding(
            code="BOARD_NETS_NOT_DRAWN",
            severity=Severity.WARNING,
            subjects=(board,),
            message=(
                f"board {item_designation(model, board)} has nets that are not drawn: "
                f"{natural_join(names)}; the board is not the only top-level device of its unit"
            ),
            fix=_INFO["BOARD_NETS_NOT_DRAWN"].filled(),
        )
        for board, names in _dropped(model).items()
    )
