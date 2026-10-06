"""T4: the chain tie rules, each row hitting alone, and the order they are tried in.

The reading is a plain namespace: a chain of terminals `p0, p1, ...` whose entry port of pole
`i` is `e<i>` and whose exit is `x<i>`; each pole is its own function.
"""

from types import SimpleNamespace
from typing import Any

from fransys_layout.conventions import Order
from fransys_layout.conventions.order import CHAIN_TIES
from fransys_layout.stages import _chain_ties
from fransys_layout.stages._chain_ties import needs_reverse

UNRANKED: dict[str, int] = {}


def _case(  # noqa: PLR0913 -- a fixture builder, every field optional
    *,
    names: list[str],
    strips: list[str] | None = None,
    entry: dict[str, str | None] | None = None,
    ranks: dict[str, int] = UNRANKED,
    designations: list[str] | None = None,
    tie_keys: dict[str, tuple[str, ...]] | None = None,
) -> tuple[Any, Any]:
    count = len(names)
    strips = strips or [""] * count
    designations = designations or ["D"] * count
    seq = [(f"p{i}", f"e{i}", f"x{i}") for i in range(count)]
    poles = {
        f"p{i}": SimpleNamespace(terminal=True, kind=None, function=f"f{i}") for i in range(count)
    }
    specs = {
        f"f{i}": SimpleNamespace(strip_text=strips[i], designation=designations[i])
        for i in range(count)
    }
    port_function = {h: f"f{i}" for i in range(count) for h in (f"e{i}", f"x{i}")}
    rd = SimpleNamespace(
        poles=poles,
        specs=specs,
        port_function=port_function,
        port_side={f"e{i}": names[i] for i in range(count)},
        strip_entry=entry or {},
        rank_of=ranks,
        tie_key=tie_keys or {},
    )
    return seq, rd


def test_the_strip_vote_alone_decides_against_the_walk() -> None:
    """D1vote: most poles enter their strip by the other port, so the chain runs the other way."""
    seq, rd = _case(
        names=["external", "external", "internal"], strips=["S"] * 3, entry={"S": "internal"}
    )
    assert needs_reverse(seq, rd) is True


def test_the_strip_vote_alone_keeps_a_majority_walk_and_a_tie_over_the_rest() -> None:
    """D1vote: a majority for the walk keeps it, and so does a tie, whatever C20 and A6 say."""
    against_rest: dict[str, Any] = {"ranks": {"x1": 1, "e0": 9}, "designations": ["B", "A"]}
    won = _case(
        names=["internal", "internal", "external"], strips=["S"] * 3, entry={"S": "internal"}
    )
    assert needs_reverse(*won) is False
    tie = _case(
        names=["external", "internal"], strips=["S"] * 2, entry={"S": "internal"}, **against_rest
    )
    assert needs_reverse(*tie) is False
    assert needs_reverse(*_case(names=["x", "x"], **against_rest)) is True


def test_the_potential_rank_alone_decides_when_no_strip_votes() -> None:
    """C20: the lower rank (higher potential) goes on top; equal or missing ranks do not decide."""
    keep = ["A", "B"]
    down = _case(names=["a", "b"], ranks={"e0": 5, "x1": 2}, designations=keep)
    assert needs_reverse(*down) is True
    up = _case(names=["a", "b"], ranks={"e0": 2, "x1": 5}, designations=["B", "A"])
    assert needs_reverse(*up) is False
    equal = _case(names=["a", "b"], ranks={"e0": 3, "x1": 3}, designations=["B", "A"])
    assert needs_reverse(*equal) is True
    one = _case(names=["a", "b"], ranks={"e0": 5}, designations=["B", "A"])
    assert needs_reverse(*one) is True


def test_the_designation_alone_decides_when_both_tie() -> None:
    """A6: the end with the lower designation runs first; a tie falls to the sort key."""
    assert needs_reverse(*_case(names=["a", "b"], designations=["B", "A"])) is True
    assert needs_reverse(*_case(names=["a", "b"], designations=["A", "B"])) is False
    keys: dict[str, tuple[str, ...]] = {"f0": ("2",), "f1": ("1",)}
    assert needs_reverse(*_case(names=["a", "b"], tie_keys=keys)) is True
    assert needs_reverse(*_case(names=["a", "b"])) is False


def test_the_order_of_the_rows_is_the_order_the_rules_are_tried(monkeypatch: Any) -> None:
    """Swapping A6 ahead of C20 changes a chain where they disagree."""
    case = _case(names=["a", "b"], ranks={"e0": 5, "x1": 2}, designations=["A", "B"])
    assert needs_reverse(*case) is True
    swapped = Order("swapped", tuple(reversed(CHAIN_TIES.criteria)))
    monkeypatch.setattr(_chain_ties, "CHAIN_TIES", swapped)
    assert needs_reverse(*case) is False


def test_a_strip_is_entered_on_the_side_of_the_role_not_the_port_name() -> None:
    """D1vote: the reading carries sides only (`port_side`), so a port name never decides entry."""
    seq, rd = _case(
        names=["external", "external", "internal"], strips=["S"] * 3, entry={"S": "internal"}
    )
    assert not hasattr(rd, "port_name")
    assert needs_reverse(seq, rd) is True
    flipped = _case(
        names=["internal", "internal", "external"], strips=["S"] * 3, entry={"S": "external"}
    )
    assert needs_reverse(*flipped) is True
