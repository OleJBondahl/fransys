"""layout-0129: `Home` is the one fact of where a cell or a spec stands against its home."""

from samples import column, function_spec, hid

from fransys_layout.stages import Cell, Home
from fransys_layout.stages.attach import _with_attached


def test_a_cell_and_a_spec_stand_at_home_by_default() -> None:
    """Only a writer that moves or copies a cell leaves HERE."""
    assert Cell(function=hid("function", 1), index=0).home is Home.HERE
    assert function_spec(1).home is Home.HERE


def test_an_attached_replica_is_away_and_an_attached_feeder_is_at_home() -> None:
    """`_with_attached` defaults to a replica; a feeder passes HERE (layout-0107)."""
    host = column("h", (1,))
    entry = (host.cells[0].function, "n", 0, hid("function", 2), "in", False)
    copy = _with_attached(host, [entry]).cells[0]
    home = _with_attached(host, [entry], home=Home.HERE).cells[0]
    assert (copy.home, home.home) == (Home.ELSEWHERE, Home.HERE)
