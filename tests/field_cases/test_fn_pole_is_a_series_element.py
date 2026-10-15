"""Field case: one pole of a multi-pole function stands in a series as a one-pole element.

A two-pole switch is one function (pins 1/2 and 3/4). Its second pole alone feeds a one-pole
breaker, and a changeover relay's make throw takes its common from the first pole alone.

The bug: a multi-pole function in a series sets its whole pole count ("S1.main leaves with 2 poles
(2, 4) but F2.element takes 1 pole"), so a single pole needed a `d.wire` with pin names.

Fixing decision: author-0056 (API-FRICTION-2 C5): `fn.pole(n)` counts from 1 in pole order.
"""

import fransys as fr
import pytest
from fransys.colours import BK


def _design(build):
    d = fr.design("demo_parts")
    s1 = d.device("S1", "DEMO-SWITCH-DC-2P")
    build(d, s1)
    return d


def _ends(d) -> set[frozenset]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def _pole_to_breaker(d, s1) -> None:
    f2 = d.device("F2", "DEMO-MCB-C6")
    d.series(s1.main.pole(2), f2.element, wire=(BK, 0.75))


def _pole_to_relay(d, s1) -> None:
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(s1.main.pole(1), k1.co_1.no, wire=(BK, 0.75))


def test_pole_two_load_feeds_the_one_pole_breaker_and_pole_one_is_untouched() -> None:
    ends = _ends(_design(_pole_to_breaker))
    assert frozenset(("-S1:4", "-F2:1")) in ends
    assert not any(pin in end for end in ends for pin in ("-S1:1", "-S1:2", "-S1:3"))


def test_pole_one_load_feeds_a_relay_common_and_pole_two_is_untouched() -> None:
    ends = _ends(_design(_pole_to_relay))
    assert frozenset(("-S1:2", "-K1:11")) in ends
    assert not any(pin in end for end in ends for pin in ("-S1:3", "-S1:4"))


def test_a_pole_past_the_count_names_the_function_and_its_count() -> None:
    def build(d, s1) -> None:
        f2 = d.device("F2", "DEMO-MCB-C6")
        with pytest.raises(fr.AuthorError, match=r"S1\.main has 2 poles; pole\(3\)"):
            d.series(s1.main.pole(3), f2.element, wire=(BK, 0.75))

    _design(build)


@pytest.mark.parametrize("n", [0, -1, True, 1.0, "2"])
def test_a_pole_number_that_is_not_an_integer_from_one_raises_at_the_call(n) -> None:
    def build(_d, s1) -> None:
        with pytest.raises(fr.AuthorError, match=r"S1\.main\.pole\(.*\) takes a pole number"):
            s1.main.pole(n)

    _design(build)


def test_a_changeover_is_refused_by_name() -> None:
    def build(d, s1) -> None:
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        with pytest.raises(fr.AuthorError, match=r"K1\.co_1\.no or K1\.co_1\.nc"):
            d.series(k1.co_1.pole(1), s1.main.pole(1), wire=(BK, 0.75))

    _design(build)


def test_pole_one_of_a_one_pole_function_is_the_function() -> None:
    def build(d, s1) -> None:
        f2 = d.device("F2", "DEMO-MCB-C6")
        d.series(s1.main.pole(1), f2.element.pole(1), wire=(BK, 0.75))

    assert frozenset(("-S1:2", "-F2:1")) in _ends(_design(build))
