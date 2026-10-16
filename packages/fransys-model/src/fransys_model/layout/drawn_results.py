"""Drawn results: what the assembly writes for render, one record per drawn thing (SS6, SS8).

A symbol or a wire is drawn from its record alone: a library key, a page, a position and
the values `to_fragment` takes. The assembly writes them; render only reads. Axes are `"x"`, `"y"`.
"""

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.connectivity import Net

from .enums import Orientation, PageRole
from .formats import SheetFormat
from .results import Page


@value
class DrawnPoint:
    """One grid point of a drawn wire, in G from the page content-box origin."""

    x: int
    y: int


@record(kind="layout.drawn_symbol")
class DrawnSymbol:
    """One drawn thing that is not a wire: a library symbol placed on a page.

    `symbol` is the electrical-symbols key, variant included. `x`, `y` is the grid origin of
    the oriented symbol; `n` the table rows; `lengths` the stretch per axis; `offsets` a port
    id's coordinate along the stretch axis; `leads` the ports whose bound leads draw; `slots`
    the strings by slot id. `muted` draws a not-installed item grey and dashed. `owner` is the
    model thing as its id text (a record cannot hold `Id[Any]`), for the shorts check and links.
    """

    id: Id[DrawnSymbol]
    key: AuthoringKey
    symbol: str
    page: Id[Page]
    x: int
    y: int
    orient: Orientation
    produced_by: str
    n: int = 1
    lengths: frozendict[str, int] = frozendict()
    offsets: frozendict[str, int] = frozendict()
    leads: tuple[str, ...] = ()
    slots: frozendict[str, str] = frozendict()
    tint: str | None = None
    muted: bool = False
    owner: str | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.drawn_wire")
class DrawnWire:
    """One drawn wire: a polyline in the library's wire style on a page.

    `style` is a `[[wire]]` id of the library (`wire`, `trunk`, `link`, `by_others`);
    `lanes` above one is a bundle. `net` is the net the wire carries, when it has one.
    """

    id: Id[DrawnWire]
    key: AuthoringKey
    style: str
    page: Id[Page]
    points: tuple[DrawnPoint, ...]
    produced_by: str
    lanes: int = 1
    net: Id[Net] | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.drawn_page")
class DrawnPage:
    """One drawn page: its sheet and its role, so render can frame it.

    `sheet_format` names the authored sheet; `None` is the house sheet.
    """

    id: Id[DrawnPage]
    key: AuthoringKey
    page: Id[Page]
    kind: PageRole
    produced_by: str
    sheet_format: Id[SheetFormat] | None = None
    ext: frozendict[str, Value] = frozendict()
