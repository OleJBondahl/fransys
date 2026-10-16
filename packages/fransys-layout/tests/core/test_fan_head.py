"""The head of a fan and P3's head_short, on hand-built fans and on a cut with two drivers."""

from __future__ import annotations

from fransys_layout.core.fan_head import fan_head, head_short
from fransys_layout.core.values import Attach, Fan, PinRef

from .cut_fixtures import cut_of, elem, net, page_of


def attach(sym: str) -> Attach:
    return Attach(column=f"c:{sym}", lane=0, cell=0, pin=PinRef(sym, "s"))


def fan_with(drivers: tuple[Attach, ...]) -> Fan:
    return Fan("f:feed", ("feed",), drivers, (attach("k1"),), None, 1, "top")


def test_fan_head_is_the_one_driver_and_none_otherwise() -> None:
    one = attach("d0")
    assert fan_head(fan_with((one,))) == one
    assert fan_head(fan_with(())) is None
    assert fan_head(fan_with((one, attach("d1")))) is None


def test_head_short_reports_the_page_with_most_other_legs() -> None:
    assert head_short({1}, [1, 2, 2]) == (1, 2, 2)
    assert head_short({1, 2}, [1, 3, 3]) == (1, 3, 2)


def test_head_short_is_none_when_the_head_page_holds_the_most_legs() -> None:
    assert head_short({1}, [1, 1, 2]) is None
    assert head_short({1}, [1, 2]) is None  # a tie with the head's page: no finding
    assert head_short({1}, [1, 1]) is None  # every leg on the head's page
    assert head_short({1}, []) is None  # no legs


def test_head_short_ties_between_other_pages_keep_the_lower_page() -> None:
    assert head_short({3}, [1, 2]) == (0, 1, 1)


def test_a_fan_with_several_drivers_has_no_head_and_reports_nothing() -> None:
    """Two drivers feed the net with three legs: the fan has no head, so no HEAD_OFF_LEGS."""
    syms = [
        elem("d0", 500, 400),
        elem("d1", 500, 400),
        elem("k1", 300, 400),
        elem("k2", 300, 400),
        elem("k3", 300, 400),
    ]
    result = cut_of(syms, [net("feed", "d0.s", "d1.s", "k1.n", "k2.n", "k3.n")])
    (fan,) = result.flow.fans
    assert len(fan.drivers) == 2
    assert fan_head(fan) is None
    assert page_of(result)["c:d0"] < page_of(result)["c:k2"]  # the legs stand on later pages
    assert [f for f in result.spec.findings if f.code == "HEAD_OFF_LEGS"] == []
