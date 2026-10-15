"""A pole is in series when it has one wired N pin and one wired S pin (design 2.1, fact 7)."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.rows_series_pairs import SeriesPair
from fransys_model.derive.series_pairs import series_pairs
from fransys_model.layout import Side
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function, Port

_MCB3 = "DEMO-MCB-3P"
_CONN2 = "DEMO-CONN-2P"
_CONN4 = "DEMO-CONN-4P"

# Hand-written facings for the breaker (not read from the symbol): each pole's line pin faces N,
# its load pin S.
_MCB_SIDES = {"1": Side.N, "2": Side.S, "3": Side.N, "4": Side.S, "5": Side.N, "6": Side.S}


def _series(d: fr.Design) -> None:
    """SER: breaker CB, poles 1 and 2 wired on both pins, pole 3 wired nowhere."""
    with d.function("SER", "Series breaker"):
        cb = d.device("CB", _MCB3, place="L0")
        for pin, far in ((1, "K1"), (2, "K2"), (3, "K3"), (4, "K4")):
            d.detail.wire(cb[pin], d.device(far, _CONN2, place="L0")[1], wire=(BU, 0.5))


def _half(d: fr.Design) -> None:
    """HALF: breaker HB, pole 2 wired on both pins, its S pin 4 unwired, poles 1 and 3 wired."""
    with d.function("HALF", "Half-open breaker"):
        hb = d.device("HB", _MCB3, place="L0")
        for pin, far in ((1, "H1"), (2, "H2"), (3, "H3"), (5, "H5"), (6, "H6")):
            d.detail.wire(hb[pin], d.device(far, _CONN2, place="L0")[1], wire=(BU, 0.5))


def _junction(d: fr.Design) -> None:
    """JN: a 4-pin connector with pins 1-2 and 3-4 wired. CN: a 2-pin connector wired 1 to 2."""
    with d.function("JN", "Junction"):
        jn = d.device("JN", _CONN4, place="L0")
        d.detail.wire(jn[1], jn[2], wire=(BU, 0.5))
        d.detail.wire(jn[3], jn[4], wire=(BU, 0.5))
    with d.function("CN", "Two-pin connector"):
        cn = d.device("CN", _CONN2, place="L0")
        d.detail.wire(cn[1], cn[2], wire=(BU, 0.5))


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """One design holding the breaker, the junction and the two-pin connector."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _series(d)
    _half(d)
    _junction(d)
    return fr.build(d).model


def _function(model: fr.Model, item_key: str, name: str) -> Id[Function]:
    """The function `name` of the item whose key joins to `item_key`."""
    (item,) = [i for i, it in items(model).items() if "/".join(it.key) == item_key]
    (found,) = [f.id for f in functions(model).values() if f.item == item and f.name == name]
    return found


def _pins(model: fr.Model, function: Id[Function]) -> dict[str, Id[Port]]:
    """The ports of `function` by their printed name."""
    return {p.name: p.id for p in ports(model).values() if p.function == function}


def _sides(
    model: fr.Model, function: Id[Function], by_name: Mapping[str, Side]
) -> dict[Id[Port], Side]:
    """A `sides` map from each port of `function` named in `by_name`."""
    pins = _pins(model, function)
    return {pins[name]: side for name, side in by_name.items()}


def test_a_breaker_with_two_poles_in_series_gives_a_pair_per_pole(model: fr.Model) -> None:
    """Catches a pole missing its pair, or pairs out of pole order or with a wrong index."""
    function = _function(model, "SER/CB", "element")
    pins = _pins(model, function)
    sides = _sides(model, function, _MCB_SIDES)
    assert series_pairs(model, function, sides) == (
        SeriesPair(pole=0, north=pins["1"], south=pins["2"]),
        SeriesPair(pole=1, north=pins["3"], south=pins["4"]),
    )


def test_a_pole_with_its_south_pin_unwired_gives_no_pair_others_do(model: fr.Model) -> None:
    """Catches a pole paired without a wired S pin: pole 1 is open, poles 0 and 2 still pair."""
    function = _function(model, "HALF/HB", "element")
    pins = _pins(model, function)
    sides = _sides(model, function, _MCB_SIDES)
    assert series_pairs(model, function, sides) == (
        SeriesPair(pole=0, north=pins["1"], south=pins["2"]),
        SeriesPair(pole=2, north=pins["5"], south=pins["6"]),
    )


def test_a_junction_with_pins_on_one_side_or_east_west_gives_no_pair(model: fr.Model) -> None:
    """Catches a junction read as a series pole: two wired N pins, or pins facing E and W.

    The same connector facing N and S on pins 1 and 2 pairs, so the empty results are not a
    blanket miss.
    """
    function = _function(model, "JN/JN", "x1")
    pins = _pins(model, function)
    one_side = _sides(model, function, {"1": Side.N, "2": Side.N, "3": Side.S, "4": Side.S})
    east_west = _sides(model, function, {"1": Side.E, "2": Side.W, "3": Side.E, "4": Side.W})
    north_south = _sides(model, function, {"1": Side.N, "2": Side.S})
    assert series_pairs(model, function, one_side) == ()
    assert series_pairs(model, function, east_west) == ()
    assert series_pairs(model, function, north_south) == (
        SeriesPair(pole=0, north=pins["1"], south=pins["2"]),
    )


def test_a_single_pole_connector_pairs_only_when_it_faces_north_and_south(model: fr.Model) -> None:
    """Catches E/W pins read as series, and a single-pole function with no poles dropped.

    CN has no pole link, so it is one pole 0 holding both pins.
    """
    function = _function(model, "CN/CN", "x1")
    pins = _pins(model, function)
    east_west = _sides(model, function, {"1": Side.E, "2": Side.W})
    north_south = _sides(model, function, {"1": Side.N, "2": Side.S})
    assert series_pairs(model, function, east_west) == ()
    assert series_pairs(model, function, north_south) == (
        SeriesPair(pole=0, north=pins["1"], south=pins["2"]),
    )
