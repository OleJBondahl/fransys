"""layout-0107: the fed box is read from V1's sides: its group on top, the feeder's below."""

from typing import Any

from samples import function_spec, hid
lazy import pytest

from fransys_layout.engines.schematic.read import pairs
from fransys_model.derive import BoxPair

_FED, _FEEDER = hid("function", 1), hid("function", 2)
_NO_MODEL: Any = None  # box_pairs is patched, the model is never read


def _pairs(own: tuple[int, int], far: tuple[int, int]) -> dict[Any, BoxPair]:
    both = tuple((hid("port", a), hid("port", b)) for a, b in zip(own, far, strict=True))
    return {
        hid("function", 91): BoxPair(
            function=hid("function", 91), partner=hid("function", 92), port_pairs=both
        )
    }


def _feeds(monkeypatch: pytest.MonkeyPatch, north: set[int], south: set[int]):
    monkeypatch.setattr(pairs, "box_pairs", lambda _model, _drawn: _pairs((11, 12), (21, 22)))
    specs = (function_spec(1), function_spec(2))
    return pairs.box_feeds(
        _NO_MODEL, specs, {hid("port", n) for n in north}, {hid("port", n) for n in south}
    )


def test_a_group_on_top_fed_by_a_group_below_is_a_pairing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ports 11, 12 are on top of box 1 and 21, 22 below box 2: box 1 is fed by box 2."""
    (feed,) = _feeds(monkeypatch, {11, 12}, {21, 22})
    assert (feed.fed, feed.feeder) == (_FED, _FEEDER)
    assert [(p.fed, p.feeder) for p in feed.ports] == [
        (hid("port", 11), hid("port", 21)),
        (hid("port", 12), hid("port", 22)),
    ]


def test_two_groups_both_on_the_bottom_are_no_pairing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both paired groups below their boxes: neither stands over the other, as today."""
    # UNDO: engines/schematic/read/pairs.py:box_feeds, `if all(p in north ...) and all(p in south
    #     ...)` -> `if True` (the side check is dropped)
    assert _feeds(monkeypatch, set(), {11, 12, 21, 22}) == ()


def test_a_box_with_no_side_split_is_no_pairing(monkeypatch: pytest.MonkeyPatch) -> None:
    """`item_sides` gives `{}` on a tie: no port is on top, so no pairing."""
    assert _feeds(monkeypatch, set(), set()) == ()


def test_in_a_chain_the_upper_pair_stays_and_the_lower_is_no_pairing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Box 3 feeds box 2 and box 2 feeds box 1: the pair over box 2 stays, the other goes."""
    # UNDO: read/pairs.py:box_feeds, the `f.feeder not in fed_boxes and` term removed
    both = {
        hid("function", 91): BoxPair(
            function=hid("function", 91),
            partner=hid("function", 92),
            port_pairs=((hid("port", 11), hid("port", 21)),),
        ),
        hid("function", 93): BoxPair(
            function=hid("function", 93),
            partner=hid("function", 94),
            port_pairs=((hid("port", 21), hid("port", 31)),),
        ),
    }
    monkeypatch.setattr(pairs, "box_pairs", lambda _model, _drawn: both)
    specs = tuple(function_spec(n) for n in (1, 2, 3))
    top = {hid("port", 11), hid("port", 21)}
    below = {hid("port", 21), hid("port", 31)}
    got = pairs.box_feeds(_NO_MODEL, specs, top, below)
    assert [(f.fed, f.feeder) for f in got] == [(hid("function", 2), hid("function", 3))]
