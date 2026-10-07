"""Derived layout kinds of harness lines on schematic pages (decision model-0173, spec HL9).

Render draws each by kind and reads every coordinate from the record. Texts are never stored:
the box texts come from `derive`, only their slot positions are kept here.
"""

from dataclasses import replace

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port

from .order import by_index, holder_of
from .results import Page, RoutePoint


@record(kind="layout.harness_line")
class HarnessLine:
    """One branch of a harness, drawn as an orthogonal polyline on one page.

    `branch` numbers the branch within its harness. `points` are stored in `index` order,
    in grid units on the page. `text_x`, `text_y` is where its designation text is centred; the
    text is always horizontal.
    """

    id: Id[HarnessLine]
    key: AuthoringKey
    page: Id[Page]
    harness: Id[Item]
    branch: int
    points: tuple[RoutePoint, ...]
    text_x: int
    text_y: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `points` in `index` order; a repeated `index` is refused."""
        kind, holder = "layout.harness_line", holder_of(self)
        points = by_index(self.points, RoutePoint, kind=kind, holder=holder)
        if points is not None:
            object.__setattr__(self, "points", points)


@value
class BoxText:
    """One text slot of a `ConnectorBox`: `x`, `y` is where line `index` of its texts stands."""

    index: int
    x: int
    y: int


@value
class BoxCell:
    """One pin cell of a `ConnectorBox`: the rectangle (top-left `x`, `y`) of one port."""

    index: int
    port: Id[Port]
    x: int
    y: int
    width: int
    height: int


@record(kind="layout.connector_box")
class ConnectorBox:
    """The box of one connector function at a harness line's end, on one page.

    `x`, `y` is the top-left corner and `width`, `height` the size, in grid units on the page.
    `texts` and `cells` are stored in `index` order; the text itself is never stored.
    """

    id: Id[ConnectorBox]
    key: AuthoringKey
    page: Id[Page]
    function: Id[Function]
    x: int
    y: int
    width: int
    height: int
    texts: tuple[BoxText, ...]
    cells: tuple[BoxCell, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `texts` and `cells` in `index` order; a repeated `index` is refused."""
        kind, holder = "layout.connector_box", holder_of(self)
        texts = by_index(self.texts, BoxText, kind=kind, holder=holder)
        if texts is not None:
            object.__setattr__(self, "texts", texts)
        cells = by_index(self.cells, BoxCell, kind=kind, holder=holder)
        if cells is not None:
            object.__setattr__(self, "cells", cells)


@value
class FanLeg:
    """One leg of a `HarnessFanOut`: the polyline of one conductor, points by `index`."""

    index: int
    conductor: Id[Conductor]
    points: tuple[RoutePoint, ...]


@record(kind="layout.harness_fan_out")
class HarnessFanOut:
    """The wires leaving the end of one harness branch that ends in no connector.

    `x`, `y` is the line's end point, where it ends and the legs start. `legs` are stored in `index`
    order, each leg's `points` too. Its legs are exempt from the orthogonal-wire rule by kind.
    """

    id: Id[HarnessFanOut]
    key: AuthoringKey
    page: Id[Page]
    harness: Id[Item]
    branch: int
    x: int
    y: int
    legs: tuple[FanLeg, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `legs` and each leg's `points` in `index` order; a repeated `index` is refused."""
        kind, holder = "layout.harness_fan_out", holder_of(self)
        legs = by_index(self.legs, FanLeg, kind=kind, holder=holder)
        if legs is None:
            return
        ordered = tuple(
            replace(
                leg, points=by_index(leg.points, RoutePoint, kind=kind, holder=holder) or leg.points
            )
            for leg in legs
        )
        object.__setattr__(self, "legs", ordered)
