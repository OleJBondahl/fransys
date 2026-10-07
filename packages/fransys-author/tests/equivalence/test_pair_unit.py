"""EA8, EA12: a board unit with a boundary, an open connector and a mate in a cabinet, one model."""

from typing import TYPE_CHECKING, NamedTuple

from fransys_author import Design
from fransys_author.surface import Design as SurfaceDesign
from fransys_author.surface import Device, design, unit

from .conftest import assert_same_model
from .series_parts import pair_library

if TYPE_CHECKING:
    from fransys_model.kernel import Draft


def engine(lib: Draft) -> Draft:
    e = Design(lib)
    c1 = e.location("C1", "")
    io = e.scope("IO", at=c1).unit("demo-io-board", revision=1, interface="1", tag="IO")
    io.revision(1, date="d", text="t", created="XX")
    x1 = io.item("DEMO-CONN-2P", name="X1", tag="X1")
    x2 = io.item("DEMO-CONN-2P", name="X2", tag="X2")
    io.boundary(x1, name="X1")
    io.boundary(x2)
    io.unused(x2)
    p1 = e.item("DEMO-CONN-2P", name="P1", tag="P1", at=c1)
    e.mate(p1, x1)
    return e.draft()


class _Board(NamedTuple):
    X1: Device


@unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
def board(d: SurfaceDesign) -> _Board:
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    d.device("X2", "DEMO-CONN-2P", unused=True)
    return _Board(x1)


def surface(lib: Draft) -> Draft:
    d = design(lib, place="C1")
    io = d.add(board, "IO")
    p1 = d.device("P1", "DEMO-CONN-2P")
    d.mate(p1, io.X1)
    return d.draft()


def test_the_board_unit_by_engine_and_surface_is_one_model() -> None:
    assert_same_model(pair_library(), engine, surface)
