"""Derived layout kind of a subject's place in a page or sheet frame (model-0355).

The facade's switches write it; no pass writes it yet. It holds no coordinate and no string.
"""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port

from .enums import Shown
from .order import holder_of
from .results import Page
from .sheets import LayoutSheet


@value
class FrameCell:
    """A cell of a page frame's reference grid: `column` from 1, `row` one capital letter."""

    column: int
    row: str

    def __post_init__(self) -> None:
        """Refuse a column below 1 and a row that is not one capital letter."""
        if type(self.column) is int and self.column < 1:
            msg = "a frame cell column starts at 1"
            raise SchemaError(msg, kind="layout.frame_cell")
        row = self.row
        if type(row) is str and not (len(row) == 1 and "A" <= row <= "Z"):
            msg = "a frame cell row is one capital letter"
            raise SchemaError(msg, kind="layout.frame_cell")


@record(kind="layout.membership")
class Membership:
    """Where a subject sits: the frame cell of one page or sheet that shows it.

    Exactly one of `page`, `sheet` holds it and exactly one of `function`, `port`,
    `conductor` (a conductor end), `item` (a unit outline or a connector box) is the subject.
    `rank` is its reading order on its holder; `shown` says drawn or reference marker on a port
    or conductor-end row, else `None`. No coordinate, no string.
    """

    id: Id[Membership]
    key: AuthoringKey
    page: Id[Page] | None
    sheet: Id[LayoutSheet] | None
    function: Id[Function] | None
    port: Id[Port] | None
    conductor: Id[Conductor] | None
    item: Id[Item] | None
    rank: int
    shown: Shown | None
    cell: FrameCell
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Require one holder and one subject."""
        _exactly_one(
            self, "a membership has exactly one of page and sheet", (self.page, self.sheet)
        )
        subjects = (self.function, self.port, self.conductor, self.item)
        _exactly_one(
            self, "a membership has exactly one of function, port, conductor and item", subjects
        )


def _exactly_one(rec: Membership, msg: str, fields: tuple[object, ...]) -> None:
    if sum(field is not None for field in fields) != 1:
        raise SchemaError(msg, kind="layout.membership", record_id=holder_of(rec))
